Integration tests
=================

This directory contains integration test scaffolding for end-to-end workflows between Cart, Order, Inventory, Payment and Email systems.

Placing fixtures
----------------
Put any sample data files (CSV/JSON/XLSX) under `fixtures/`.
A recommended path is:

  static/tests/integration/fixtures/orders.xlsx

Expected sheet/column shape (example):
- Sheet: orders
- Columns: order_id, user_email, book_title, quantity, price, payment_method, card_number

How to enable integration tests
-------------------------------
Integration tests are skipped by default. Remove the `@pytest.mark.skip` decorator from a test to enable it locally. Integration tests may require additional dependencies (pandas/openpyxl) and may need network or database mocks.

CI note
-------
Integration tests are intentionally NOT run in the default `CI` workflow. When ready, we will create a separate workflow that runs integration tests in a controlled environment or a feature branch.
