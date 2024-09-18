# Importing the requests module
from typing import Literal
import requests
import pandas as pd


def get_klines(symbol: str,
               trade: Literal["spot", "future"] = "spot",
               interval: Literal["1m", "3m", "5m", "15m", "30m", "1h", "2h",
                                 "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M"] = "1m",
               limit: int = 1) -> list:

    request_path = f"https://www.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}" if trade == "spot" \
        else f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={limit}"

    result = requests.get(request_path, timeout=10)

    if result.status_code == 200:
        klines_data = result.json()
        for kline in klines_data:
            df = pd.DataFrame([{
                'time': pd.to_datetime(kline[0], unit='ms'),
                f'{trade}Open': float(kline[1]),
                f'{trade}High': float(kline[2]),
                f'{trade}Low': float(kline[3]),
                f'{trade}Close': float(kline[4]),
                f'{trade}Volume': float(kline[5]),
                f'{trade}QuoteAssetVolume': float(kline[7]),
                f'{trade}NumberOfTrades': kline[8],
                f'{trade}TakerBuyBaseAssetVolume': float(kline[9]),
                f'{trade}TakerBuyQuoteAssetVolume': float(kline[10])
            }])

            # Feature Engineering
            df['year'] = df['time'].dt.year
            df['month'] = df['time'].dt.month
            df['day'] = df['time'].dt.day
            df['hour'] = df['time'].dt.hour
            df['minute'] = df['time'].dt.minute
            df['dayOfWeek'] = df['time'].dt.dayofweek + \
                1  # Monday is 1, Sunday is 7
            df['isWeekend'] = df['dayOfWeek'].isin([6, 7]).astype(int)
            df['partOfMonth'] = pd.cut(df['day'], bins=[0, 10, 20, 31], labels=[
                'Early', 'Mid', 'Late'])
            df.drop(columns=['time'], inplace=True)

            return df.to_dict('records')
    else:
        return None


def get_cfd(symbol: str, period: Literal["MINUTE_15", "MINUTE_30", "HOUR_1", "HOUR_2", "HOUR_4", "DAY_1"] = "MINUTE_15"):
    result = requests.get(
        f'https://www.binance.com/bapi/earn/v1/public/indicator/capital-flow/info?period={period}&symbol={symbol}', timeout=10)

    if result.status_code == 200:
        data = result.json()['data']
        # Data Manipulation
        data = {k: v for k, v in data.items() if k not in [
            "id", "capitalFlowRuleId", "symbol", "capitalFlowPeriod", "createTimestamp", "updateTimestamp"]}
        return data
    else:
        return None


