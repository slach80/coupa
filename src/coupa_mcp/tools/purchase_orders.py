from mcp.server.fastmcp import FastMCP

from ..client import CoupaClient


def register(mcp: FastMCP, client: CoupaClient) -> None:

    @mcp.tool(
        name="coupa_list_purchase_orders",
        description=(
            "List purchase orders from Coupa. Supports pagination and optional "
            "filtering by status or supplier. Returns an array of PO objects."
        ),
    )
    async def list_purchase_orders(
        offset: int = 0,
        limit: int = 50,
        status: str | None = None,
        supplier_id: int | None = None,
    ) -> dict:
        params: dict = {"offset": offset, "limit": limit}
        if status:
            params["fields[purchase_order][status]"] = status
        if supplier_id:
            params["fields[purchase_order][supplier_id]"] = supplier_id
        return await client.get("/purchase_orders", params=params)

    @mcp.tool(
        name="coupa_get_purchase_order",
        description="Retrieve a single purchase order by its Coupa ID.",
    )
    async def get_purchase_order(id: int) -> dict:
        return await client.get(f"/purchase_orders/{id}")

    @mcp.tool(
        name="coupa_search_purchase_orders",
        description=(
            "Search purchase orders using arbitrary Coupa query parameters. "
            "Pass a dict of field:value pairs as 'query'. "
            "Example: {\"status\": \"issued\", \"supplier[name]\": \"Acme Corp\"}"
        ),
    )
    async def search_purchase_orders(
        query: dict,
        offset: int = 0,
        limit: int = 50,
    ) -> dict:
        params = {**query, "offset": offset, "limit": limit}
        return await client.get("/purchase_orders", params=params)
