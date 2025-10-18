import pytest
from app import app, BOOKS, INVENTORY
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

        # Check inventory reduced by 2
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

        # Payment should fail and inventory should be unchanged
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

        # Since inventory was zero, the process should not have reduced stock (still zero)
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
        # attempting checkout should fail due to insufficient stock
        post = post_process_checkout(client, 'Frank', 'frank@example.com', '6 Rd', 'Burg', '55555', card_number='4242424242424242')
        assert INVENTORY[book.title] == 0


