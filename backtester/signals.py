import logging
import pandas as pd
import talib

def detect_bb_trends_with_volume(df, uptrend_vol_threshold=2000, downtrend_vol_threshold=2500):
    """
    Detects uptrend and downtrend start signals using Bollinger Bands with volume filtering.
    
    Uptrend Start: Previous close < previous lower band AND current close > previous lower band
    Downtrend Start: Previous close > previous upper band AND current close < previous upper band
    
    Args:
        df (pd.DataFrame): DataFrame with columns ['close', 'bb_upper', 'bb_lower', 'volume']
        uptrend_vol_threshold (int): Minimum volume required for uptrend signals
        downtrend_vol_threshold (int): Minimum volume required for downtrend signals (higher due to panic selling)
        
    Returns:
        pd.DataFrame: DataFrame with new columns 'uptrend_start', 'downtrend_start'
    """
    # Validate data
    assert df.index.is_monotonic_increasing, "DataFrame index must be sorted"
    assert pd.api.types.is_datetime64_any_dtype(df.index), "Index must be datetime"
    df = df.copy()
    
    # Log initial data info
    logging.info(f"Processing {len(df)} M30 bars for BB trend detection")
    logging.info(f"Uptrend volume threshold: {uptrend_vol_threshold}, Downtrend volume threshold: {downtrend_vol_threshold}")
    
    # Track volume thresholds separately
    valid_uptrend_volume = df['volume'] > uptrend_vol_threshold
    valid_downtrend_volume = df['volume'] > downtrend_vol_threshold
    
    # Log volume statistics
    if logging.getLogger().level == logging.INFO:
        uptrend_volume_count = valid_uptrend_volume.sum()
        downtrend_volume_count = valid_downtrend_volume.sum()
        logging.info(f"Bars with valid uptrend volume: {uptrend_volume_count}/{len(df)} ({uptrend_volume_count/len(df):.2%})")
        logging.info(f"Bars with valid downtrend volume: {downtrend_volume_count}/{len(df)} ({downtrend_volume_count/len(df):.2%})")
    
    # Create BB trend signals with asymmetric volume filtering and consistent band references
    df['uptrend_start'] = (
        (df['close'].shift(1) < df['bb_lower'].shift(1)) &
        (df['close'] > df['bb_lower'].shift(1)) &  # Use previous lower band
        valid_uptrend_volume
    )
    
    df['downtrend_start'] = (
        (df['close'].shift(1) > df['bb_upper'].shift(1)) &
        (df['close'] < df['bb_upper'].shift(1)) &  # Use previous upper band consistently
        valid_downtrend_volume
    )
    
    # Calculate and log metrics
    uptrend_count = df['uptrend_start'].sum()
    downtrend_count = df['downtrend_start'].sum()
    total_signals = uptrend_count + downtrend_count
    
    if len(df) > 0:
        uptrend_rate = uptrend_count / len(df)
        downtrend_rate = downtrend_count / len(df)
        signal_rate = total_signals / len(df)
    else:
        uptrend_rate = downtrend_rate = signal_rate = 0.0
    
    logging.info(f"BB Uptrend start signals: {uptrend_count} ({uptrend_rate:.2%})")
    logging.info(f"BB Downtrend start signals: {downtrend_count} ({downtrend_rate:.2%})")
    logging.info(f"Total trend start signals: {total_signals} ({signal_rate:.2%})")
    
    # Log recent signals for debugging
    if logging.getLogger().level == logging.INFO:
        recent_uptrends = df[df['uptrend_start']].tail(3)
        recent_downtrends = df[df['downtrend_start']].tail(3)
        
        if len(recent_uptrends) > 0:
            logging.info(f"Recent uptrend signals: {recent_uptrends.index.tolist()}")
        if len(recent_downtrends) > 0:
            logging.info(f"Recent downtrend signals: {recent_downtrends.index.tolist()}")
    
    return df

