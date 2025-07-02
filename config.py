# --- MT5 Connection Settings ---
MT5_LOGIN = 152851811  # Replace with your MT5 account number
MT5_PASSWORD = "aO07Oa'i"  # IMPORTANT: Replace with your MT5 password
MT5_SERVER = "FBS-Demo"      # IMPORTANT: Replace with your MT5 server name

# --- Live Trading Parameters ---
TRADING_SYMBOL = "EURUSD"
LOT_SIZE = 0.01

# --- File Paths ---
DATA_FOLDER = "Data"
M30_FILE = "EURUSD_M30.csv"
M3_FILE = "EURUSD_M3.csv"

# --- Bollinger Bands Parameters ---
BB_TIMEPERIOD = 20
BB_NBDEVUP = 1
BB_NBDEVDN = 1
BB_MATYPE = 0  # 0=SMA, 1=EMA, etc.

# --- Volume Filter Parameters ---
UPTREND_VOL_THRESHOLD = 8000
DOWNTREND_VOL_THRESHOLD = 8000

# --- Entry Signal Parameters ---
EMA_PERIOD = 10
EMA_THRESHOLD_PIPS = 5
PIP_SIZE = 0.0001
MAX_CONCURRENT_TRADES = 10

# --- Final Strategy Parameters ---
TP_PIPS = 80  # From SL=20, RR=4.0
SL_PIPS = 20
