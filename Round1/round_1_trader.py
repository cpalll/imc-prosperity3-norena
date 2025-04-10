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
        # Set Position limit constants
        POSITION_LIMIT = 50

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
            print("Bids:", order_depth.buy_orders)
            print("Asks:", order_depth.sell_orders)

            if product == "RAINFOREST_RESIN":
                fair_value = 10000
                max_bid = max(order_depth.buy_orders)
                max_bid_volume = order_depth.buy_orders[max_bid]
                min_ask = min(order_depth.sell_orders)
                min_ask_volume = order_depth.sell_orders[min_ask]


                # Sell if bid price higher than fair value
                if max_bid > fair_value:
                    max_sell_volume = POSITION_LIMIT + current_position
                    sell_quantity = min(max_bid_volume, max_sell_volume)
                    orders.append(Order(product, max_bid, -sell_quantity))
                    print(f"Selling resin at {max_bid} for {sell_quantity}")
                # Buy if ask price lower than fair value
                elif min_ask < fair_value:
                    max_buy_volume = POSITION_LIMIT - current_position
                    buy_quantity = min(min_ask_volume, max_buy_volume)
                    orders.append(Order(product, min_ask, -buy_quantity))
                    print(f"Buying resin at {min_ask} for {buy_quantity}")
                print(f"{product} - Position: {current_position}")



            # --- 4. Store Orders (If Any) ---
            if orders:
                result[product] = orders

        # --- 5. Update and Serialize State ---
        self.trader_data["example_state"] += 1  # Track iterations
        trader_data_str = jsonpickle.encode(self.trader_data)

        return result, conversions, trader_data_str