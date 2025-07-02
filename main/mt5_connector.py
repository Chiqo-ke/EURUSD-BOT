import MetaTrader5 as mt5
import logging

def initialize_mt5(login, password, server):
    """
    Initializes and logs into the MetaTrader 5 terminal.

    Args:
        login (int): The account number.
        password (str): The account password.
        server (str): The server name.

    Returns:
        bool: True if connection and login are successful, False otherwise.
    """
    # Initialize connection to the MetaTrader 5 terminal
    if not mt5.initialize():
        logging.error(f"initialize() failed, error code = {mt5.last_error()}")
        return False
    
    logging.info(f"MetaTrader5 package author: {mt5.version()[2]}")
    logging.info(f"MetaTrader5 package version: {mt5.version()[0]}.{mt5.version()[1]}")

    # Log in to the trade account
    if not mt5.login(login, password, server):
        logging.error(f"login(login={login}, server='{server}') failed, error code = {mt5.last_error()}")
        mt5.shutdown()
        return False
    
    logging.info(f"Successfully connected to account {login} on server {server}")
    return True

def shutdown_mt5():
    """
    Shuts down the connection to the MetaTrader 5 terminal.
    """
    mt5.shutdown()
    logging.info("MT5 connection shut down.")
