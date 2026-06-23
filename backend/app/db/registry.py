"""Tool registry — explicit map of tool names to handler functions."""

from app.db.tools.profiles import (
    create_business_profile,
    get_business_profile,
    update_business_profile,
)
from app.db.tools.products import (
    search_products,
    create_product,
    update_product,
    delete_product,
)
from app.db.tools.services import (
    search_services,
    create_service,
    update_service,
    delete_service,
)
from app.db.tools.customers import (
    search_customers,
    create_customer,
    get_customer,
    update_customer,
)
from app.db.tools.transactions import (
    record_transaction,
    get_transactions,
    get_transactions_summary,
    update_transaction,
    delete_transaction,
)
from app.db.tools.invoices import (
    create_invoice,
    get_invoices,
    update_invoice_status,
)
from app.db.tools.payments import (
    record_payment,
    get_payments,
)
from app.db.tools.inventory import (
    get_inventory,
    update_inventory,
    add_inventory,
    record_inventory_movement,
)
from app.db.tools.storage import (
    upload_business_logo,
)
from app.db.tools.understanding import (
    get_business_understanding,
    add_evidence,
    update_confidence,
    evolve_understanding,
)
from app.db.tools.checkpoints import (
    create_checkpoint,
    get_checkpoints,
)

TOOLS = {
    "create_business_profile": create_business_profile,
    "get_business_profile": get_business_profile,
    "update_business_profile": update_business_profile,
    "search_products": search_products,
    "create_product": create_product,
    "update_product": update_product,
    "delete_product": delete_product,
    "search_services": search_services,
    "create_service": create_service,
    "update_service": update_service,
    "delete_service": delete_service,
    "search_customers": search_customers,
    "create_customer": create_customer,
    "get_customer": get_customer,
    "update_customer": update_customer,
    "record_transaction": record_transaction,
    "get_transactions": get_transactions,
    "get_transactions_summary": get_transactions_summary,
    "update_transaction": update_transaction,
    "delete_transaction": delete_transaction,
    "create_invoice": create_invoice,
    "get_invoices": get_invoices,
    "update_invoice_status": update_invoice_status,
    "record_payment": record_payment,
    "get_payments": get_payments,
    "get_inventory": get_inventory,
    "update_inventory": update_inventory,
    "add_inventory": add_inventory,
    "record_inventory_movement": record_inventory_movement,
    "upload_business_logo": upload_business_logo,
    "get_business_understanding": get_business_understanding,
    "add_evidence": add_evidence,
    "update_confidence": update_confidence,
    "evolve_understanding": evolve_understanding,
    "create_checkpoint": create_checkpoint,
    "get_checkpoints": get_checkpoints,
}


def get_tool(name: str):
    return TOOLS.get(name)


def list_tools() -> list[str]:
    return list(TOOLS.keys())
