from datamodel import OrderDepth, TradingState, Order
from typing import Dict, List
import jsonpickle  # For state persistence


class Trader:

    def __init__(self):
        # Initialize default state (only for local testing)
        self.trader_data = {
            "example_state": 0  # Replace with your own state variables
        }

    def run(self, state: TradingState) -> tuple[Dict[str, List[Order]], int, str]:
        """
        Processes market data and returns orders.
        :param state: Contains order book, positions, and traderData
        :return: (orders, conversions, traderData)
        """
        # --- 1. Load Persistent State ---
        if state.traderData:
            self.trader_data = jsonpickle.decode(state.traderData)

        # --- 2. Initialize Outputs ---
        result: Dict[str, List[Order]] = {}  # Orders per product
        conversions = 0  # No conversions by default

        # --- 3. Process Each Product ---
        for product in state.order_depths:
            order_depth = state.order_depths[product]
            current_position = state.position.get(product, 0)
            orders: List[Order] = []

            # --- [Your Strategy Logic Goes Here] ---
            # Example: Print market data
            print(f"{product} - Position: {current_position}")
            print("Bids:", order_depth.buy_orders)
            print("Asks:", order_depth.sell_orders)

            if product == "RAINFOREST_RESIN":
                fair_value = 10000
                max_bid = max(order_depth.buy_orders)
                quantity = order_depth.buy_orders[0]
                if max(order_depth.buy_orders) < fair_value:
                    orders.append(Order(product, max_bid, quantity))



            # --- 4. Store Orders (If Any) ---
            if orders:
                result[product] = orders

        # --- 5. Update and Serialize State ---
        self.trader_data["example_state"] += 1  # Track iterations
        trader_data_str = jsonpickle.encode(self.trader_data)

        return result, conversions, trader_data_str