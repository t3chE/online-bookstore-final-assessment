# tests/test_order_logic.py

import pytest
import uuid
from unittest.mock import patch, Mock

# Import the necessary components directly from the model definitions
from models import Order, PaymentGateway, EmailService, Book, Cart

# --- Fixtures for clean testing ---
# (Assume clean_books, populated_cart, etc., are in conftest.py)

@pytest.fixture
def order_data(populated_cart):
    """Provides consistent, valid data required for order creation."""
    return {
        'items': populated_cart.get_items(),
        'user_email': 'test@user.com',
        'shipping_info': {'name': 'Test', 'address': '1 Main'},
        'total_amount': populated_cart.get_total_price(),
        # Provide minimal payment_info so Order can be instantiated
        'payment_info': {'method': 'credit_card', 'transaction_id': 'TXN000'}
    }

# --- Payment Gateway Mock Unit Tests (FR-004) ---

def test_process_payment_mock_success_returns_id():
    """Verifies that a successful payment returns the expected structure and a transaction ID."""
    payment_info = {'card_number': '4000123456789012', 'amount': 30.97}
    result = PaymentGateway.process_payment(payment_info)
    
    assert result['success'] is True
    assert 'transaction_id' in result
    assert isinstance(result['transaction_id'], str)
    # The actual length check depends on your mock implementation, but a basic check is good
    assert len(result['transaction_id']) > 0 

def test_process_payment_mock_failure_card_1111_error():
    """Edge Case: Verifies the payment failure scenario for the card ending in 1111."""
    payment_info = {'card_number': '4000123456781111', 'amount': 30.97}
    result = PaymentGateway.process_payment(payment_info)
    
    assert result['success'] is False
    assert 'message' in result
    # Accept either 'declined' or 'invalid'/'failed' wording depending on implementation
    assert any(k in result['message'].lower() for k in ('declined', 'invalid', 'failed'))

# --- Email Service Mock Unit Tests (FR-005) ---

@patch('models.print') # Mock the print function used internally by EmailService
def test_send_order_confirmation_mock_is_called(mock_print, order_data):
    """Verifies the mock email service is called when sending a confirmation."""
    order = Order(order_id='TEST001', **order_data)
    
    EmailService.send_order_confirmation('test@user.com', order)

    # Assert that the print function was called at least once and the output contains expected lines
    assert mock_print.call_count > 0
    joined = "\n".join(" ".join(map(str, c.args)) for c in mock_print.call_args_list)
    assert 'test@user.com' in joined
    assert 'TEST001' in joined

# --- Order Class Unit Tests (FR-003, FR-005) ---

def test_order_creation_success(order_data):
    """Verifies the Order object is instantiated correctly with all data points."""
    order_id = 'ORD-123'
    order = Order(order_id=order_id, **order_data)
    
    assert order.order_id == order_id
    assert order.user_email == order_data['user_email']
    assert order.total_amount == order_data['total_amount']

def test_order_details_match_cart_data(order_data, populated_cart):
    """Verifies the line item details are correctly copied from the cart."""
    order = Order(order_id='ORD-456', **order_data)
    
    # Check that the number of items and the total price match the cart data used
    assert len(order.items) == len(populated_cart.get_items()) 
    assert order.total_amount == pytest.approx(populated_cart.get_total_price())
    
    order_item_titles = [item.book.title for item in order.items]
    cart_item_titles = [item.book.title for item in populated_cart.get_items()]
    
    assert set(order_item_titles) == set(cart_item_titles)    