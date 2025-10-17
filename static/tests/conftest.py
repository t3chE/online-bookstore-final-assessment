import pytest
import app


@pytest.fixture(scope="function", autouse=True)
def cleanup_globals():
    """
    Clears and restores the `app.users` mapping in-place around each test.
    This avoids reassigning module globals and keeps any references to
    `app.users` valid for the rest of the application.
    """
    backup = dict(app.users)
    try:
        app.users.clear()
        yield
    finally:
        app.users.clear()
        app.users.update(backup)


@pytest.fixture
def clean_books():\
    """Provides a fresh list of Book instances for tests."""
    return [
        app.Book("The Great Gatsby", "Fiction", 10.99, "img/gatsby.jpg"),
        app.Book("1984", "Dystopia", 8.99, "img/1984.jpg"),
        app.Book("I Ching", "Traditional", 18.99, "img/iching.jpg"),
    ]


@pytest.fixture
def empty_cart():
    """Returns a fresh, empty Cart object for testing Cart methods."""
    return app.Cart()


@pytest.fixture
def populated_cart(clean_books):
    """Returns a Cart with two books added."""
    cart = app.Cart()
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