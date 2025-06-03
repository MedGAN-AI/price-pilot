from langchain_core.tools import Tool

def _check_order_status(order_id: str) -> str:
    """
    Stub implementation. In a real system, you’d call your order database or API.
    """
    return f"Order {order_id} is currently being processed and should ship soon."

order_tool = Tool(
    name="OrderTool",
    func=_check_order_status,
    description="Gets the status of a customer order. Input: an order ID string."
)
