from typing import Literal

from mcp.server.fastmcp import FastMCP

from ..client import CoupaClient

ApprovableType = Literal["purchase_orders", "invoices", "requisitions"]


def register(mcp: FastMCP, client: CoupaClient) -> None:

    @mcp.tool(
        name="coupa_approve_object",
        description=(
            "Approve a purchase order, invoice, or requisition. "
            "Specify the object_type ('purchase_orders', 'invoices', or 'requisitions') "
            "and the object's ID."
        ),
    )
    async def approve_object(
        object_type: ApprovableType,
        id: int,
        comment: str | None = None,
    ) -> dict:
        body = {"comment": comment} if comment else None
        return await client.put(f"/{object_type}/{id}/approve", body=body)

    @mcp.tool(
        name="coupa_reject_object",
        description=(
            "Reject a purchase order, invoice, or requisition. "
            "A rejection comment is required. "
            "Specify the object_type ('purchase_orders', 'invoices', or 'requisitions') "
            "and the object's ID."
        ),
    )
    async def reject_object(
        object_type: ApprovableType,
        id: int,
        comment: str,
    ) -> dict:
        return await client.put(f"/{object_type}/{id}/reject", body={"comment": comment})
