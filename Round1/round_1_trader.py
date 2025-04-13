import json
from typing import Any, Dict, List
import jsonpickle

from datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState


class Logger:
    def __init__(self) -> None:
        self.logs = ""
        self.max_log_length = 3750

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(self, state: TradingState, orders: dict[Symbol, list[Order]], conversions: int, trader_data: str) -> None:
        base_length = len(
            self.to_json(
                [
                    self.compress_state(state, ""),
                    self.compress_orders(orders),
                    conversions,
                    "",
                    "",
                ]
            )
        )

        # We truncate state.traderData, trader_data, and self.logs to the same max. length to fit the log limit
        max_item_length = (self.max_log_length - base_length) // 3

        print(
            self.to_json(
                [
                    self.compress_state(state, self.truncate(state.traderData, max_item_length)),
                    self.compress_orders(orders),
                    conversions,
                    self.truncate(trader_data, max_item_length),
                    self.truncate(self.logs, max_item_length),
                ]
            )
        )

        self.logs = ""

    def compress_state(self, state: TradingState, trader_data: str) -> list[Any]:
        return [
            state.timestamp,
            trader_data,
            self.compress_listings(state.listings),
            self.compress_order_depths(state.order_depths),
            self.compress_trades(state.own_trades),
            self.compress_trades(state.market_trades),
            state.position,
            self.compress_observations(state.observations),
        ]

    def compress_listings(self, listings: dict[Symbol, Listing]) -> list[list[Any]]:
        compressed = []
        for listing in listings.values():
            compressed.append([listing.symbol, listing.product, listing.denomination])

        return compressed

    def compress_order_depths(self, order_depths: dict[Symbol, OrderDepth]) -> dict[Symbol, list[Any]]:
        compressed = {}
        for symbol, order_depth in order_depths.items():
            compressed[symbol] = [order_depth.buy_orders, order_depth.sell_orders]

        return compressed

    def compress_trades(self, trades: dict[Symbol, list[Trade]]) -> list[list[Any]]:
        compressed = []
        for arr in trades.values():
            for trade in arr:
                compressed.append(
                    [
                        trade.symbol,
                        trade.price,
                        trade.quantity,
                        trade.buyer,
                        trade.seller,
                        trade.timestamp,
                    ]
                )

        return compressed

    def compress_observations(self, observations: Observation) -> list[Any]:
        conversion_observations = {}
        for product, observation in observations.conversionObservations.items():
            conversion_observations[product] = [
                observation.bidPrice,
                observation.askPrice,
                observation.transportFees,
                observation.exportTariff,
                observation.importTariff,
                observation.sugarPrice,
                observation.sunlightIndex,
            ]

        return [observations.plainValueObservations, conversion_observations]

    def compress_orders(self, orders: dict[Symbol, list[Order]]) -> list[list[Any]]:
        compressed = []
        for arr in orders.values():
            for order in arr:
                compressed.append([order.symbol, order.price, order.quantity])

        return compressed

    def to_json(self, value: Any) -> str:
        return json.dumps(value, cls=ProsperityEncoder, separators=(",", ":"))

    def truncate(self, value: str, max_length: int) -> str:
        if len(value) <= max_length:
            return value

        return value[: max_length - 3] + "..."
logger = Logger()


