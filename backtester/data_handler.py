import MetaTrader5 as mt5
import pandas as pd
import logging

def get_historical_data(symbol, timeframe, start_date, end_date):
    """
    Fetches historical price data from MT5 for a given symbol and timeframe.

    Args:
        symbol (str): The trading symbol (e.g., 'EURUSD').
        timeframe (mt5.TIMEFRAME): The timeframe for the candles (e.g., mt5.TIMEFRAME_M30).
        start_date (datetime): The start date for the historical data.
        end_date (datetime): The end date for the historical data.

    Returns:
        pd.DataFrame: A DataFrame with the historical data, indexed by datetime.
    """
    logging.info(f"Fetching historical data for {symbol} on {timeframe} from {start_date} to {end_date}")
    rates = mt5.copy_rates_range(symbol, timeframe, start_date, end_date)

    if rates is None or len(rates) == 0:
        logging.warning(f"No historical data found for {symbol} in the specified range.")
        return pd.DataFrame()

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.rename(columns={'time': 'datetime', 'tick_volume': 'volume'}, inplace=True)
    df.set_index('datetime', inplace=True)
    
    logging.info(f"Successfully fetched {len(df)} bars for {symbol}.")
    return df

def get_latest_candles(symbol, timeframe, count=10):
    """
    Fetches the most recent candles from MT5.

    Args:
        symbol (str): The trading symbol.
        timeframe (mt5.TIMEFRAME): The timeframe for the candles.
        count (int): The number of recent candles to fetch.

    Returns:
        pd.DataFrame: A DataFrame with the latest candle data.
    """
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)

    if rates is None or len(rates) == 0:
        logging.warning(f"Could not fetch latest candles for {symbol}.")
        return pd.DataFrame()

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.rename(columns={'time': 'datetime', 'tick_volume': 'volume'}, inplace=True)
    df.set_index('datetime', inplace=True)
    return df

def load_csv_data(file_path):
    """
    Loads historical data from a CSV file and standardizes the index to UTC.

    Args:
        file_path (str): The full path to the CSV file.

    Returns:
        pd.DataFrame: A DataFrame with the loaded data, or an empty DataFrame on error.
    """
    try:
        df = pd.read_csv(
            file_path,
            parse_dates=['datetime'],
            index_col='datetime'
        )

        # --- Timezone Standardization ---
        # If the index is timezone-naive, assume it's UTC.
        # If it's timezone-aware, convert it to UTC for consistency.
        if df.index.tz is None:
            df.index = df.index.tz_localize('UTC')
        else:
            df.index = df.index.tz_convert('UTC')

        # Ensure column names match the rest of the system
        if 'tick_volume' in df.columns:
            df.rename(columns={'tick_volume': 'volume'}, inplace=True)

        logging.info(f"Successfully loaded data from {file_path}")
        return df
    except FileNotFoundError:
        logging.error(f"Data file not found at {file_path}")
        return pd.DataFrame()
    except Exception as e:
        logging.error(f"Error loading data from {file_path}: {e}")
        return pd.DataFrame()

