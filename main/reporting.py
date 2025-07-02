import pandas as pd
import os

def save_results_to_csv(trades_df: pd.DataFrame, metrics: dict, results_folder: str = 'results'):
    """
    Saves the trades DataFrame and performance metrics to CSV files.

    Args:
        trades_df (pd.DataFrame): DataFrame of trade results.
        metrics (dict): A dictionary of metrics from calculate_trading_metrics.
        results_folder (str): The folder to save the results in.
    """
    os.makedirs(results_folder, exist_ok=True)

    # Save trades
    trades_df.to_csv(os.path.join(results_folder, 'trades.csv'), index=False)

    # Save metrics
    metrics_to_save = metrics.copy()
    if 'exit_reasons' in metrics_to_save and isinstance(metrics_to_save['exit_reasons'], dict):
        metrics_to_save['exit_reasons'] = str(metrics_to_save['exit_reasons'])
        
    metrics_df = pd.DataFrame([metrics_to_save])
    metrics_df.to_csv(os.path.join(results_folder, 'metrics.csv'), index=False)

def calculate_trading_metrics(trades_df: pd.DataFrame, dual_entry: bool = False) -> dict:
    """
    Calculates and returns key performance metrics from a DataFrame of trades.

    Args:
        trades_df (pd.DataFrame): DataFrame of trade results.
        dual_entry (bool): Flag to indicate if metrics are for a dual entry strategy.

    Returns:
        dict: A dictionary containing all calculated metrics.
    """
    if trades_df.empty:
        return {
            'total_trades': 0, 'winning_trades': 0, 'losing_trades': 0, 'breakeven_trades': 0,
            'win_rate_pct': 0, 'total_pnl_pips': 0, 'average_win_pips': 0, 'average_loss_pips': 0,
            'largest_win_pips': 0, 'largest_loss_pips': 0, 'profit_factor': 0,
            'max_consecutive_wins': 0, 'max_consecutive_losses': 0, 'exit_reasons': {}
        }

    # Common metrics
    metrics = {}
    metrics['total_trades'] = len(trades_df)
    metrics['winning_trades'] = (trades_df['pnl_pips'] > 0).sum()
    metrics['losing_trades'] = (trades_df['pnl_pips'] < 0).sum()
    metrics['breakeven_trades'] = (trades_df['pnl_pips'] == 0).sum()
    metrics['win_rate_pct'] = (metrics['winning_trades'] / metrics['total_trades'] * 100) if metrics['total_trades'] > 0 else 0
    metrics['total_pnl_pips'] = trades_df['pnl_pips'].sum()
    
    wins = trades_df[trades_df['pnl_pips'] > 0]['pnl_pips']
    losses = trades_df[trades_df['pnl_pips'] < 0]['pnl_pips']
    
    metrics['average_win_pips'] = wins.mean() if not wins.empty else 0
    metrics['average_loss_pips'] = losses.mean() if not losses.empty else 0
    metrics['largest_win_pips'] = wins.max() if not wins.empty else 0
    metrics['largest_loss_pips'] = losses.min() if not losses.empty else 0
    
    total_profit = wins.sum()
    total_loss = abs(losses.sum())
    metrics['profit_factor'] = total_profit / total_loss if total_loss > 0 else float('inf')

    # Max consecutive wins/losses
    consecutive_wins = 0
    max_consecutive_wins = 0
    consecutive_losses = 0
    max_consecutive_losses = 0
    for pnl in trades_df['pnl_pips']:
        if pnl > 0:
            consecutive_wins += 1
            consecutive_losses = 0
        elif pnl < 0:
            consecutive_losses += 1
            consecutive_wins = 0
        max_consecutive_wins = max(max_consecutive_wins, consecutive_wins)
        max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)

    metrics['max_consecutive_wins'] = max_consecutive_wins
    metrics['max_consecutive_losses'] = max_consecutive_losses
    metrics['exit_reasons'] = trades_df['exit_reason'].value_counts().to_dict()

    if dual_entry:
        trade1_metrics = calculate_trading_metrics(trades_df[trades_df['trade_id'] == 'trade1'], dual_entry=False)
        trade2_metrics = calculate_trading_metrics(trades_df[trades_df['trade_id'] == 'trade2'], dual_entry=False)
        metrics['trade1'] = trade1_metrics
        metrics['trade2'] = trade2_metrics
        
        # Add combined metrics
        metrics['combined_pnl'] = trade1_metrics['total_pnl_pips'] + trade2_metrics['total_pnl_pips']
        if 'trailing_sl' in trades_df['exit_reason'].unique():
            metrics['trailing_activations'] = trades_df[trades_df['exit_reason'] == 'trailing_sl'].shape[0] # Simplified
            metrics['trailing_sl_exits'] = trades_df[trades_df['exit_reason'] == 'trailing_sl'].shape[0]

    return metrics

