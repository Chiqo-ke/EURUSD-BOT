from tvDatafeed import TvDatafeed, Interval
import os
import time
import logging
from datetime import datetime, timezone
import threading

username = "nyagamacharia6"
password = "ChiqoMehum1432."

tv = TvDatafeed(username, password)

# Trading pair configuration
SYMBOL = "EURUSD"
EXCHANGE = "FX_IDC"

# Data fetching configuration
M30_BARS = 100  # Number of M30 bars to fetch
M3_BARS = 300   # Number of M3 bars to fetch

# Directory configuration
DATA_DIR = "Data"
LOGS_DIR = "logs"

# Timing configuration (in seconds)
SLEEP_INTERVAL = 3  # How often to check if it's time to fetch data
ERROR_RETRY_INTERVAL = 3  # How long to wait after an error

# Logging configuration
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'

# You can add more symbols here for multi-symbol fetching
SYMBOLS_CONFIG = {
    "EURUSD": {
        "exchange": "FX_IDC",
        "m30_bars": 100,
        "m3_bars": 300
    }    
}

class RealTimeDataFetcher:
    def __init__(self, symbol="EURUSD", exchange="FX_IDC"):
        self.symbol = symbol
        self.exchange = exchange
        self.symbol_config = SYMBOLS_CONFIG.get(symbol, {
            "exchange": exchange,
            "m30_bars": M30_BARS,
            "m3_bars": M3_BARS
        })
        self.tv = TvDatafeed()
        self.running = False
        self.m30_data = None
        self.m3_data = None
        self.data_lock = threading.Lock()
        
        # Create necessary directories
        os.makedirs("logs", exist_ok=True)
        os.makedirs("Data", exist_ok=True)
        
        # Setup logging
        self.setup_logging()
        
    def setup_logging(self):
        """Setup logging configuration"""
        log_filename = f"logs/data_fetcher_{datetime.now().strftime('%Y%m%d')}.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def get_current_utc_time(self):
        """Get current UTC time"""
        return datetime.now(timezone.utc)
    
    def should_fetch_m30(self, current_time):
        """Check if it's time to fetch M30 data (at 00 and 30 minutes)"""
        return current_time.minute in [0, 30] and current_time.second == 0
    
    def should_fetch_m3(self, current_time):
        """Check if it's time to fetch M3 data (every 3 minutes)"""
        return current_time.minute % 3 == 0 and current_time.second == 0
    
    def remove_incomplete_candle(self, data, interval_minutes):
        """Remove the last incomplete candle from the data"""
        if data is None or data.empty:
            return data
            
        current_time = self.get_current_utc_time()
        
        # Create a copy to avoid modifying original
        cleaned_data = data.copy()
        
        # Get the last timestamp
        last_timestamp = cleaned_data.index[-1]
        
        # Convert to datetime if it's not already
        if hasattr(last_timestamp, 'to_pydatetime'):
            last_timestamp = last_timestamp.to_pydatetime()
        
        # Make timezone aware if needed
        if last_timestamp.tzinfo is None:
            last_timestamp = last_timestamp.replace(tzinfo=timezone.utc)
        
        # Calculate when the last candle should close
        if interval_minutes == 30:
            # For M30, candles close at :00 and :30
            if last_timestamp.minute == 0:
                expected_close = last_timestamp.replace(minute=30)
            else:  # minute == 30
                expected_close = last_timestamp.replace(hour=last_timestamp.hour + 1, minute=0)
        else:  # M3
            # For M3, candles close every 3 minutes
            next_close_minute = ((last_timestamp.minute // 3) + 1) * 3
            if next_close_minute >= 60:
                expected_close = last_timestamp.replace(hour=last_timestamp.hour + 1, minute=next_close_minute - 60)
            else:
                expected_close = last_timestamp.replace(minute=next_close_minute)
        
        # If current time hasn't reached the expected close time, remove the last candle
        if current_time < expected_close:
            cleaned_data = cleaned_data.iloc[:-1]
            self.logger.info(f"Removed incomplete candle: {last_timestamp} (closes at {expected_close})")
        
        return cleaned_data
    
    def fetch_and_process_data(self, interval, n_bars, data_type, max_retries=3):
        """Fetch data and remove incomplete candle with retry mechanism"""
        retry_count = 0
        retry_delay = 5  # seconds between retries
        
        while retry_count <= max_retries:
            try:
                if retry_count > 0:
                    self.logger.info(f"Retry attempt {retry_count}/{max_retries} for {data_type} data...")
                else:
                    self.logger.info(f"Fetching {data_type} data...")
                
                raw_data = self.tv.get_hist(
                    symbol=self.symbol,
                    exchange=self.exchange,
                    interval=interval,
                    n_bars=n_bars,
                )
                
                if raw_data is None or raw_data.empty:
                    self.logger.warning(f"No data received for {data_type} (attempt {retry_count + 1})")
                    if retry_count < max_retries:
                        self.logger.info(f"Retrying in {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        retry_count += 1
                        continue
                    else:
                        self.logger.error(f"Failed to fetch {data_type} data after {max_retries + 1} attempts")
                        return None
                
                # Determine interval minutes
                interval_minutes = 30 if data_type == "M30" else 3
                
                # Remove incomplete candle
                processed_data = self.remove_incomplete_candle(raw_data, interval_minutes)
                
                # Log data info
                if not processed_data.empty:
                    last_candle_time = processed_data.index[-1]
                    self.logger.info(f"{data_type} data updated successfully. Last complete candle: {last_candle_time}")
                    self.logger.info(f"{data_type} data shape: {processed_data.shape}")
                
                return processed_data
                
            except Exception as e:
                self.logger.error(f"Error fetching {data_type} data (attempt {retry_count + 1}): {str(e)}")
                if retry_count < max_retries:
                    retry_delay_current = retry_delay * (retry_count + 1)  # Exponential backoff
                    self.logger.info(f"Retrying in {retry_delay_current} seconds...")
                    time.sleep(retry_delay_current)
                    retry_count += 1
                else:
                    self.logger.error(f"Failed to fetch {data_type} data after {max_retries + 1} attempts")
                    return None
        
        return None
    
    def save_data_to_csv(self):
        """Save current data to CSV files"""
        try:
            with self.data_lock:
                if self.m30_data is not None and not self.m30_data.empty:
                    self.m30_data.to_csv(f"Data/{self.symbol}_M30.csv")
                    self.logger.info(f"{self.symbol} M30 data saved to CSV")
                
                if self.m3_data is not None and not self.m3_data.empty:
                    self.m3_data.to_csv(f"Data/{self.symbol}_M3.csv")
                    self.logger.info(f"{self.symbol} M3 data saved to CSV")
                    
        except Exception as e:
            self.logger.error(f"Error saving data to CSV: {str(e)}")
    
    def get_m30_data(self):
        """Thread-safe method to get M30 data"""
        with self.data_lock:
            return self.m30_data.copy() if self.m30_data is not None else None
    
    def get_m3_data(self):
        """Thread-safe method to get M3 data"""
        with self.data_lock:
            return self.m3_data.copy() if self.m3_data is not None else None
    
    def run(self):
        """Main loop for real-time data fetching"""
        self.running = True
        self.logger.info("Starting real-time data fetcher...")
        
        # Initial data fetch with retries
        self.logger.info("Performing initial data fetch...")
        with self.data_lock:
            self.m30_data = self.fetch_and_process_data(
                Interval.in_30_minute, 
                self.symbol_config['m30_bars'], 
                "M30", 
                max_retries=5
            )
            self.m3_data = self.fetch_and_process_data(
                Interval.in_3_minute, 
                self.symbol_config['m3_bars'], 
                "M3", 
                max_retries=5
            )
        
        # Save initial data if successful
        if self.m30_data is not None or self.m3_data is not None:
            self.save_data_to_csv()
        
        last_m30_fetch = None
        last_m3_fetch = None
        
        while self.running:
            try:
                current_time = self.get_current_utc_time()
                
                # Check if we should fetch M30 data
                if self.should_fetch_m30(current_time):
                    current_minute_key = f"{current_time.hour:02d}:{current_time.minute:02d}"
                    if last_m30_fetch != current_minute_key:
                        new_m30_data = self.fetch_and_process_data(
                            Interval.in_30_minute, 
                            self.symbol_config['m30_bars'], 
                            "M30", 
                            max_retries=3
                        )
                        if new_m30_data is not None:
                            with self.data_lock:
                                self.m30_data = new_m30_data
                            self.save_data_to_csv()
                        else:
                            self.logger.error(f"Failed to update {self.symbol} M30 data - keeping previous data")
                        last_m30_fetch = current_minute_key
                
                # Check if we should fetch M3 data
                if self.should_fetch_m3(current_time):
                    current_minute_key = f"{current_time.hour:02d}:{current_time.minute:02d}"
                    if last_m3_fetch != current_minute_key:
                        new_m3_data = self.fetch_and_process_data(
                            Interval.in_3_minute, 
                            self.symbol_config['m3_bars'], 
                            "M3", 
                            max_retries=3
                        )
                        if new_m3_data is not None:
                            with self.data_lock:
                                self.m3_data = new_m3_data
                            self.save_data_to_csv()
                        else:
                            self.logger.error(f"Failed to update {self.symbol} M3 data - keeping previous data")
                        last_m3_fetch = current_minute_key
                
                # Sleep for 1 second to check timing
                time.sleep(1)
                
            except KeyboardInterrupt:
                self.logger.info("Received keyboard interrupt. Stopping...")
                break
            except Exception as e:
                self.logger.error(f"Error in main loop: {str(e)}")
                time.sleep(5)  # Wait 5 seconds before retrying
        
        self.stop()
    
    def stop(self):
        """Stop the data fetcher"""
        self.running = False
        self.logger.info("Data fetcher stopped.")

# Global dictionary to store fetcher instances
_fetcher_instances = {}

def get_fetcher_instance(symbol="EURUSD"):
    """Get a fetcher instance for the specified symbol"""
    global _fetcher_instances
    if symbol not in _fetcher_instances:
        config = SYMBOLS_CONFIG.get(symbol)
        if config:
            _fetcher_instances[symbol] = RealTimeDataFetcher(symbol=symbol, exchange=config['exchange'])
    return _fetcher_instances.get(symbol)

def get_m30_data(symbol="EURUSD"):
    """Get M30 data from the specified symbol's fetcher instance"""
    fetcher = get_fetcher_instance(symbol)
    return fetcher.get_m30_data() if fetcher else None

def get_m3_data(symbol="EURUSD"):
    """Get M3 data from the specified symbol's fetcher instance"""
    fetcher = get_fetcher_instance(symbol)
    return fetcher.get_m3_data() if fetcher else None

if __name__ == "__main__":
    # Create and run fetchers for all configured symbols
    for symbol in SYMBOLS_CONFIG:
        fetcher = RealTimeDataFetcher(symbol=symbol, exchange=SYMBOLS_CONFIG[symbol]['exchange'])
        _fetcher_instances[symbol] = fetcher
        
    try:
        # Start all fetchers in separate threads
        threads = []
        for fetcher in _fetcher_instances.values():
            thread = threading.Thread(target=fetcher.run)
            thread.daemon = True
            thread.start()
            threads.append(thread)
            
        # Wait for keyboard interrupt
        for thread in threads:
            thread.join()
            
    except KeyboardInterrupt:
        print("\nStopping all data fetchers...")
        for fetcher in _fetcher_instances.values():
            fetcher.stop()