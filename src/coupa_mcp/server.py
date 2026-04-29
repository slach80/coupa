from mcp.server.fastmcp import FastMCP

from .config import load_config
from .client import CoupaClient
from .tools import purchase_orders, invoices, suppliers, requisitions, approvals


def create_server() -> FastMCP:
    config = load_config()
    client = CoupaClient(config)
    mcp = FastMCP(
        name="coupa-mcp",
        instructions=(
            "Provides access to Coupa procurement data including purchase orders, "
            "invoices, suppliers, and requisitions. Use search tools for bulk queries "
            "and get tools for single-record lookups. Use approve/reject tools to act "
            "on items pending approval."
        ),
    )
    purchase_orders.register(mcp, client)
    invoices.register(mcp, client)
    suppliers.register(mcp, client)
    requisitions.register(mcp, client)
    approvals.register(mcp, client)
    return mcp


def main() -> None:
    server = create_server()
    server.run()


if __name__ == "__main__":
    main()
