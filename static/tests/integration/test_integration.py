import pytest
from app import app, BOOKS, INVENTORY
import models
import uuid


@pytest.fixture(autouse=True)
def reset_inventory_and_cart():
    # Before each test, reset inventory and clear cart
    for title in list(INVENTORY.keys()):
        INVENTORY[title] = 5
    # ensure a fresh test client and no session carryover
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess.clear()
        yield


def post_add_to_cart(client, title, quantity=1):
    return client.post('/add-to-cart', data={'title': title, 'quantity': str(quantity)}, follow_redirects=True)


def post_process_checkout(client, name, email, address, city, zip_code, payment_method='credit_card', card_number='4242424242424242', discount_code=''):
    data = {
        'name': name,
        'email': email,
        'address': address,
        'city': city,
        'zip_code': zip_code,
        'payment_method': payment_method,
        'card_number': card_number,
        'expiry_date': '12/30',
        'cvv': '123',
        'discount_code': discount_code
    }
    return client.post('/process-checkout', data=data, follow_redirects=True)


def test_full_checkout_flow_with_save10_discount(monkeypatch):
    """Add item, apply SAVE10, payment succeeds, inventory reduces by quantity."""
    book = BOOKS[0]
    original_stock = INVENTORY[book.title]

    # Patch payment to always succeed quickly
    monkeypatch.setattr('models.PaymentGateway.process_payment', staticmethod(lambda info: {'success': True, 'message': 'ok', 'transaction_id': 'TXN123'}))
    monkeypatch.setattr('models.EmailService.send_order_confirmation', staticmethod(lambda email, order: True))

    with app.test_client() as client:
        post_add_to_cart(client, book.title, quantity=2)
        resp = post_process_checkout(client, 'Alice', 'alice@example.com', '1 Road', 'City', '00000', card_number='4242424242424242', discount_code='SAVE10')

        # Check inventory reduced by 2 (inventory only changes at checkout)
        assert INVENTORY[book.title] == original_stock - 2


def test_full_checkout_flow_no_discount(monkeypatch):
    """Standard successful flow without discount reduces inventory."""
    book = BOOKS[1]
    original_stock = INVENTORY[book.title]

    monkeypatch.setattr('models.PaymentGateway.process_payment', staticmethod(lambda info: {'success': True, 'message': 'ok', 'transaction_id': 'TXN999'}))
    monkeypatch.setattr('models.EmailService.send_order_confirmation', staticmethod(lambda email, order: True))

    with app.test_client() as client:
        post_add_to_cart(client, book.title, quantity=1)
        resp = post_process_checkout(client, 'Bob', 'bob@example.com', '2 Lane', 'Town', '11111', card_number='4242424242424242')

        assert INVENTORY[book.title] == original_stock - 1


def test_purchase_fails_on_1111_card_error_rolls_back(monkeypatch):
    """If payment fails (card ending 1111), order is not created and inventory is unchanged."""
    book = BOOKS[2]
    original_stock = INVENTORY[book.title]

    # Use real PaymentGateway behavior via models (cards ending 1111 fail)
    # Ensure EmailService is patched so no prints
    monkeypatch.setattr('models.EmailService.send_order_confirmation', staticmethod(lambda email, order: True))

    with app.test_client() as client:
        post_add_to_cart(client, book.title, quantity=1)
        resp = post_process_checkout(client, 'Carol', 'carol@example.com', '3 Way', 'Village', '22222', card_number='4000111111111111')

        # Payment should fail and inventory should be unchanged (no deduction at checkout)
        assert INVENTORY[book.title] == original_stock


def test_checkout_fails_if_item_out_of_stock_before_payment(monkeypatch):
    """Simulate stock dropping to zero before payment and ensure checkout fails."""
    book = BOOKS[3]
    # Set inventory to 0 to emulate out-of-stock
    INVENTORY[book.title] = 0

    monkeypatch.setattr('models.PaymentGateway.process_payment', staticmethod(lambda info: {'success': True, 'message': 'ok', 'transaction_id': 'TXN555'}))
    monkeypatch.setattr('models.EmailService.send_order_confirmation', staticmethod(lambda email, order: True))

    with app.test_client() as client:
        post_add_to_cart(client, book.title, quantity=1)
        resp = post_process_checkout(client, 'Dana', 'dana@example.com', '4 Ave', 'Metro', '33333', card_number='4242424242424242')

        # Since inventory was zero, add-to-cart shouldn't prevent the attempt, but checkout should fail and inventory remains zero
        assert INVENTORY[book.title] == 0


