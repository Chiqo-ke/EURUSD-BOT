import pandas as pd
import logging
import talib

# Import configuration variables
import config

# Import backtester modules
from main import signals, simulation, reporting

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    """
    Main function to run the backtesting process with final optimized parameters.
    """
    # --- 1. Load Data ---
    logging.info("--- Starting Backtest with Final Parameters ---")
    try:
        m30_path = f"{config.DATA_FOLDER}/{config.M30_FILE}"
        m3_path = f"{config.DATA_FOLDER}/{config.M3_FILE}"
        m30_df = pd.read_csv(m30_path, index_col="datetime", parse_dates=True)
        m3_df = pd.read_csv(m3_path, index_col="datetime", parse_dates=True)
        logging.info(f"Loaded data: {config.M30_FILE} and {config.M3_FILE}")
    except FileNotFoundError as e:
        logging.error(f"Error loading data: {e}. Make sure files are in the '{config.DATA_FOLDER}' directory.")
        return

    if m30_df.empty or m3_df.empty:
        logging.error("Data loading failed or resulted in empty DataFrames. Exiting.")
        return

    # --- 2. Generate Signals with Final Parameters ---
    logging.info(f"Using Volume Thresholds: UPTREND={config.UPTREND_VOL_THRESHOLD}, DOWNTREND={config.DOWNTREND_VOL_THRESHOLD}")
    
    m30_df['bb_upper'], m30_df['bb_middle'], m30_df['bb_lower'] = talib.BBANDS(
        m30_df['close'],
        timeperiod=config.BB_TIMEPERIOD,
        nbdevup=config.BB_NBDEVUP,
        nbdevdn=config.BB_NBDEVDN,
        matype=config.BB_MATYPE
    )
    m30_df = signals.detect_bb_trends_with_volume(
        m30_df,
        uptrend_vol_threshold=config.UPTREND_VOL_THRESHOLD,
        downtrend_vol_threshold=config.DOWNTREND_VOL_THRESHOLD
    )

    m3_df = signals.mark_m3_entry_eligibility(m3_df, m30_df)
    m3_df = signals.generate_entry_signals(
        m3_df,
        ema_threshold_pips=config.EMA_THRESHOLD_PIPS,
        pip_size=config.PIP_SIZE
    )

    if 'entry_signal' not in m3_df.columns or m3_df['entry_signal'].sum() == 0:
        logging.warning("No entry signals were generated with the current parameters. Cannot run simulation.")
        return

    # --- 3. Run Simulation with Final Parameters ---
    logging.info(f"Running simulation with TP: {config.TP_PIPS} pips, SL: {config.SL_PIPS} pips")
    
    trades_df = simulation.simulate_fixed_tp_sl_trades(
        m3_df.copy(),
        tp_pips=config.TP_PIPS,
        sl_pips=config.SL_PIPS,
        pip_size=config.PIP_SIZE,
        max_concurrent_trades=config.MAX_CONCURRENT_TRADES
    )

    # --- 4. Display Final Results ---
    if not trades_df.empty:
        metrics = reporting.calculate_trading_metrics(trades_df)
        print("\n\n===============================================================================")
        print("                 FINAL BACKTEST RESULTS (Optimized Strategy)               ")
        print("===============================================================================")
        reporting.print_trading_metrics(metrics)

        # Save results to CSV
        reporting.save_results_to_csv(trades_df, metrics)
        logging.info("Saved trades and metrics to the 'results' folder.")
    else:
        print("\nNo trades were executed for the final configuration.")

    print("\n--- Backtest Complete ---")

if __name__ == "__main__":
    main()