def get_mdd(symbol: str, trade: Literal["spot", "future"] = "spot", limit: int = 1000):
    request_path = f"https://www.binance.com/api/v3/depth?symbol={symbol}&limit={limit}" if trade == "spot" \
        else f"https://www.binance.com/fapi/v1/depth?symbol={symbol}&limit={limit}"

    result = requests.get(request_path, timeout=10)

    if result.status_code == 200:
        data = result.json()
        mdd = {}
        # ORDER BOOK BALANCE
        # Calculate total volume for bids and asks
        total_bid_volume = sum(float(bid[1]) for bid in data["bids"])
        total_ask_volume = sum(float(ask[1]) for ask in data["asks"])
        total_volume = total_bid_volume + total_ask_volume
        mdd[f'{trade}TotalBidVolumeRatio'] = total_bid_volume / total_volume
        mdd[f'{trade}TotalAskVolumeRatio'] = total_ask_volume / total_volume

        # PRICE MOVEMENTS
        # Calculating Potential Support and Resistance Levels
        df_bids = pd.DataFrame(data["bids"], columns=['price', 'volume'])
        df_asks = pd.DataFrame(data["asks"], columns=['price', 'volume'])

        # Convert price and volume to numeric for calculation
        df_bids[['price', 'volume']] = df_bids[[
            'price', 'volume']].apply(pd.to_numeric)
        df_asks[['price', 'volume']] = df_asks[[
            'price', 'volume']].apply(pd.to_numeric)

        # Aggregate volume at each price point
        bids_volume_by_price = df_bids.groupby(
            'price').sum().sort_values(by='volume', ascending=False)
        asks_volume_by_price = df_asks.groupby(
            'price').sum().sort_values(by='volume', ascending=False)

        # Identify top potential support and resistance levels (top 5 for each)
        for i, level in enumerate(bids_volume_by_price.head(
                5).index.values.tolist()):
            mdd[f'{trade}Support_{i}'] = level
        for i, level in enumerate(asks_volume_by_price.head(
                5).index.values.tolist()):
            mdd[f'{trade}Resistance_{i}'] = level

        # LIQUIDITY
        # Calculate the spread between the best bid and best ask
        best_bid_price = df_bids['price'].max()
        best_ask_price = df_asks['price'].min()
        mdd[f'{trade}Spread'] = best_ask_price - best_bid_price

        # Analyze volume depth near market price
        # Defining a range around the market price (for example, within 0.5% of the market price)
        market_price = (best_bid_price + best_ask_price) / 2
        price_range = market_price * 0.005  # 0.5% of market price

        # Volume within the defined range for bids and asks
        bids_near_market = df_bids[(df_bids['price'] >= market_price - price_range) &
                                   (df_bids['price'] <= market_price)]
        asks_near_market = df_asks[(df_asks['price'] <= market_price + price_range) &
                                   (df_asks['price'] >= market_price)]

        total_bids_volume_near_market = bids_near_market['volume'].sum()
        mdd[f'{trade}TotalBidsVolumeNearMarket'] = total_bids_volume_near_market / total_volume
        total_asks_volume_near_market = asks_near_market['volume'].sum()
        mdd[f'{trade}TotalAsksVolumeNearMarket'] = total_asks_volume_near_market / total_volume

        # Relative Distribution Analysis
        total_volume_bids = df_bids['volume'].sum()
        total_volume_asks = df_asks['volume'].sum()
        df_bids['relative_volume'] = (
            df_bids['volume'] / total_volume_bids) * 100
        df_asks['relative_volume'] = (
            df_asks['volume'] / total_volume_asks) * 100

        # Percentage Distribution Analysis
        num_brackets = 10
        df_bids['price_bracket'] = pd.qcut(
            df_bids['price'], num_brackets, labels=False)
        df_asks['price_bracket'] = pd.qcut(
            df_asks['price'], num_brackets, labels=False)
        bids_volume_percentage = df_bids.groupby(
            'price_bracket')['volume'].sum() / total_volume_bids * 100
        for i, percentage in enumerate(bids_volume_percentage.values.tolist()):
            mdd[f'{trade}BidVolumePercentage_{i}'] = percentage
        asks_volume_percentage = df_asks.groupby(
            'price_bracket')['volume'].sum() / total_volume_asks * 100
        for i, percentage in enumerate(asks_volume_percentage.values.tolist()):
            mdd[f'{trade}AskVolumePercentage_{i}'] = percentage

        # Identify large orders and their potential price impact
        # Defining a large order threshold (e.g., orders in the top 5% of volume)
        large_order_threshold = 0.05
        large_bids = df_bids[df_bids['volume'] >=
                             df_bids['volume'].quantile(1 - large_order_threshold)]
        large_asks = df_asks[df_asks['volume'] >=
                             df_asks['volume'].quantile(1 - large_order_threshold)]

        # Calculating the potential price impact of these large orders
        # Assuming price impact is proportional to volume
        mdd[f'{trade}PriceImpactBids'] = (large_bids['volume'] *
                                          large_bids['price']).sum() / total_bid_volume
        mdd[f'{trade}PriceImpactAsks'] = (large_asks['volume'] *
                                          large_asks['price']).sum() / total_ask_volume

        # MARKET SENTIMENT ANALYSIS
        # Calculate total volumes and market price
        total_volume_bids = df_bids['volume'].sum()
        total_volume_asks = df_asks['volume'].sum()
        mdd[f'{trade}MarketPrice'] = (
            df_bids['price'].max() + df_asks['price'].min()) / 2

        # Bid-to-Ask Ratio
        mdd[f'{trade}BidToAskRatio'] = total_volume_bids / total_volume_asks

        # Identifying large orders
        large_order_threshold = 0.05
        large_bids = df_bids[df_bids['volume'] >=
                             df_bids['volume'].quantile(1 - large_order_threshold)]
        large_asks = df_asks[df_asks['volume'] >=
                             df_asks['volume'].quantile(1 - large_order_threshold)]
        mdd[f'{trade}LargeBidsCount'] = len(large_bids)
        mdd[f'{trade}LargeAsksCount'] = len(large_asks)

        # Depth Imbalance
        depth_ranges = [0.01, 0.02, 0.05]
        for depth_range in depth_ranges:
            bid_depth = df_bids[df_bids['price'] >=
                                market_price * (1 - depth_range)]['volume'].sum()
            ask_depth = df_asks[df_asks['price'] <=
                                market_price * (1 + depth_range)]['volume'].sum()
            mdd[f'{trade}DepthImbalance_{depth_range * 100}'] = bid_depth - ask_depth

        # Price Movement Trends
        bids_near_market = df_bids[(df_bids['price'] >= market_price * 0.995) &
                                   (df_bids['price'] <= market_price)]
        asks_near_market = df_asks[(df_asks['price'] <= market_price * 1.005) &
                                   (df_asks['price'] >= market_price)]
        mdd[f'{trade}BidsConcentrationNearMarketRatio'] = bids_near_market['volume'].sum(
        ) / total_bid_volume
        mdd[f'{trade}AsksConcentrationNearMarketRatio'] = asks_near_market['volume'].sum(
        ) / total_ask_volume

        # Potential Price Slippage
        # Calculating Volume-Weighted Average Price (VWAP) for Bids and Asks
        # VWAP calculation: Sum(Product of Price and Volume) / Sum(Volume) for a set number of orders
        # Setting a threshold for the number of top orders to consider for VWAP calculation
        top_order_threshold = 100  # example: top 100 orders
        # Calculating VWAP for bids and asks
        mdd[f'{trade}VwapBids'] = (df_bids.head(top_order_threshold)['price'] * df_bids.head(top_order_threshold)['volume']).sum() / \
            df_bids.head(top_order_threshold)['volume'].sum()
        mdd[f'{trade}VwapAsks'] = (df_asks.head(top_order_threshold)['price'] * df_asks.head(top_order_threshold)['volume']).sum() / \
            df_asks.head(top_order_threshold)['volume'].sum()

        # Cumulative Order Depth Analysis
        # Calculating how much the price would move to fill a large order
        def calculate_price_movement_for_large_orders(order_book, market_price, percentile_thresholds, volume_threshold, is_bid=True):
            price_movements = {}

            # Identify large orders based on percentiles and absolute size
            for percentile in percentile_thresholds:
                order_size_at_percentile = order_book['volume'].quantile(
                    percentile)
                # if order_size_at_percentile >= volume_threshold:
                cumulative_volume = 0
                price_movement = 0

                for _, row in order_book.iterrows():
                    cumulative_volume += row['volume']
                    if cumulative_volume >= order_size_at_percentile:
                        price_movement = row['price']
                        break

                if is_bid:
                    price_delta = market_price - price_movement  # Price decrease for bids
                else:
                    price_delta = price_movement - market_price  # Price increase for asks

                price_movements[percentile] = price_delta

            return price_movements

        # Define percentiles and a minimum volume threshold for considering an order large
        percentiles = [0.95, 0.99]
        minimum_large_order_volume = 1  # This is an example threshold and can be adjusted

        # Calculate price movements for large bid and ask orders
        price_movement_bid_range = calculate_price_movement_for_large_orders(
            df_bids, market_price, percentiles, minimum_large_order_volume, is_bid=True)
        for key, value in price_movement_bid_range.items():
            mdd[f'{trade}LargeBidPriceMovementRange_{key * 100}'] = value
        price_movement_ask_range = calculate_price_movement_for_large_orders(
            df_asks, market_price, percentiles, minimum_large_order_volume, is_bid=False)
        for key, value in price_movement_ask_range.items():
            mdd[f'{trade}LargeAskPriceMovementRange_{key * 100}'] = value

        # WHALE ACTIVITY
        # Identifying and Analyzing Large Orders for Whale Activity
        # Define a threshold for large orders (e.g., top 1% of orders)
        large_order_percentile_threshold = 0.99
        large_order_size_bid = df_bids['volume'].quantile(
            large_order_percentile_threshold)
        large_order_size_ask = df_asks['volume'].quantile(
            large_order_percentile_threshold)

        # Extract large orders from bids and asks
        large_bids = df_bids[df_bids['volume'] >= large_order_size_bid]
        large_asks = df_asks[df_asks['volume'] >= large_order_size_ask]

        # Analysis of Large Order Concentration
        # Distribution of large orders across different price levels
        large_bids_distribution = large_bids.groupby('price').sum()
        large_asks_distribution = large_asks.groupby('price').sum()

        # Comparison with Average Order Size
        average_order_size_bid = df_bids['volume'].mean()
        average_order_size_ask = df_asks['volume'].mean()
        large_bids_relative_size = large_bids['volume'] / \
            average_order_size_bid
        large_asks_relative_size = large_asks['volume'] / \
            average_order_size_ask

        mdd[f'{trade}LargeBidsDistributionRatio'] = large_bids_distribution['volume'].sum(
        ) / total_bid_volume
        mdd[f'{trade}LargeAsksDistributionRatio'] = large_asks_distribution['volume'].sum(
        ) / total_ask_volume
        mdd[f'{trade}LargeBidsRelativeMeanSize'] = large_bids_relative_size.mean()
        mdd[f'{trade}LargeAsksRelativeMeanSize'] = large_asks_relative_size.mean()

        return mdd
    else:
        return None