class Trader:
    def __init__(self):
        # Initialize default state (only for local testing)
        self.trader_data = {
            "example_state": 0,
            "kelp_price_interval_previous": [0, 0],
            "kelp_price_interval_current": [-9999999, 9999999],
            "kelp_range_middle": 0,
            "kelp_trading_active": True,
            "price_history": [],  # Stores last 50 mid-prices
            "entry_price": None  # Track entry price for exits
        }
        self.LOOKBACK_PERIOD = 50  # Momentum calculation window
        self.POSITION_LIMIT = 50  # Max position size
        self.TREND_THRESHOLD = 0.01


    def run(self, state: TradingState) -> tuple[Dict[str, List[Order]], int, str]:
        """
        Processes market data and returns orders.
        :param state: Contains order book, positions, and traderData
        :return: (orders, conversions, traderData)
        """
        # Set constants and parameters
        POSITION_LIMIT = 50
        KELP_RANGE_INTERVAL = 2000  # ms time intervals for ranges
        KELP_RANGE_PM = 0

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
            min_ask_volume = abs(order_depth.sell_orders[min_ask])

            # Resin trading strategy
            if product == "RAINFOREST_RESINN":
                fair_value = 10000

                # Sell if bid price higher than fair value
                if max_bid > fair_value:
                    max_sell_volume = POSITION_LIMIT + current_position
                    sell_quantity = min(max_bid_volume, max_sell_volume)
                    orders.append(Order(product, max_bid, -max_sell_volume))

                # Buy if ask price lower than fair value
                elif min_ask < fair_value:
                    max_buy_volume = POSITION_LIMIT - current_position
                    buy_quantity = min(min_ask_volume, max_buy_volume)
                    orders.append(Order(product, min_ask, max_buy_volume))

            # Kelp trading strategy
            elif product == "KELP":
                mid_price = self.trader_data["kelp_range_middle"]
                current_range = self.trader_data["kelp_price_interval_current"]
                previous_range = self.trader_data["kelp_price_interval_previous"]
                spread = abs(previous_range[0] - previous_range[1])
                range_high = mid_price + spread/2 + KELP_RANGE_PM
                range_low = mid_price - spread/2 - KELP_RANGE_PM

                if state.timestamp % KELP_RANGE_INTERVAL == 0:
                    # Start new interval
                    self.trader_data["kelp_trading_active"] = True
                    self.trader_data["kelp_price_interval_previous"] = self.trader_data["kelp_price_interval_current"]
                    self.trader_data["kelp_price_interval_current"] = [-9999999, 9999999]
                    mid_price = (max_bid + min_ask) / 2
                    self.trader_data["kelp_range_middle"] = mid_price

                current_range[1] = min(current_range[1], max_bid)
                current_range[0] = max(current_range[0], min_ask)

                if min_ask > range_high:
                    mid_price = (max_bid + min_ask) / 2
                    self.trader_data["kelp_price_interval_previous"][0] = min_ask
                    self.trader_data["kelp_range_middle"] = mid_price
                elif max_bid < range_low:
                    mid_price = (max_bid + min_ask) / 2
                    self.trader_data["kelp_price_interval_previous"][1] = max_bid
                    self.trader_data["kelp_range_middle"] = mid_price


                mid_price = self.trader_data["kelp_range_middle"]
                if self.trader_data["kelp_trading_active"] and state.timestamp > KELP_RANGE_INTERVAL:
                    # Sell if bid price higher than fair value
                    if max_bid > mid_price:
                        max_sell_volume = POSITION_LIMIT + current_position
                        sell_quantity = min(max_bid_volume, max_sell_volume)
                        orders.append(Order(product, max_bid, -max_sell_volume))

                    # Buy if ask price lower than fair value
                    elif min_ask < mid_price:
                        max_buy_volume = POSITION_LIMIT - current_position
                        buy_quantity = min(min_ask_volume, -max_buy_volume)
                        orders.append(Order(product, min_ask, max_buy_volume))

                elif not self.trader_data["kelp_trading_active"]:
                    # Cut losses - exit open position
                    if current_position > 0:
                        sell_quantity = current_position
                        if sell_quantity > 0:
                            orders.append(Order(product, max_bid + 2, -sell_quantity))

                    elif current_position < 0:
                        buy_quantity = current_position
                        if buy_quantity > 0:
                            orders.append(Order(product, min_ask - 2, buy_quantity))

            # INK trading strategy
            elif product == "SQUID_INKk":
                mid_price = (max_bid + min_ask) / 2

                # Update price history
                self.trader_data["price_history"].append(mid_price)
                while len(self.trader_data["price_history"]) > self.LOOKBACK_PERIOD:
                    self.trader_data["price_history"].pop(0)

                # Calculate momentum
                momentum = 0
                if len(self.trader_data["price_history"]) == self.LOOKBACK_PERIOD:
                    old_price = self.trader_data["price_history"][0]
                    momentum = (mid_price - old_price) / old_price

                # Determine position direction
                target_position = 0

                if momentum > self.TREND_THRESHOLD:  # Strong uptrend
                    target_position = self.POSITION_LIMIT
                elif momentum < -self.TREND_THRESHOLD:  # Strong downtrend
                    target_position = -self.POSITION_LIMIT

                # Generate orders
                position_change = target_position - current_position

                if position_change > 0:  # We want to buy
                    max_buy_volume = POSITION_LIMIT - current_position
                    buy_quantity = min(min_ask_volume, max_buy_volume)
                    orders.append(Order(product, min_ask, position_change))
                    self.trader_data["entry_price"] = min_ask

                elif position_change < 0:  # We want to sell
                    max_sell_volume = POSITION_LIMIT + current_position
                    sell_quantity = min(max_bid_volume, max_sell_volume)
                    orders.append(Order(product, max_bid, -position_change))
                    self.trader_data["entry_price"] = max_bid



                # Profit taking/stop loss
                if self.trader_data["entry_price"]:
                    if current_position > 0:  # Long position
                        if mid_price > self.trader_data["entry_price"] * 1.02:  # % profit take
                            orders.append(Order(product, max_bid, -current_position))
                        elif mid_price < self.trader_data["entry_price"] * 0.99:  # % stop loss
                            orders.append(Order(product, max_bid, -current_position))

                    elif current_position < 0:  # Short position
                        if mid_price < self.trader_data["entry_price"] * 0.98:  # % profit take
                            orders.append(Order(product, min_ask, -current_position))
                        elif mid_price > self.trader_data["entry_price"] * 1.01:  # % stop loss
                            orders.append(Order(product, min_ask, -current_position))

                # Update entry price if position changed
                if orders:
                    self.trader_data["entry_price"] = mid_price



            # --- 4. Store Orders (If Any) ---
            if orders:
                result[product] = orders

        # --- 5. Update and Serialize State ---
        self.trader_data["example_state"] += 1  # Track iterations
        trader_data_str = jsonpickle.encode(self.trader_data)

        logger.flush(state, result, conversions, self.trader_data)

        return result, conversions, trader_data_str