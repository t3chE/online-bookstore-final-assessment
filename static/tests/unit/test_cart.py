# tests/test_cart.py

import pytest
from unittest.mock import patch 

# Import the necessary components directly from the model definitions
from models import Book, Cart

# --- Cart Component Unit Tests (FR-002) ---

def test_add_single_item_to_empty_cart(empty_cart, clean_books):
    """Tests adding one book to the cart."""
    # Arrange: Cart is empty
    book = clean_books[0] # The Great Gatsby, 10.99
    
    # Act
    empty_cart.add_book(book, 1)
    
    # Assert: one unique item in the cart
    assert len(empty_cart.get_items()) == 1
    assert empty_cart.get_total_price() == 10.99

def test_add_same_item_twice_increases_quantity(empty_cart, clean_books):
    """Tests that adding the same item multiple times increases its quantity, not its count."""
    # Arrange
    book = clean_books[0]
    
    # Act
    empty_cart.add_book(book, 1)
    empty_cart.add_book(book, 2)
    
    # Assert
    assert len(empty_cart.get_items()) == 1 # Still one unique book in the cart
    assert empty_cart.get_total_items() == 3 # Total quantity is 3
    assert empty_cart.get_total_price() == (10.99 * 3)

def test_remove_existing_item_decreases_count(populated_cart):
    """Tests removing a book completely from a cart."""
    # Arrange: Populated cart has 'The Great Gatsby' and '1984'.
    book_title = '1984'
    initial_count = len(populated_cart.get_items())
    
    # Act
    populated_cart.remove_book(book_title)
    
    # Assert
    assert len(populated_cart.get_items()) == initial_count - 1
    assert book_title not in [item.book.title for item in populated_cart.get_items()]

def test_get_total_price_correct_subtotal(populated_cart):
    """Verifies the total price calculation for multiple items."""
    # Arrange:
    # Gatsby: 2 * 10.99 = 21.98
    # 1984:   1 * 8.99  = 8.99
    # Total: 30.97
    expected_total = 30.97
    
    # Act
    actual_total = populated_cart.get_total_price()
    
    # Assert
    assert actual_total == pytest.approx(expected_total) # Use pytest.approx for float comparison

def test_clear_cart_results_in_zero_items(populated_cart):
    """Tests the clear() method functionality."""
    # Arrange: Cart is populated
    
    # Act
    populated_cart.clear()
    
    # Assert
    assert populated_cart.is_empty() is True
    assert populated_cart.get_total_price() == 0

def test_update_quantity_to_zero_removes_item(populated_cart):
    """Edge Case: Updating a book's quantity to 0 removes it from the cart."""
    # Arrange: Populated cart has 'The Great Gatsby'.
    book_title = 'The Great Gatsby'
    initial_count = len(populated_cart.get_items())
    
    # Act
    populated_cart.update_quantity(book_title, 0)
    
    # Assert
    assert len(populated_cart.get_items()) == initial_count - 1 # Item count should decrease
    assert book_title not in [item.book.title for item in populated_cart.get_items()]