def get_traders_stat(symbol: str,
                     stat: Literal["topAccounts", "topPositions",
                                   "globalAccounts"] = "globalAccounts",
                     period: Literal["5m", "15m", "30m", "1h",
                                     "2h", "4h", "6h", "12h", "1d"] = "5m",
                     limit: int = 1):

    if stat == "topAccounts":
        request_path = f"https://fapi.binance.com/futures/data/topLongShortAccountRatio?symbol={symbol}&period={period}&limit={limit}"
    elif stat == "topPositions":
        request_path = f"https://fapi.binance.com/futures/data/topLongShortPositionRatio?symbol={symbol}&period={period}&limit={limit}"
    else:
        request_path = f"https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol={symbol}&period={period}&limit={limit}"

    result = requests.get(request_path, timeout=10)

    if result.status_code == 200:
        traders_data = result.json()
        ts = {f"{stat}{k.capitalize().replace('account', '').replace('position', '')}": float(
            v) for k, v in traders_data[0].items() if k not in ["symbol", "timestamp"]}

        return ts

    return None


def get_recent_trades(symbol: str, trade: Literal["spot", "future"] = "spot", limit: int = 1000):
    request_path = f"https://www.binance.com/api/v3/trades?symbol={symbol}&limit={limit}" if trade == "spot" \
        else f"https://fapi.binance.com/fapi/v1/trades?symbol={symbol}&limit={limit}"

    result = requests.get(request_path, timeout=10)

    if result.status_code == 200:
        trades_data = result.json()
        rtd = {}
        # Convert the trades data into a DataFrame
        df_trades = pd.DataFrame(trades_data)

        # Convert 'time' from Unix timestamp (milliseconds) to a human-readable format
        df_trades['time'] = pd.to_datetime(df_trades['time'], unit='ms')

        # Convert 'price', 'qty', and 'quoteQty' to numeric
        df_trades[['price', 'qty', 'quoteQty']] = df_trades[[
            'price', 'qty', 'quoteQty']].apply(pd.to_numeric)

        # Calculate additional features
        total_trade_volume = df_trades['qty'].sum()
        average_trade_price = (
            df_trades['price'] * df_trades['qty']).sum() / total_trade_volume
        trade_frequency = df_trades['time'].diff().mean()
        # Proportion of trades where buyer is the maker
        buyer_maker_ratio = df_trades['isBuyerMaker'].mean()

        rtd[f'{trade}TotalTradeVolume'] = total_trade_volume
        rtd[f'{trade}AverageTradePrice'] = average_trade_price
        rtd[f'{trade}TradeFrequency(sec)'] = trade_frequency.total_seconds()
        rtd[f'{trade}BuyerMakerRatio'] = buyer_maker_ratio

        return rtd

    return None
