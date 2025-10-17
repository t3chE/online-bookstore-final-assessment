# tests/unit_tests.py

import pytest
import uuid
from unittest.mock import patch, Mock

# Import all classes/objects directly from app.py
from app import Book, Cart, User, Order, PaymentGateway, EmailService, BOOKS, users

@pytest.fixture
def clean_books():
    """Provides a fresh, immutable list of books for test reference."""
    return [
        Book("The Great Gatsby", "Fiction", 10.99, "img/gatsby.jpg"),
        Book("1984", "Dystopia", 8.99, "img/1984.jpg"),
        Book("I Ching", "Traditional", 18.99, "img/iching.jpg")
    ]

@pytest.fixture
def empty_cart():
    """Returns a fresh, empty Cart object for testing Cart methods."""
    return Cart()

@pytest.fixture
def populated_cart(clean_books):
    """Returns a Cart with two books added."""
    cart = Cart()
    cart.add_book(clean_books[0], 2)  # Gatsby: 2 * 10.99 = 21.98
    cart.add_book(clean_books[1], 1)  # 1984: 1 * 8.99 = 8.99
    return cart

@pytest.fixture
def new_user_data():
    """Provides consistent test data for user registration."""
    return {
        'email': 'test@newuser.com',
        'password': 'securepassword',
        'name': 'Test User',
        'address': '1 Test Lane'
    }

@pytest.fixture(scope='function', autouse=True)
def cleanup_globals():
    """
    Cleans up global state (like the 'users' dict) before and after each test
    to ensure isolation, which is critical when testing a Flask app.
    """
    original_users = users.copy()
    
    # Setup: Ensure globals are clean before test starts (e.g., remove test users)
    global users 
    users = {} 
    
    yield # Run the test function
    
    # Teardown: Restore the original global state
    users = original_users