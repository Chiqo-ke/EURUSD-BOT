import sys
import os
import logging
import time
import json
from datetime import datetime
import pandas as pd
import talib
import MetaTrader5 as mt5
import config

class RealTimeTrader:
    """A real-time trading system with detailed event logging and MT5 execution."""

    def __init__(self):
        """Initializes the trading system, logging, and MT5 connection."""
        self.setup_logging()
        self.logger.info("--- Initializing Real-Time Trading System ---")
        self.initialized = self.initialize_mt5()
        if not self.initialized:
            self.logger.critical("System initialization failed due to MT5 connection error.")
            return

        # Data and state storage
        self.dataframes = {}
        self.last_processed_times = {}
        self.active_positions = {}
        self.active_trends = {}

        # Trading parameters from config
        self.bb_period = config.BB_TIMEPERIOD
        self.bb_std_dev_up = config.BB_NBDEVUP
        self.bb_std_dev_dn = config.BB_NBDEVDN
        self.bb_matype = config.BB_MATYPE
        self.uptrend_volume_threshold = config.UPTREND_VOL_THRESHOLD
        self.downtrend_volume_threshold = config.DOWNTREND_VOL_THRESHOLD
        self.sl_pips = config.SL_PIPS
        self.tp_pips = config.TP_PIPS
        self.ema_period = config.EMA_PERIOD
        self.ema_threshold_pips = config.EMA_THRESHOLD_PIPS
        self.pip_size = config.PIP_SIZE
        self.lot_size = config.LOT_SIZE
        self.max_concurrent_trades = config.MAX_CONCURRENT_TRADES

        # Parameters not in config
        self.ema_tp_period = 50
        self.magic_number = 234000
        self.check_interval = 5 # seconds

    def setup_logging(self):
        """Creates logging infrastructure with general, trade, and pattern logs."""
        log_dir = 'logs'
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        today = datetime.now().strftime('%Y%m%d')
        log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # 1. General System Logger
        self.logger = logging.getLogger('TradingSystem')
        self.logger.setLevel(logging.DEBUG)
        if not self.logger.handlers:
            # File handler
            system_log_file = os.path.join(log_dir, f'trading_system_{today}.log')
            fh = logging.FileHandler(system_log_file)
            fh.setFormatter(log_format)
            self.logger.addHandler(fh)
            # Console handler
            ch = logging.StreamHandler(sys.stdout)
            ch.setFormatter(log_format)
            ch.setLevel(logging.DEBUG)
            self.logger.addHandler(ch)

        # 2. Trade Execution Logger
        self.trade_logger = logging.getLogger('Trades')
        self.trade_logger.setLevel(logging.INFO)
        if not self.trade_logger.handlers:
            trade_log_file = os.path.join(log_dir, f'trades_{today}.log')
            fh_trade = logging.FileHandler(trade_log_file)
            fh_trade.setFormatter(log_format)
            self.trade_logger.addHandler(fh_trade)

        # 3. Pattern Detection Logger
        self.pattern_logger = logging.getLogger('Patterns')
        self.pattern_logger.setLevel(logging.INFO)
        if not self.pattern_logger.handlers:
            pattern_log_file = os.path.join(log_dir, f'patterns_{today}.log')
            fh_pattern = logging.FileHandler(pattern_log_file)
            fh_pattern.setFormatter(log_format)
            self.pattern_logger.addHandler(fh_pattern)

    def initialize_mt5(self):
        """Establishes and verifies the MetaTrader 5 connection."""
        self.logger.info("Attempting to initialize MT5 connection...")
        if not mt5.initialize(login=config.MT5_LOGIN, password=config.MT5_PASSWORD, server=config.MT5_SERVER):
            self.logger.error(f"MT5 initialization failed, error code = {mt5.last_error()}")
            return False
        account_info = mt5.account_info()
        if account_info is None:
            self.logger.error(f"MT5 login failed, error code = {mt5.last_error()}")
            mt5.shutdown()
            return False
        self.logger.info(f"Logged in to MT5 account #{account_info.login} (Server: {account_info.server}, Balance: {account_info.balance})")
        self.logger.info(f"MetaTrader5 version: {mt5.version()}")
        return True

    def load_initial_data(self):
        """Scans 'Data/' folder and loads all available CSV data."""
        self.logger.info("--- Loading Initial Data ---")
        data_dir = config.DATA_FOLDER
        if not os.path.exists(data_dir):
            self.logger.error(f"Data directory '{data_dir}' not found.")
            return

        for filename in os.listdir(data_dir):
            if filename.endswith('.csv'):
                parts = filename.replace('.csv', '').split('_')
                if len(parts) == 2:
                    symbol, timeframe = parts[0], parts[1]
                    filepath = os.path.join(data_dir, filename)
                    try:
                        df = pd.read_csv(filepath)
                        df['datetime'] = pd.to_datetime(df['datetime'])
                        df.set_index('datetime', inplace=True)
                        if 'volume' in df.columns:
                            df.rename(columns={'volume': 'tick_volume'}, inplace=True)
                        
                        if symbol not in self.dataframes:
                            self.dataframes[symbol] = {}
                            self.last_processed_times[symbol] = {}

                        self.dataframes[symbol][timeframe] = df
                        self.last_processed_times[symbol][timeframe] = df.index[-1]
                        self.logger.info(f"Loaded {symbol} {timeframe}: {len(df)} bars, latest: {df.index[-1]}")
                    except Exception as e:
                        self.logger.error(f"Failed to load {filepath}: {e}")
        self.logger.info(f"Loaded data for {len(self.dataframes)} currency pairs: {list(self.dataframes.keys())}")

    def check_for_new_data(self):
        self.logger.debug("Starting check_for_new_data.")
        """Checks for new data in CSV files and reloads if necessary."""
        data_dir = 'Data'
        for symbol, timeframes in self.last_processed_times.items():
            for timeframe, last_time in timeframes.items():
                filepath = os.path.join(data_dir, f"{symbol}_{timeframe}.csv")
                if os.path.exists(filepath):
                    try:
                        # In a real scenario, this check could be more efficient
                        # For this implementation, we reload and check the last timestamp
                        df = pd.read_csv(filepath)
                        df['datetime'] = pd.to_datetime(df['datetime'])
                        latest_csv_time = df['datetime'].iloc[-1]

                        if latest_csv_time > last_time:
                            self.logger.info(f"New {timeframe} data for {symbol}: {latest_csv_time}")
                            df.set_index('datetime', inplace=True)
                            if 'volume' in df.columns:
                                df.rename(columns={'volume': 'tick_volume'}, inplace=True)
                            self.dataframes[symbol][timeframe] = df
                            self.last_processed_times[symbol][timeframe] = latest_csv_time

                    except Exception as e:
                        self.logger.warning(f"Could not check/load new data for {filepath}: {e}")
        self.logger.debug("Finished check_for_new_data.")

    def detect_and_log_patterns(self, symbol, timeframe, bar):
        """Creates a detailed dictionary for a bar and logs it as JSON."""
        self.logger.debug(f"Entering detect_and_log_patterns for {symbol} {timeframe}.")
        pattern_data = {
            'symbol': symbol,
            'timeframe': timeframe,
            'timestamp': bar.name.isoformat(),
            'open': bar['open'],
            'high': bar['high'],
            'low': bar['low'],
            'close': bar['close'],
            'volume': bar.get('tick_volume', 0)
        }

        if timeframe == 'M30':
            bb_upper = bar.get('bb_upper', None)
            bb_lower = bar.get('bb_lower', None)
            pattern_data.update({
                'bb_upper': bb_upper,
                'bb_middle': bar.get('bb_middle', None),
                'bb_lower': bb_lower,
                'price_position': 'within_bands'
            })
            if bb_upper is not None and bar['close'] > bb_upper:
                pattern_data['price_position'] = 'above_upper'
            elif bb_lower is not None and bar['close'] < bb_lower:
                pattern_data['price_position'] = 'below_lower'
        
        elif timeframe == 'M3':
            ema10 = bar.get('ema_10', None)
            ema50 = bar.get('ema_tp_50', None)
            pattern_data.update({
                'ema_10': ema10,
                'ema_tp_50': ema50
            })
            if ema10 is not None:
                pip_size = 0.0001 if 'JPY' not in symbol else 0.01
                distance_pips = (bar['close'] - ema10) / pip_size
                pattern_data['price_vs_ema'] = 'above' if distance_pips > 0 else 'below'
                pattern_data['distance_pips'] = round(distance_pips, 2)

        self.pattern_logger.info(json.dumps(pattern_data))

    def detect_bb_trends_realtime(self, symbol):
        """Processes the latest M30 bar for Bollinger Bands trend signals."""
        self.logger.debug(f"Detecting BB trends for {symbol} on M30.")
        df = self.dataframes[symbol]['M30']
        if len(df) < self.bb_period:
            return df # Not enough data

        # Calculate BBands
        bb_upper, bb_middle, bb_lower = talib.BBANDS(
            df['close'], timeperiod=self.bb_period, nbdevup=self.bb_std_dev_up, nbdevdn=self.bb_std_dev_dn, matype=self.bb_matype)
        df['bb_upper'] = bb_upper
        df['bb_middle'] = bb_middle
        df['bb_lower'] = bb_lower
        
        # Simple trend detection based on last close
        last_close = df['close'].iloc[-1]
        last_upper = df['bb_upper'].iloc[-1]
        last_lower = df['bb_lower'].iloc[-1]

        # A simple trend is active if the last close crossed a band
        df['uptrend_start'] = last_close > last_upper
        df['downtrend_start'] = last_close < last_lower
        
        return df

    def calculate_entry_indicators(self, symbol):
        """Calculates indicators for the M3 timeframe."""
        self.logger.debug(f"Calculating entry indicators for {symbol} on M3.")
        df = self.dataframes[symbol]['M3']
        if df.empty or len(df) < self.ema_period:
            self.logger.debug("M3 dataframe is empty or has insufficient data for EMA calculation.")
            return

        # Calculate EMA
        ema_col = f'ema_{self.ema_period}'
        df[ema_col] = talib.EMA(df['close'], timeperiod=self.ema_period)
        self.logger.debug(f"{ema_col.upper()} calculated and added to M3 dataframe.")

    def generate_signals_and_trade(self, symbol):
        """Generates M3 entry signals based on M30 trends and executes trades."""
        m30_df = self.dataframes[symbol]['M30']
        m3_df = self.dataframes[symbol]['M3']

        if m30_df.empty or m3_df.empty:
            return

        # Check for active trend from M30
        if not (m30_df.iloc[-1]['uptrend_start'] or m30_df.iloc[-1]['downtrend_start']):
            return # No active trend

        # Simplified signal logic on M3 data
        last_m3_bar = m3_df.iloc[-1]
        signal = 0
        ema_col = f'ema_{self.ema_period}'

        # Ensure the EMA column exists before trying to access it
        if ema_col not in m3_df.columns:
            self.logger.warning(f"EMA column '{ema_col}' not found. Insufficient data for calculation.")
            return

        if pd.isna(last_m3_bar[ema_col]):
            self.logger.warning(f"EMA value is NaN for timestamp {last_m3_bar.name}. Skipping signal generation.")
            return

        if m30_df.iloc[-1]['uptrend_start']:
            if last_m3_bar['close'] > last_m3_bar[ema_col]:
                signal = 1
        elif m30_df.iloc[-1]['downtrend_start']:
            if last_m3_bar['close'] < last_m3_bar[ema_col]:
                signal = -1

        # Check if the current bar is new since the last processed trade for this timeframe
        last_processed_m3_time = self.last_processed_times.get(symbol, {}).get('M3')
        if signal != 0 and (last_processed_m3_time is None or last_m3_bar.name > last_processed_m3_time):
            self.last_processed_times[symbol]['M3'] = last_m3_bar.name
            order_type = 'BUY' if signal == 1 else 'SELL'
            log_msg = f"{order_type} SIGNAL | Time: {last_m3_bar.name}, Price: {last_m3_bar['close']}"
            self.logger.info(log_msg)
            self.trade_logger.info(log_msg)
            self.execute_trade(symbol=symbol, order_type=order_type, volume=self.lot_size, 
                               sl_pips=self.sl_pips, tp_pips=self.tp_pips)

    def execute_trade(self, symbol, order_type, volume, sl_pips, tp_pips):
        """Executes a trade via MT5."""
        self.logger.info(f"Executing {order_type} on {symbol} for {volume} lots.")
        # ... Placeholder for actual MT5 execution logic ...

    def shutdown_mt5(self):
        """Shuts down the MT5 connection."""
        self.logger.info("Shutting down MT5 connection.")
        mt5.shutdown()

    def run(self, symbol):
        """Runs the main trading loop."""
        if not self.initialized:
            self.logger.critical("Cannot run, system not initialized.")
            return

        self.load_initial_data()
        
        try:
            while True:
                self.logger.debug("Entering run loop.")
                self.logger.info("--- Starting new processing cycle ---")
                self.check_for_new_data()
                
                self.detect_bb_trends_realtime(symbol)
                self.calculate_entry_indicators(symbol)
                self.generate_signals_and_trade(symbol)

                self.logger.info(f"Processing complete. Waiting for {self.check_interval} seconds.")
                time.sleep(self.check_interval)

        except KeyboardInterrupt:
            self.logger.info("Bot stopped by user.")
        finally:
            self.shutdown_mt5()
            self.logger.info("--- Forward Testing Bot Shutdown ---")

if __name__ == "__main__":
    trader = RealTimeTrader()
    trader.run(symbol=config.TRADING_SYMBOL)
