# config.py
import os

# Discord
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

# Symbols — top coins
SYMBOLS_LIST = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT"
]

# State file
STATE_FILE = "state.json"
TRADE_LOG_FILE = "trade_log.json"

# Analyzer settings
DELTA_THRESHOLD = 35.0          # base threshold
OI_SURGE_PCT = 0.001            # base OI change threshold
VOLUME_LOOKBACK = 20            # candles for volume average
ATR_LOOKBACK = 14               # candles for ATR

# Risk settings
STOP_LOSS_ATR_MULT = 1.5
TAKE_PROFIT_ATR_MULT = 2.5