def mark_m3_entry_eligibility(m3_df, m30_df):
    """
    Marks M3 bars as eligible for entry based on M30 trend start signals.
    
    When an uptrend_start or downtrend_start is detected on M30, all subsequent M3 bars
    that start after that M30 bar completes are marked as eligible until a signal in
    the opposite direction is detected.
    
    Args:
        m3_df (pd.DataFrame): M3 bars DataFrame
        m30_df (pd.DataFrame): M30 bars DataFrame with 'uptrend_start' and 'downtrend_start'
        
    Returns:
        pd.DataFrame: Updated m3_df with 'eligible_for_entry' and 'entry_direction' columns
    """
    logging.info(f"Marking entry eligibility for {len(m3_df)} M3 bars based on {len(m30_df)} M30 bars")
    
    # Ensure data is sorted
    m3_df = m3_df.copy().sort_index()
    m30_df = m30_df.copy().sort_index()
    
    # Initialize columns
    m3_df['eligible_for_entry'] = False
    m3_df['entry_direction'] = None
    # Initialize 'triggering_m30_bar' with the correct dtype to avoid FutureWarning
    if pd.api.types.is_datetime64_any_dtype(m30_df.index):
        # Preserve timezone if present
        m3_df['triggering_m30_bar'] = pd.Series(pd.NaT, index=m3_df.index, dtype=m30_df.index.dtype)
    else:
        m3_df['triggering_m30_bar'] = pd.NaT
    
    # Get M30 trend start signals
    m30_signals = m30_df[(m30_df['uptrend_start']) | (m30_df['downtrend_start'])].copy()
    logging.info(f"Found {len(m30_signals)} M30 trend start signals")
    
    # If no signals, return early
    if m30_signals.empty:
        logging.warning("No M30 trend signals found. No M3 bars will be marked eligible.")
        return m3_df
    
    # Iterate through each M30 signal to mark subsequent M3 bars
    for i in range(len(m30_signals)):
        signal_time = m30_signals.index[i]
        
        # Determine the end time for marking eligibility
        # It's the time of the next signal, or the end of the M3 data if it's the last signal
        end_time = m30_signals.index[i+1] if i + 1 < len(m30_signals) else m3_df.index[-1]
        
        # Determine the direction of the trend
        direction = 'uptrend' if m30_signals.iloc[i]['uptrend_start'] else 'downtrend'
        
        # Select M3 bars within the trend window
        # The M3 bar must start *after* the M30 signal bar has completed.
        # An M30 bar from time `t` covers the interval [t, t + 30 mins).
        # So, eligible M3 bars must start at or after t + 30 mins.
        start_of_m3_window = signal_time + pd.Timedelta(minutes=30)
        
        eligible_mask = (m3_df.index >= start_of_m3_window) & (m3_df.index < end_time)
        
        # Mark the bars
        m3_df.loc[eligible_mask, 'eligible_for_entry'] = True
        m3_df.loc[eligible_mask, 'entry_direction'] = direction
        m3_df.loc[eligible_mask, 'triggering_m30_bar'] = signal_time
        
        # Log the marking action
        marked_count = eligible_mask.sum()
        if marked_count > 0:
            logging.info(f"M30 {direction} signal at {signal_time}: marked {marked_count} M3 bars as eligible")
            
    # Final summary
    if logging.getLogger().level == logging.INFO:
        total_eligible = m3_df['eligible_for_entry'].sum()
        uptrend_eligible = (m3_df['entry_direction'] == 'uptrend').sum()
        downtrend_eligible = (m3_df['entry_direction'] == 'downtrend').sum()
        
        logging.info("M3 entry eligibility summary:")
        logging.info(f"  Total eligible bars: {total_eligible}/{len(m3_df)} ({total_eligible/len(m3_df):.2%})")
        logging.info(f"  Uptrend eligible: {uptrend_eligible}")
        logging.info(f"  Downtrend eligible: {downtrend_eligible}")
    
    return m3_df

