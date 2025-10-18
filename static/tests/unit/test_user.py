# tests/test_user.py

import pytest
from unittest.mock import patch, Mock

# Import the User class from models and the users global from app
from models import User
from app import users

# (Fixtures for new_user_data, cleanup_globals will be in conftest.py)

# --- User Account Unit Tests (FR-006) ---

def test_user_registration_success_valid_data(new_user_data):
    """Verifies a new User object can be created and stored successfully."""
    
    # The registration logic is currently spread across the Flask route and the global 'users' dict.
    # To unit test the pure logic, we focus on the User class instance.
    
    # Arrange (Mimic route action): Create the user instance
    user_instance = User(
        new_user_data['email'], 
        new_user_data['password'], 
        new_user_data['name'], 
        new_user_data['address']
    )
    
    # Act: Check attributes
    
    # Assert
    assert user_instance.email == 'test@newuser.com'
    assert user_instance.name == 'Test User'
    assert user_instance.password == 'securepassword' 
    # NOTE: Since no hashing is implemented in the model, we assert the plain password.
    # If a hashing function were implemented, we would test that here (e.g., assert user_instance.password != 'securepassword').

# Since the registration and login logic is within the Flask routes, 
# full unit testing requires *mocking* the Flask context, which is complex.
# A simpler unit test focuses on the User object and the global state directly (as done above)
# and reserves the full route logic for Integration Testing.

def test_update_user_profile_name_success(new_user_data):
    """Tests updating a user's name on their profile."""
    # Arrange: Create a user instance
    user = User(**new_user_data)
    
    # Act: Update the name attribute directly (mimicking the model update)
    user.name = "Updated Name"
    
    # Assert
    assert user.name == "Updated Name"
    
def test_user_initial_order_history_is_empty(new_user_data):
    """Tests that a new user starts with an empty order history."""
    # Arrange: Create a user instance
    user = User(**new_user_data)
    
    # Assert
    assert user.get_order_history() == []