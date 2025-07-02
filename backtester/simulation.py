import logging
import pandas as pd

def simulate_fixed_tp_sl_trades(df, tp_pips, sl_pips, pip_size, max_concurrent_trades):
    """
    Simulates trades with fixed TP/SL levels, allowing a specified number of concurrent trades.

    Args:
        df (pd.DataFrame): DataFrame with an 'entry_signal' column (1 for buy, -1 for sell).
        tp_pips (float): Take profit in pips.
        sl_pips (float): Stop loss in pips.
        pip_size (float): The value of one pip.
        max_concurrent_trades (int): The maximum number of trades that can be open at once.

    Returns:
        pd.DataFrame: A DataFrame containing the results of all trades.
    """
    logging.info("--- Starting Trade Simulation (Multi-Trade, Fixed TP/SL) ---")
    logging.info(f"TP: {tp_pips} pips, SL: {sl_pips} pips, Pip Size: {pip_size}")
    
    active_trades = []
    closed_trades = []

    # Convert pips to price units
    tp_price_diff = tp_pips * pip_size
    sl_price_diff = sl_pips * pip_size

    for i in range(len(df)):
        row = df.iloc[i]
        bar_high = row['high']
        bar_low = row['low']

        # --- Manage Existing Trades ---
        remaining_trades = []
        for trade in active_trades:
            trade_closed = False
            if trade['type'] == 'buy':
                # Check for SL
                if bar_low <= trade['sl_price']:
                    trade['exit_time'] = row.name
                    trade['exit_price'] = trade['sl_price']
                    trade['pnl_pips'] = -sl_pips
                    trade['exit_reason'] = 'sl'
                    closed_trades.append(trade)
                    trade_closed = True
                # Check for TP
                elif bar_high >= trade['tp_price']:
                    trade['exit_time'] = row.name
                    trade['exit_price'] = trade['tp_price']
                    trade['pnl_pips'] = tp_pips
                    trade['exit_reason'] = 'tp'
                    closed_trades.append(trade)
                    trade_closed = True
            elif trade['type'] == 'sell':
                # Check for SL
                if bar_high >= trade['sl_price']:
                    trade['exit_time'] = row.name
                    trade['exit_price'] = trade['sl_price']
                    trade['pnl_pips'] = -sl_pips
                    trade['exit_reason'] = 'sl'
                    closed_trades.append(trade)
                    trade_closed = True
                # Check for TP
                elif bar_low <= trade['tp_price']:
                    trade['exit_time'] = row.name
                    trade['exit_price'] = trade['tp_price']
                    trade['pnl_pips'] = tp_pips
                    trade['exit_reason'] = 'tp'
                    closed_trades.append(trade)
                    trade_closed = True
            
            if not trade_closed:
                remaining_trades.append(trade)
        active_trades = remaining_trades

        # --- Check for New Entry Signals ---
        if len(active_trades) < max_concurrent_trades:
            # Check for a buy signal
            if row['entry_signal'] == 1:
                entry_price = row['open']
                active_trades.append({
                    'entry_time': row.name,
                    'entry_price': entry_price,
                    'type': 'buy',
                    'sl_price': entry_price - sl_price_diff,
                    'tp_price': entry_price + tp_price_diff
                })
            
            # Check for a sell signal
            elif row['entry_signal'] == -1:
                entry_price = row['open']
                active_trades.append({
                    'entry_time': row.name,
                    'entry_price': entry_price,
                    'type': 'sell',
                    'sl_price': entry_price + sl_price_diff,
                    'tp_price': entry_price - tp_price_diff
                })

    # --- Finalize any open trades at the end of the data ---
    for trade in active_trades:
        trade['exit_time'] = df.index[-1]
        trade['exit_price'] = df.iloc[-1]['close']
        pnl = (trade['exit_price'] - trade['entry_price']) / pip_size if trade['type'] == 'buy' else (trade['entry_price'] - trade['exit_price']) / pip_size
        trade['pnl_pips'] = pnl
        trade['exit_reason'] = 'open'
        closed_trades.append(trade)

    logging.info(f"Simulation complete. Total trades recorded: {len(closed_trades)}")
    return pd.DataFrame(closed_trades)