def generate_entry_signals(m3_df, ema_threshold_pips, pip_size=0.0001):
    """
    Generates buy/sell entry signals for M3 bars based on M30 trend and EMA conditions.
    A unified 'entry_signal' column is created: 1 for buy, -1 for sell, 0 for no signal.
   
    Args:
        m3_df (pd.DataFrame): M3 bars DataFrame with columns:
            ['close', 'eligible_for_entry', 'entry_direction']
        ema_threshold_pips (float): Minimum required distance from EMA in pips
        pip_size (float): Value of one pip (default 0.0001 for most pairs)
       
    Returns:
        pd.DataFrame: Updated m3_df with a new 'entry_signal' column.
    """
    logging.info(f"Generating entry signals for {len(m3_df)} M3 bars")
    logging.info(f"EMA threshold: {ema_threshold_pips} pips ({ema_threshold_pips * pip_size:.5f} price units)")
    
    # Convert pips to price units
    threshold_price = ema_threshold_pips * pip_size
   
    # Initialize signal columns
    m3_df = m3_df.copy()
    m3_df['ema'] = talib.EMA(m3_df['close'], timeperiod=10)
    m3_df['entry_signal'] = 0  # 0 for no signal, 1 for buy, -1 for sell
   
    # Calculate conditions using vectorized operations
    prev_close_above_ema = m3_df['close'].shift(1) > (m3_df['ema'].shift(1) + threshold_price)
    prev_close_below_ema = m3_df['close'].shift(1) < (m3_df['ema'].shift(1) - threshold_price)
   
    # Count eligible bars by direction
    eligible_count = m3_df['eligible_for_entry'].sum()
    uptrend_eligible = (m3_df['eligible_for_entry'] & (m3_df['entry_direction'] == 'uptrend')).sum()
    downtrend_eligible = (m3_df['eligible_for_entry'] & (m3_df['entry_direction'] == 'downtrend')).sum()
    
    logging.info(f"Eligible bars: {eligible_count} total ({uptrend_eligible} uptrend, {downtrend_eligible} downtrend)")
    
    # Buy conditions (only when eligible and in uptrend)
    buy_conditions = (
        m3_df['eligible_for_entry'] &
        (m3_df['entry_direction'] == 'uptrend') &
        prev_close_above_ema
    )
   
    # Sell conditions (only when eligible and in downtrend)
    sell_conditions = (
        m3_df['eligible_for_entry'] &
        (m3_df['entry_direction'] == 'downtrend') &
        prev_close_below_ema
    )
   
    # Apply signals to the unified column
    m3_df.loc[buy_conditions, 'entry_signal'] = 1
    m3_df.loc[sell_conditions, 'entry_signal'] = -1
    
    # Log signal statistics
    if logging.getLogger().level == logging.INFO:
        buy_signals = (m3_df['entry_signal'] == 1).sum()
        sell_signals = (m3_df['entry_signal'] == -1).sum()
        total_signals = buy_signals + sell_signals
        
        if eligible_count > 0:
            buy_rate = buy_signals / uptrend_eligible if uptrend_eligible > 0 else 0
            sell_rate = sell_signals / downtrend_eligible if downtrend_eligible > 0 else 0
            overall_rate = total_signals / eligible_count
        else:
            buy_rate = sell_rate = overall_rate = 0
        
        logging.info("Entry signals generated:")
        logging.info(f"  Buy signals: {buy_signals}/{uptrend_eligible} uptrend eligible ({buy_rate*100:.2f}%)")
        logging.info(f"  Sell signals: {sell_signals}/{downtrend_eligible} downtrend eligible ({sell_rate*100:.2f}%)")
        logging.info(f"  Total signals: {total_signals}/{eligible_count} eligible ({overall_rate*100:.2f}%)")
        
        # Log recent signals for debugging
        recent_buys = m3_df[m3_df['entry_signal'] == 1].tail(3)
        recent_sells = m3_df[m3_df['entry_signal'] == -1].tail(3)
        
        if len(recent_buys) > 0:
            logging.info(f"Recent buy signals: {recent_buys.index.tolist()}")
        if len(recent_sells) > 0:
            logging.info(f"Recent sell signals: {recent_sells.index.tolist()}")

    return m3_df