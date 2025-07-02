import MetaTrader5 as mt5
import logging

def execute_trade(symbol, order_type, volume, sl_pips, tp_pips, pip_size):
    """
    Executes a trade on the MT5 platform with enhanced logic.

    Args:
        symbol (str): The trading symbol (e.g., 'EURUSD').
        order_type (str): 'BUY' or 'SELL'.
        volume (float): The trade volume in lots.
        sl_pips (float): The stop loss in pips.
        tp_pips (float): The take profit in pips.
        pip_size (float): The size of a pip for the symbol.

    Returns:
        bool: True if the trade was successfully executed, False otherwise.
    """
    try:
        # Get symbol info and ensure it's visible in Market Watch
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            logging.error(f"Failed to get symbol info for {symbol}. It might not exist.")
            return False

        if not symbol_info.visible:
            logging.warning(f"{symbol} is not visible in MarketWatch. Attempting to enable it.")
            if not mt5.symbol_select(symbol, True):
                logging.error(f"Failed to enable {symbol} in MarketWatch. Cannot proceed with trade.")
                return False
            # Re-fetch symbol info after enabling
            symbol_info = mt5.symbol_info(symbol)

        # Get the latest market price
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            logging.error(f"Failed to get market tick for {symbol}. Cannot determine price.")
            return False

        # Determine order type and price
        if order_type.upper() == 'BUY':
            trade_type = mt5.ORDER_TYPE_BUY
            price = tick.ask
        elif order_type.upper() == 'SELL':
            trade_type = mt5.ORDER_TYPE_SELL
            price = tick.bid
        else:
            logging.error(f"Invalid order type: {order_type}")
            return False

        # Calculate SL and TP prices
        sl_price = price - sl_pips * pip_size if order_type.upper() == 'BUY' else price + sl_pips * pip_size
        tp_price = price + tp_pips * pip_size if order_type.upper() == 'BUY' else price - tp_pips * pip_size

        # Check margin requirements before sending the order
        margin = mt5.order_calc_margin(mt5.TRADE_ACTION_DEAL, symbol, volume, price)
        if margin is None:
            logging.error(f"Failed to calculate margin for {symbol}. Check account balance or symbol settings.")
            return False

        # Build the trade request with improved settings
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": trade_type,
            "price": price,
            "sl": round(sl_price, symbol_info.digits),
            "tp": round(tp_price, symbol_info.digits),
            "deviation": 10,  # Max price deviation in points
            "magic": 234000,  # Unique EA ID
            "comment": f"Python Trade - {order_type}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_FOK,  # Fill Or Kill for better execution
        }

        # Send the order
        logging.info(f"Sending {order_type} order for {symbol} at {price} with SL={sl_price:.5f}, TP={tp_price:.5f}")
        result = mt5.order_send(request)

        if result is None:
            logging.error(f"Order send failed. MT5 Error: {mt5.last_error()}")
            return False

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logging.error(f"Order failed: {result.comment}, Retcode: {result.retcode}")
            return False

        logging.info(
            f"Order executed successfully: Ticket: {result.order}, "
            f"Volume: {volume}, Price: {result.price}, SL: {result.sl}, TP: {result.tp}"
        )
        return True

    except Exception as e:
        logging.error(f"An unexpected error occurred in execute_trade: {e}")
        return False
