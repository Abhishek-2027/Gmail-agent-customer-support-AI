import json
import os

def get_order_details(order_id: str) -> str:
    """
    Mock tool to fetch order details from mock_orders.json
    """
    base_dir = os.path.dirname(__file__)
    db_path = os.path.join(base_dir, "mock_orders.json")
    
    if not os.path.exists(db_path):
        return "Order database not found."
        
    try:
        with open(db_path, "r") as f:
            data = json.load(f)
            
        for order in data.get("orders", []):
            if order["order_id"].upper() == order_id.upper():
                return f"Order Found: {json.dumps(order)}"
                
        return f"Order {order_id} not found in our system."
    except Exception as e:
        return f"Error accessing order database: {str(e)}"

# Registry of available tools for the agent
AVAILABLE_TOOLS = {
    "get_order_details": get_order_details
}
