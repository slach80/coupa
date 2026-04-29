from mcp.server.fastmcp import FastMCP

from ..client import CoupaClient


def register(mcp: FastMCP, client: CoupaClient) -> None:

    @mcp.tool(
        name="coupa_list_requisitions",
        description=(
            "List requisitions from Coupa. Supports pagination and optional "
            "filtering by status or requester."
        ),
    )
    async def list_requisitions(
        offset: int = 0,
        limit: int = 50,
        status: str | None = None,
        requester_id: int | None = None,
    ) -> dict:
        params: dict = {"offset": offset, "limit": limit}
        if status:
            params["fields[requisition_header][status]"] = status
        if requester_id:
            params["fields[requisition_header][requester_id]"] = requester_id
        return await client.get("/requisitions", params=params)

    @mcp.tool(
        name="coupa_get_requisition",
        description="Retrieve a single requisition by its Coupa ID.",
    )
    async def get_requisition(id: int) -> dict:
        return await client.get(f"/requisitions/{id}")

    @mcp.tool(
        name="coupa_search_requisitions",
        description=(
            "Search requisitions using arbitrary Coupa query parameters. "
            "Pass a dict of field:value pairs as 'query'."
        ),
    )
    async def search_requisitions(
        query: dict,
        offset: int = 0,
        limit: int = 50,
    ) -> dict:
        params = {**query, "offset": offset, "limit": limit}
        return await client.get("/requisitions", params=params)

    @mcp.tool(
        name="coupa_create_requisition",
        description=(
            "Create a new requisition in Coupa. Provide a name and one or more line items. "
            "Returns the created requisition object including its ID."
        ),
    )
    async def create_requisition(
        name: str,
        lines: list[dict],
        description: str | None = None,
    ) -> dict:
        body: dict = {
            "requisition-header": {
                "title": name,
                "line-items": [
                    {
                        "description": line["description"],
                        "quantity": line["quantity"],
                        "unit-price": line["unit_price"],
                        "currency": {"code": line["currency"]},
                        **({"account": {"id": line["account_id"]}} if "account_id" in line else {}),
                        **({"commodity": {"id": line["commodity_id"]}} if "commodity_id" in line else {}),
                    }
                    for line in lines
                ],
            }
        }
        if description:
            body["requisition-header"]["justification"] = description
        return await client.post("/requisitions", body=body)

    @mcp.tool(
        name="coupa_submit_requisition",
        description=(
            "Submit a draft requisition for approval. "
            "This transitions the requisition from 'draft' into the approval queue."
        ),
    )
    async def submit_requisition(id: int) -> dict:
        return await client.put(f"/requisitions/{id}/submit")
