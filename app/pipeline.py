import asyncio
from collections import OrderedDict
from typing import Literal, List

from app.scripts.data_collectors import get_klines, get_cfd, get_mdd, get_recent_trades, get_traders_stat


class DataCollectorPipeline:
    SHEET_NAMES = ["January", "February", "March", "April", "May", "June",
                   "July", "August", "September", "October", "November", "December"]

    def __init__(self, app, symbols: List[str], interval: Literal["1m", "3m", "5m", "15m", "30m", "1h", "2h",
                                                                  "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M"] = "1m") -> None:
        self.app = app
        self.symbols = symbols
        self.interval = interval
        self.symbol_folder_ids = {}

        # Initialization
        # Create main folder (Crypto Exchange, only binance for now)
        binance_folder_id = app.state.google_accessor.create_or_get_folder(
            "Binance")
        # Create all the folders for the symbols
        for symbol in symbols:
            self.symbol_folder_ids[symbol] = app.state.google_accessor.create_or_get_folder(
                symbol, binance_folder_id)

    async def tasks(self, symbol) -> dict:
        # 1. Extracting Klines
        spot_klines = get_klines(symbol, interval=self.interval)
        future_klines = get_klines(symbol, "future", interval=self.interval)
        klines = {**spot_klines[0], **future_klines[0]}

        # 2. Extracting Capital Flow Data
        capital_flow = get_cfd(symbol)

        # 3. Extracting Market Depth
        spot_market_depth = get_mdd(symbol)
        future_market_depth = get_mdd(symbol, "future")
        market_depth = {**spot_market_depth, **future_market_depth}

        # 4. Traders Statistics
        top_accounts = get_traders_stat(symbol, "topAccounts")
        top_positions = get_traders_stat(symbol, "topPositions")
        global_accounts = get_traders_stat(symbol, "globalAccounts")
        traders_stat = {**top_accounts, **top_positions, **global_accounts}

        # 5. Recent Trades
        spot_recent_trades = get_recent_trades(symbol)
        future_recent_trades = get_recent_trades(symbol, "future")
        recent_trades = {**spot_recent_trades, **future_recent_trades}

        # Combining all data
        data = {**klines, **capital_flow, **market_depth,
                **traders_stat, **recent_trades}

        return data

    async def insert_to_db(self, symbol, data):
        # Create or Get Reference of spreadsheet (by year)
        spreadsheet_id = self.app.state.google_accessor.create_or_get_spreadsheet_in_folder(data['year'],
                                                                                            self.symbol_folder_ids[symbol],
                                                                                            tuple(
                                                                                                DataCollectorPipeline.SHEET_NAMES),
                                                                                            tuple(data.keys()))
        # Call append data on the spreadsheet
        self.app.state.google_accessor.add_row_data(
            spreadsheet_id,
            DataCollectorPipeline.SHEET_NAMES[data['month'] - 1],
            [list(data.values())])

    async def handle_symbol(self, symbol):
        data = await self.tasks(symbol)
        await self.insert_to_db(symbol, data)

    async def run(self):
        try:
            tasks = [self.handle_symbol(symbol) for symbol in self.symbols]
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            print("Task Interrupted\nStopping Data Collection ...")
            exit(0)