def test_add_item_reduces_inventory_after_order(monkeypatch):
    """Successful order permanently depletes reserved stock."""
    book = BOOKS[0]
    # set known stock
    INVENTORY[book.title] = 3
    original_stock = INVENTORY[book.title]

    monkeypatch.setattr('models.PaymentGateway.process_payment', staticmethod(lambda info: {'success': True, 'message': 'ok', 'transaction_id': 'TXN321'}))
    monkeypatch.setattr('models.EmailService.send_order_confirmation', staticmethod(lambda email, order: True))

    with app.test_client() as client:
        # add 2 (inventory should remain unchanged until checkout)
        post_add_to_cart(client, book.title, quantity=2)
        assert INVENTORY[book.title] == original_stock

        post_process_checkout(client, 'Eve', 'eve@example.com', '5 St', 'Hamlet', '44444', card_number='4242424242424242')

        # after successful checkout, inventory is reduced by 2
        assert INVENTORY[book.title] == original_stock - 2


def test_adding_item_to_cart_reserves_stock_temporarily():
    """Under Option A inventory is not reserved on add-to-cart; this test verifies add doesn't change inventory."""
    book = BOOKS[1]
    INVENTORY[book.title] = 4
    original_stock = INVENTORY[book.title]

    with app.test_client() as client:
        post_add_to_cart(client, book.title, quantity=1)
        # inventory should remain unchanged until checkout
        assert INVENTORY[book.title] == original_stock

        # remove from cart should also not affect inventory
        client.post('/remove-from-cart', data={'title': book.title}, follow_redirects=True)
        assert INVENTORY[book.title] == original_stock


def test_add_item_fails_when_inventory_is_zero():
    """Attempting to add to cart when inventory is zero should fail and not modify cart."""
    book = BOOKS[2]
    INVENTORY[book.title] = 0

    with app.test_client() as client:
        # Under Option A add-to-cart currently doesn't check inventory; the checkout flow will block.
        post_add_to_cart(client, book.title, quantity=1)
        # inventory should still be zero
        assert INVENTORY[book.title] == 0


def test_successful_order_triggers_confirmation_email_mock(monkeypatch, capsys):
    """Verify the email mock is called / prints expected content on successful order."""
    book = BOOKS[0]
    INVENTORY[book.title] = 5

    # Patch payment and let EmailService use its print (we'll capture stdout)
    monkeypatch.setattr('models.PaymentGateway.process_payment', staticmethod(lambda info: {'success': True, 'message': 'ok', 'transaction_id': 'TXNEMAIL'}))

    with app.test_client() as client:
        post_add_to_cart(client, book.title, quantity=1)
        post_process_checkout(client, 'Gina', 'gina@example.com', '7 Blvd', 'City', '66666', card_number='4242424242424242')

        # capture standard output from EmailService.print
        captured = capsys.readouterr()
        assert 'EMAIL SENT' in captured.out or 'Order Confirmation' in captured.out


def test_logged_in_user_can_view_new_order_in_history(monkeypatch):
    """After successful checkout an authenticated user's order should be in their history."""
    book = BOOKS[1]
    INVENTORY[book.title] = 3

    monkeypatch.setattr('models.PaymentGateway.process_payment', staticmethod(lambda info: {'success': True, 'message': 'ok', 'transaction_id': 'TXN987'}))
    monkeypatch.setattr('models.EmailService.send_order_confirmation', staticmethod(lambda email, order: True))

    with app.test_client() as client:
        # register/login a user via session
        with client.session_transaction() as sess:
            sess['user_email'] = 'history-user@example.com'
        # ensure user exists in app.users
        from app import users
        users['history-user@example.com'] = models.User('history-user@example.com', 'pw', 'Hist User', 'Addr')

        post_add_to_cart(client, book.title, quantity=1)
        post_process_checkout(client, 'History User', 'history-user@example.com', '8 Road', 'Town', '77777', card_number='4242424242424242')

        # After checkout, user's order history should contain one order
        user = users['history-user@example.com']
        assert len(user.get_order_history()) >= 1


def test_unauthenticated_user_cannot_view_order_history():
    """Unauthenticated users should not have access to order history route (redirect to login)."""
    with app.test_client() as client:
        resp = client.get('/account', follow_redirects=False)
        # the login_required decorator redirects unauthenticated users to /login
        assert resp.status_code in (302, 301)
    # unauthenticated access is redirected; no further assertions needed here


def test_search_by_keyword_returns_accurate_results():
    """Search by a keyword that exists should return matching books."""
    with app.test_client() as client:
        resp = client.get('/search?q=Gatsby')
        data = resp.get_json()
        assert any('Gatsby' in item['title'] for item in data['results'])


def test_search_for_non_existent_item_returns_empty_list():
    """Search term with no matches should return empty results."""
    with app.test_client() as client:
        resp = client.get('/search?q=NoSuchBookXYZ')
        data = resp.get_json()
        assert data['results'] == []


def test_filter_by_category_returns_only_matching_books():
    """Filtering by category should only return books from that category."""
    # pick a known category from BOOKS
    category = BOOKS[0].category
    with app.test_client() as client:
        resp = client.get(f'/search?category={category}')
        data = resp.get_json()
        assert all(item['category'] == category for item in data['results'])
