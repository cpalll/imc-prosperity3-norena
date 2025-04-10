from datamodel import TradingState, Order
from typing import Dict, List
import math
import jsonpickle  # For state persistence


class Trader:

    def __init__(self):
        # Initialize default state (only for local testing)
        self.trader_data = {
            "example_state": 0,
            "kelp_price_interval_previous": [0, 0],
            "kelp_price_interval_current": [-9999999, 9999999],
            "kelp_range_middle": 0,
            "kelp_trading_active": True,
        }

    def run(self, state: TradingState) -> tuple[Dict[str, List[Order]], int, str]:
        """
        Processes market data and returns orders.
        :param state: Contains order book, positions, and traderData
        :return: (orders, conversions, traderData)
        """
        # Set Position limit constants
        POSITION_LIMIT = 50
        KELP_RANGE_INTERVAL = 10000  # 10000 ms time intervals for ranges
        KELP_NEW_INTERVAL_THRESHOLD = 500  # 500 ms for new interval
        KELP_RANGE_PM = 1

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

            max_bid = max(order_depth.buy_orders)
            max_bid_volume = order_depth.buy_orders[max_bid]

            min_ask = min(order_depth.sell_orders)
            min_ask_volume = order_depth.sell_orders[min_ask]

            # Resin trading strategy
            if product == "RAINFOREST_RESIN":
                fair_value = 10000

                # Sell if bid price higher than fair value
                if max_bid > fair_value:
                    max_sell_volume = POSITION_LIMIT + current_position
                    sell_quantity = min(max_bid_volume, max_sell_volume)
                    orders.append(Order(product, max_bid, -sell_quantity))
                    print(f"SELL {sell_quantity}x {product} @ {max_bid}")

                # Buy if ask price lower than fair value
                elif min_ask < fair_value:
                    max_buy_volume = POSITION_LIMIT - current_position
                    buy_quantity = min(min_ask_volume, max_buy_volume)
                    orders.append(Order(product, min_ask, -buy_quantity))
                    print(f"BUY {buy_quantity}x {product} @ {min_ask}")

            # Kelp trading strategy
            if product == "KELP":
                best_bid = max(order_depth.buy_orders.keys())
                best_ask = min(order_depth.sell_orders.keys())
                mid_price = self.trader_data["kelp_range_middle"]
                current_range = self.trader_data["kelp_price_interval_current"]
                previous_range = self.trader_data["kelp_price_interval_previous"]
                spread = abs(previous_range[0] - previous_range[1])
                range_high = mid_price + spread / 2 + KELP_RANGE_PM
                range_low = mid_price - spread / 2 - KELP_RANGE_PM

                if state.timestamp % KELP_RANGE_INTERVAL == 0:
                    # Start new interval
                    self.trader_data["kelp_trading_active"] = True
                    self.trader_data["kelp_price_interval_previous"] = self.trader_data[
                        "kelp_price_interval_current"]
                    self.trader_data["kelp_price_interval_current"] = [-9999999, 9999999]
                    mid_price = (best_bid + best_ask) / 2
                    self.trader_data["kelp_range_middle"] = mid_price

                current_range[1] = min(current_range[1], best_bid)
                current_range[0] = max(current_range[0], best_ask)

                if best_ask > range_high:
                    mid_price = (best_bid + best_ask) / 2
                    self.trader_data["kelp_range_middle"] = mid_price - 1
                elif best_bid < range_low:
                    mid_price = (best_bid + best_ask) / 2
                    self.trader_data["kelp_range_middle"] = mid_price + 1

                mid_price = self.trader_data["kelp_range_middle"]
                if self.trader_data["kelp_trading_active"] and state.timestamp > KELP_RANGE_INTERVAL:
                    # Sell if bid price higher than fair value
                    if max_bid > mid_price:
                        max_sell_volume = POSITION_LIMIT + current_position
                        sell_quantity = min(max_bid_volume, max_sell_volume)
                        orders.append(Order(product, max_bid, -sell_quantity))
                        print(f"SELL {sell_quantity}x {product} @ {max_bid}")

                    # Buy if ask price lower than fair value
                    elif min_ask < mid_price:
                        max_buy_volume = POSITION_LIMIT - current_position
                        buy_quantity = min(min_ask_volume, max_buy_volume)
                        orders.append(Order(product, min_ask, -buy_quantity))
                        print(f"BUY {buy_quantity}x {product} @ {min_ask}")

                elif not self.trader_data["kelp_trading_active"]:
                    # Cut losses - exit open position
                    if current_position > 0:
                        sell_quantity = current_position
                        if sell_quantity > 0:
                            orders.append(Order(product, best_bid + 1, -sell_quantity))

                    elif current_position < 0:
                        buy_quantity = current_position
                        if buy_quantity > 0:
                            orders.append(Order(product, best_ask - 1, buy_quantity))

            # --- 4. Store Orders (If Any) ---
            if orders:
                result[product] = orders

        # --- 5. Update and Serialize State ---
        self.trader_data["example_state"] += 1  # Track iterations
        trader_data_str = jsonpickle.encode(self.trader_data)

        return result, conversions, trader_data_str