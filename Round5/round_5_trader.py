import json
from typing import Any, Dict, List
import jsonpickle
import numpy as np

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
        lo, hi = 0, min(len(value), max_length)
        out = ""

        while lo <= hi:
            mid = (lo + hi) // 2

            candidate = value[:mid]
            if len(candidate) < len(value):
                candidate += "..."

            encoded_candidate = json.dumps(candidate)

            if len(encoded_candidate) <= max_length:
                out = candidate
                lo = mid + 1
            else:
                hi = mid - 1
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
            "entry_price": None,  # Track entry price for exits

            # Pairs trading
            # Picnice baskets
            "pair_symbols": ("PICNIC_BASKET1", "PICNIC_BASKET2"),  # Asset pair
            "spread_window": 50,  # Lookback window for spread mean/std
            "entry_z": 1.5,  # Enter trade when Z-score > |1.5|
            "exit_z": 0.5,  # Exit trade when Z-score < |0.5|
            "picnic_spread_history": [],  # Tracks historical spreads
            "basket1_mid": 0,
            "basket2_mid": 0,

            # Djembes and jams rock vouchers
            "pair_symbols_dj": ("DJEMBES", "JAMS"),  # Asset pair
            "spread_window_dj": 50,  # Lookback window for spread mean/std
            "entry_z_dj": 1.5,  # Enter trade when Z-score > |1.5|
            "exit_z_dj": 0.5,  # Exit trade when Z-score < |0.5|
            "spread_history_dj": [],  # Tracks historical spreads
            "djembes_mid": 0,
            "jams_mid": 0,

            # VWAP
            "djembe_price_volume": [],  # Stores (price, volume) tuples
            "current_vwap": None,
            "entry_vwap": None,

            "jams_price_history": [],

            #
        }

        # Set constants and parameters
        self.POSITION_LIMIT = 50


        self.CROISSANTS_LIMIT = 250
        self.JAMS_LIMIT = 350
        self.DJEMBES_LIMIT = 60
        self.PICNIC_BASKET1_LIMIT = 60
        self.PICNIC_BASKET2_LIMIT = 100
        self.MAGNIFICENT_MACARON_LIMIT = 75

        self.KELP_RANGE_INTERVAL = 2000  # ms time intervals for ranges
        self.KELP_RANGE_PM = 0

        self.LOOKBACK_PERIOD = 300  # Momentum calculation window
        self.TREND_THRESHOLD = 0.01

        self.vwap_window = 50  # Number of timesteps to calculate VWAP
        self.volume_participation = 0.5  # % of available volume to take

        self.EXIT = False

    def calculate_vwap(self, price_volume_data):
        total_volume = sum(vol for (_, vol) in price_volume_data)
        if total_volume == 0:
            return None
        return sum(price * vol for (price, vol) in price_volume_data) / total_volume


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
            print("Bids:", order_depth.buy_orders)
            print("Asks:", order_depth.sell_orders)

            max_bid = max(order_depth.buy_orders) if order_depth.buy_orders else 0
            max_bid_volume = order_depth.buy_orders[max_bid] if order_depth.buy_orders else 0

            min_ask = min(order_depth.sell_orders) if order_depth.sell_orders else 0
            min_ask_volume = abs(order_depth.sell_orders[min_ask]) if order_depth.sell_orders else 0

            # Resin trading strategy
            if product == "RAINFOREST_RESIN":
                fair_value = 10000

                # Sell if bid price higher than fair value
                if max_bid > fair_value:
                    max_sell_volume = self.POSITION_LIMIT + current_position
                    sell_quantity = min(max_bid_volume, max_sell_volume)
                    orders.append(Order(product, max_bid, -max_sell_volume))

                # Buy if ask price lower than fair value
                elif min_ask < fair_value:
                    max_buy_volume = self.POSITION_LIMIT - current_position
                    buy_quantity = min(min_ask_volume, max_buy_volume)
                    orders.append(Order(product, min_ask, max_buy_volume))

            # Kelp trading strategy
            elif product == "KELP":
                mid_price = self.trader_data["kelp_range_middle"]
                current_range = self.trader_data["kelp_price_interval_current"]
                previous_range = self.trader_data["kelp_price_interval_previous"]
                spread = abs(previous_range[0] - previous_range[1])
                range_high = mid_price + spread/2 + self.KELP_RANGE_PM
                range_low = mid_price - spread/2 - self.KELP_RANGE_PM

                if state.timestamp % self.KELP_RANGE_INTERVAL == 0:
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
                if self.trader_data["kelp_trading_active"] and state.timestamp > self.KELP_RANGE_INTERVAL:
                    # Sell if bid price higher than fair value
                    if max_bid > mid_price:
                        max_sell_volume = self.POSITION_LIMIT + current_position
                        sell_quantity = min(max_bid_volume, max_sell_volume)
                        orders.append(Order(product, max_bid, -max_sell_volume))

                    # Buy if ask price lower than fair value
                    elif min_ask < mid_price:
                        max_buy_volume = self.POSITION_LIMIT - current_position
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
            elif product == "SQUID_INKK":
                mid_price = (max_bid + min_ask) / 2
                ma = np.mean(self.trader_data["price_history"][-10:])  # 10-period MA

                # Update price history
                self.trader_data["price_history"].append(mid_price)
                while len(self.trader_data["price_history"]) > self.LOOKBACK_PERIOD:
                    self.trader_data["price_history"].pop(0)

                # Calculate momentum
                momentum = 0
                #if len(self.trader_data["price_history"]) == self.LOOKBACK_PERIOD:
                old_price = self.trader_data["price_history"][0]
                momentum = (mid_price - old_price) / old_price

                # Determine position direction
                target_position = 0

                if momentum > self.TREND_THRESHOLD and mid_price > ma:  # Strong uptrend
                    target_position = self.POSITION_LIMIT
                elif momentum < -self.TREND_THRESHOLD and mid_price < ma:  # Strong downtrend
                    target_position = -self.POSITION_LIMIT

                # Generate orders
                position_change = target_position - current_position

                if current_position == 0:
                    if position_change > 0:  # We want to buy
                        orders.append(Order(product, min_ask, position_change))
                        self.trader_data["entry_price"] = min_ask

                    elif position_change < 0:  # We want to sell
                        orders.append(Order(product, max_bid, position_change))
                        self.trader_data["entry_price"] = max_bid



                # Profit taking/stop loss
                if self.trader_data["entry_price"]:
                    returns = (mid_price - self.trader_data["entry_price"]) / self.trader_data["entry_price"]

                    # Long exit
                    if current_position > 0 and (returns > 0.02 or returns < -0.01):
                        orders.append(Order(product, max_bid, -current_position))

                    # Short exit
                    elif current_position < 0 and (returns < -0.02 or returns > 0.01):
                        orders.append(Order(product, min_ask, -current_position))

            # Picnic baskets strategy
            elif product == "PICNIC_BASKET2" or product == "PICNIC_BASKET1":
                # Check if both baskets exist in the order book
                basket1_data = state.order_depths.get("PICNIC_BASKET1", None)
                basket2_data = state.order_depths.get("PICNIC_BASKET2", None)

                if basket1_data and basket2_data:
                    # Calculate mid-prices
                    if basket1_data.buy_orders and basket1_data.sell_orders:
                        self.trader_data["basket1_mid"] = (max(basket1_data.buy_orders) + min(basket1_data.sell_orders)) / 2
                    if basket2_data.buy_orders and basket2_data.sell_orders:
                        self.trader_data["basket2_mid"] = (max(basket2_data.buy_orders) + min(basket2_data.sell_orders)) / 2

                    # Calculate spread (simple price difference)
                    spread = self.trader_data["basket1_mid"] - self.trader_data["basket2_mid"]
                    self.trader_data["picnic_spread_history"].append(spread)
                    if len(self.trader_data["picnic_spread_history"]) > self.trader_data["spread_window"]:
                        self.trader_data["picnic_spread_history"].pop(0)

                    # Compute Z-score if enough data
                    if len(self.trader_data["picnic_spread_history"]) >= self.trader_data["spread_window"]:
                        spread_mean = np.mean(self.trader_data["picnic_spread_history"])
                        spread_std = np.std(self.trader_data["picnic_spread_history"])
                        z_score = (spread - spread_mean) / spread_std if spread_std != 0 else 0

                        # Get current positions
                        basket1_pos = state.position.get("PICNIC_BASKET1", 0)
                        basket2_pos = state.position.get("PICNIC_BASKET2", 0)


                        # Trading signals
                        if z_score > self.trader_data["entry_z"] and basket1_pos == 0:
                            # Short PICNIC_BASKET1, Long PICNIC_BASKET2 (spread too wide)
                            max_sell_volume = self.PICNIC_BASKET1_LIMIT + basket1_pos
                            result["PICNIC_BASKET1"] = [
                                Order("PICNIC_BASKET1", min(basket1_data.sell_orders), -self.PICNIC_BASKET1_LIMIT)]
                            max_buy_volume = self.PICNIC_BASKET2_LIMIT - basket2_pos
                            result["PICNIC_BASKET2"] = [
                                Order("PICNIC_BASKET2", max(basket2_data.buy_orders), self.PICNIC_BASKET2_LIMIT)]

                        elif z_score < -self.trader_data["entry_z"] and basket2_pos == 0:
                            # Long PICNIC_BASKET1, Short PICNIC_BASKET2 (spread too narrow)
                            max_buy_volume = self.PICNIC_BASKET1_LIMIT - basket1_pos
                            result["PICNIC_BASKET1"] = [
                                Order("PICNIC_BASKET1", max(basket1_data.buy_orders), self.PICNIC_BASKET1_LIMIT)]
                            max_sell_volume = self.PICNIC_BASKET2_LIMIT + basket2_pos
                            result["PICNIC_BASKET2"] = [
                                Order("PICNIC_BASKET2", min(basket2_data.sell_orders), -self.PICNIC_BASKET2_LIMIT)]

                        elif abs(z_score) < self.trader_data["exit_z"]:
                            # Close positions (spread reverted)
                            if basket1_pos > 0:
                                result["PICNIC_BASKET1"] = [
                                    Order("PICNIC_BASKET1", min(basket1_data.sell_orders), -basket1_pos)]
                            elif basket1_pos < 0:
                                result["PICNIC_BASKET1"] = [
                                    Order("PICNIC_BASKET1", max(basket1_data.buy_orders), -basket1_pos)]

                            if basket2_pos > 0:
                                result["PICNIC_BASKET2"] = [
                                    Order("PICNIC_BASKET2", min(basket2_data.sell_orders), -basket2_pos)]
                            elif basket2_pos < 0:
                                result["PICNIC_BASKET2"] = [
                                    Order("PICNIC_BASKET2", max(basket2_data.buy_orders), -basket2_pos)]

            elif product == "DJEMBESS":
                # Only process when we have valid market data
                if max_bid and min_ask:
                    mid_price = (max_bid + min_ask) / 2
                    total_volume = max_bid_volume + min_ask_volume
                    self.trader_data["djembe_price_volume"].append((mid_price, total_volume))

                    # Maintain rolling window
                    if len(self.trader_data["djembe_price_volume"]) > self.vwap_window:
                        self.trader_data["djembe_price_volume"].pop(0)

                    # Calculate VWAP if we have enough data
                    if len(self.trader_data["djembe_price_volume"]) >= 5:  # Minimum 5 periods
                        self.trader_data["current_vwap"] = self.calculate_vwap(self.trader_data["djembe_price_volume"])

                # Trading logic when we have VWAP and market prices
                if self.trader_data["current_vwap"] and max_bid and min_ask:
                    orders = []

                    # Buy signal (price below VWAP with available liquidity)
                    if min_ask < self.trader_data["current_vwap"] and min_ask_volume > 0:
                        max_buy_size = min(
                            self.DJEMBES_LIMIT - current_position,
                            int(min_ask_volume * self.volume_participation),
                            min_ask_volume  # Absolute limit
                        )
                        if max_buy_size > 0:
                            orders.append(Order("DJEMBES", min_ask, max_buy_size))

                    # Sell signal (price above VWAP with available liquidity)
                    elif max_bid > self.trader_data["current_vwap"] and max_bid_volume > 0:
                        max_sell_size = min(
                            self.DJEMBES_LIMIT + current_position,
                            int(max_bid_volume * self.volume_participation),
                            max_bid_volume  # Absolute limit
                        )
                        if max_sell_size > 0:
                            orders.append(Order("DJEMBES", max_bid, -max_sell_size))

                    # Position management
                    if current_position != 0:
                        # Initialize entry VWAP if not set
                        if not self.trader_data["entry_vwap"]:
                            self.trader_data["entry_vwap"] = self.trader_data["current_vwap"]

                        # Take profit or stop loss conditions
                        take_profit = False
                        stop_loss = False

                        if current_position > 0:  # Long position
                            take_profit = max_bid > self.trader_data["entry_vwap"] * 1.015
                            stop_loss = min_ask < self.trader_data["entry_vwap"] * 0.99
                        else:  # Short position
                            take_profit = min_ask < self.trader_data["entry_vwap"] * 0.985
                            stop_loss = max_bid > self.trader_data["entry_vwap"] * 1.01

                        if take_profit or stop_loss:
                            close_price = max_bid if current_position > 0 else min_ask
                            orders.append(Order("DJEMBES", close_price, -current_position))
                            self.trader_data["entry_vwap"] = None

            elif product == "DJEMBES" or product == "CROISSANTS":
                # Check if both products exist in the order book
                basket1_data = state.order_depths.get("DJEMBES", None)
                basket2_data = state.order_depths.get("CROISSANTS", None)

                if basket1_data and basket2_data:
                    # Calculate mid-prices
                    if basket1_data.buy_orders and basket1_data.sell_orders:
                        self.trader_data["djembes_mid"] = (max(basket1_data.buy_orders) + min(
                            basket1_data.sell_orders)) / 2
                    if basket2_data.buy_orders and basket2_data.sell_orders:
                        self.trader_data["jams_mid"] = (max(basket2_data.buy_orders) + min(
                            basket2_data.sell_orders)) / 2

                    # Calculate spread (simple price difference)
                    spread = self.trader_data["djembes_mid"] - self.trader_data["jams_mid"]
                    self.trader_data["spread_history_dj"].append(spread)
                    if len(self.trader_data["spread_history_dj"]) > self.trader_data["spread_window_dj"]:
                        self.trader_data["spread_history_dj"].pop(0)

                    # Compute Z-score if enough data
                    if len(self.trader_data["spread_history_dj"]) >= self.trader_data["spread_window_dj"]:
                        spread_mean = np.mean(self.trader_data["spread_history_dj"])
                        spread_std = np.std(self.trader_data["spread_history_dj"])
                        z_score = (spread - spread_mean) / spread_std if spread_std != 0 else 0

                        # Get current positions
                        basket1_pos = state.position.get("DJEMBES", 0)
                        basket2_pos = state.position.get("CROISSANTS", 0)

                        # Trading signals
                        if z_score > self.trader_data["entry_z_dj"] and basket1_pos == 0:
                            # Short PICNIC_BASKET1, Long PICNIC_BASKET2 (spread too wide)
                            max_sell_volume = self.DJEMBES_LIMIT + basket1_pos
                            result["DJEMBES"] = [
                                Order("DJEMBES", min(basket1_data.sell_orders) - 2, -max_sell_volume)]
                            max_buy_volume = self.CROISSANTS_LIMIT - basket2_pos
                            result["CROISSANTS"] = [
                                Order("CROISSANTS", max(basket2_data.buy_orders) + 2, max_buy_volume)]

                        elif z_score < -self.trader_data["entry_z_dj"] and basket2_pos == 0:
                            # Long PICNIC_BASKET1, Short PICNIC_BASKET2 (spread too narrow)
                            max_buy_volume = self.DJEMBES_LIMIT - basket1_pos
                            result["DJEMBES"] = [
                                Order("DJEMBES", max(basket1_data.buy_orders) - 2, max_buy_volume)]
                            max_sell_volume = self.CROISSANTS_LIMIT + basket2_pos
                            result["CROISSANTS"] = [
                                Order("CROISSANTS", min(basket2_data.sell_orders) + 2, -max_sell_volume)]



                        elif abs(z_score) < self.trader_data["exit_z_dj"]:
                            # Close positions (spread reverted)
                            if basket1_pos > 0:
                                result["DJEMBES"] = [
                                    Order("DJEMBES", min(basket1_data.sell_orders), -basket1_pos)]
                            elif basket1_pos < 0:
                                result["DJEMBES"] = [
                                    Order("DJEMBES", max(basket1_data.buy_orders), -basket1_pos)]

                            if basket2_pos > 0:
                                result["CROISSANTS"] = [
                                    Order("CROISSANTS", min(basket2_data.sell_orders), -basket2_pos)]
                            elif basket2_pos < 0:
                                result["CROISSANTS"] = [
                                    Order("CROISSANTS", max(basket2_data.buy_orders), -basket2_pos)]
            elif product == "MAGNIFICENT_MACARONS":
                CSI = 44
                EXIT1 = 49
                EXIT2 = 32

                sunlight = state.observations.conversionObservations.get(product).sunlightIndex if state.observations.conversionObservations.get(product) else 100


                if sunlight <= CSI and current_position == 0 and len(order_depth.sell_orders) > 0 and not self.EXIT:
                    # Buy
                    orders.append(Order(product, min_ask + 20, self.MAGNIFICENT_MACARON_LIMIT))
                elif sunlight > CSI and current_position == 0:
                    self.EXIT = False

                if current_position > 0 and len(order_depth.buy_orders) > 0:
                    # Close all positions
                    if sunlight >= EXIT1 or sunlight <= EXIT2:
                        self.EXIT = True
                        orders.append(Order(product, max_bid, -current_position))
                    #elif sunlight <= EXIT2:
                    #    orders.append(Order(product, max_bid, -current_position))





            # --- 4. Store Orders (If Any) ---
            if orders:
                result[product] = orders

        # --- 5. Update and Serialize State ---
        self.trader_data["example_state"] += 1  # Track iterations
        trader_data_str = jsonpickle.encode(self.trader_data)

        logger.flush(state, result, conversions, trader_data_str)

        return result, conversions, trader_data_str