def print_trading_metrics(metrics: dict, dual_entry: bool = False) -> None:
    """
    Prints a formatted summary of trading performance metrics.

    Args:
        metrics (dict): A dictionary of metrics from calculate_trading_metrics.
        dual_entry (bool): Flag to format output for dual entry strategies.
    """
    print("="*80)
    print("TRADING PERFORMANCE METRICS".center(80))
    print("="*80)

    if not dual_entry:
        print(f"Total Trades: {metrics['total_trades']}")
        print(f"Winning Trades: {metrics['winning_trades']}")
        print(f"Losing Trades: {metrics['losing_trades']}")
        print(f"Breakeven Trades: {metrics['breakeven_trades']}")
        print(f"Win Rate: {metrics['win_rate_pct']:.2f}%")
        print(f"Total P&L: {metrics['total_pnl_pips']:.1f} pips")
        print(f"Average Win: {metrics['average_win_pips']:.1f} pips")
        print(f"Average Loss: {metrics['average_loss_pips']:.1f} pips")
        print(f"Largest Win: {metrics['largest_win_pips']:.1f} pips")
        print(f"Largest Loss: {metrics['largest_loss_pips']:.1f} pips")
        print(f"Profit Factor: {metrics['profit_factor']:.2f}")
        print(f"Max Consecutive Wins: {metrics['max_consecutive_wins']}")
        print(f"Max Consecutive Losses: {metrics['max_consecutive_losses']}")
        print(f"Exit Reasons: {metrics['exit_reasons']}")
    else:
        # Print metrics for each trade leg
        for trade_id, trade_metrics in [('Trade1 (Fixed TP)', metrics['trade1']), ('Trade2 (Trailing SL)', metrics['trade2'])]:
            print(f"\n{trade_id}:")
            print("-"*40)
            print(f"Total Trades: {trade_metrics['total_trades']}")
            print(f"Winning Trades: {trade_metrics['winning_trades']}")
            print(f"Losing Trades: {trade_metrics['losing_trades']}")
            print(f"Breakeven Trades: {trade_metrics['breakeven_trades']}")
            print(f"Win Rate: {trade_metrics['win_rate_pct']:.2f}%")
            print(f"Total P&L: {trade_metrics['total_pnl_pips']:.1f} pips")
            print(f"Average Win: {trade_metrics['average_win_pips']:.1f} pips")
            print(f"Average Loss: {trade_metrics['average_loss_pips']:.1f} pips")
            print(f"Largest Win: {trade_metrics['largest_win_pips']:.1f} pips")
            print(f"Largest Loss: {trade_metrics['largest_loss_pips']:.1f} pips")
            print(f"Profit Factor: {trade_metrics['profit_factor']:.2f}")
            print(f"Max Consecutive Wins: {trade_metrics['max_consecutive_wins']}")
            print(f"Max Consecutive Losses: {trade_metrics['max_consecutive_losses']}")
            print(f"Exit Reasons: {trade_metrics['exit_reasons']}")

        # Print combined and trailing SL specific metrics
        print("\nCOMBINED PERFORMANCE:")
        print("-"*40)
        print(f"Total Combined P&L: {metrics.get('combined_pnl', 0):.1f} pips")
        if metrics.get('combined_pnl', 0) != 0:
            trade1_contrib = (metrics['trade1']['total_pnl_pips'] / metrics['combined_pnl'] * 100) if metrics['combined_pnl'] != 0 else 0
            trade2_contrib = (metrics['trade2']['total_pnl_pips'] / metrics['combined_pnl'] * 100) if metrics['combined_pnl'] != 0 else 0
            print(f"Trade1 Contribution: {metrics['trade1']['total_pnl_pips']:.1f} pips ({trade1_contrib:.2f}%)")
            print(f"Trade2 Contribution: {metrics['trade2']['total_pnl_pips']:.1f} pips ({trade2_contrib:.2f}%)")
        
        if 'trailing_activations' in metrics:
            print(f"Trailing Activations: {metrics.get('trailing_activations', 0)}")
            print(f"Trailing SL Exits: {metrics.get('trailing_sl_exits', 0)}")

    print("="*80)
