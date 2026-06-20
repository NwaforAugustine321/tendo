"""Auto-import all tool modules to trigger @register decorators."""

from app.db.tools import (  # noqa: F401
    customers,
    inventory,
    invoices,
    payments,
    products,
    profiles,
    transactions,
    services,
    storage,
)
