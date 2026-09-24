import requests
import logging
import time

logger = logging.getLogger("DataEngine")


class DataEngine:
    def __init__(self, symbol: str = "BTCUSDT"):
        self.symbol = symbol.upper()
        self.base_url = "https://fapi.binance.com"
        self.session = requests.Session()

    def _get(self, endpoint: str, params: dict, retries: int = 3):
        """Retry logic ke saath GET request."""
        for attempt in range(retries):
            try:
                res = self.session.get(
                    f"{self.base_url}{endpoint}",
                    params=params,
                    timeout=10
                )
                if res.status_code == 200:
                    return res.json()
                logger.warning(f"{endpoint} returned {res.status_code}, attempt {attempt+1}")
            except Exception as e:
                logger.warning(f"{endpoint} failed: {e}, attempt {attempt+1}")
            time.sleep(1.5 ** attempt)  # exponential backoff
        return None

    def fetch_open_interest(self) -> float:
        data = self._get("/fapi/v1/openInterest", {"symbol": self.symbol})
        if data and "openInterest" in data:
            return float(data["openInterest"])
        return 0.0

    def fetch_recent_trades(self, limit: int = 1000) -> dict:
        """Delta aur volume nikalta hai recent trades se."""
        data = self._get("/fapi/v1/trades", {"symbol": self.symbol, "limit": limit})
        delta = 0.0
        total_volume = 0.0
        buy_volume = 0.0
        sell_volume = 0.0

        if isinstance(data, list):
            for trade in data:
                qty = float(trade["qty"])
                total_volume += qty
                if trade["isBuyerMaker"]:
                    delta -= qty
                    sell_volume += qty
                else:
                    delta += qty
                    buy_volume += qty

        return {
            "delta": delta,
            "volume_chunk": total_volume,
            "buy_volume": buy_volume,
            "sell_volume": sell_volume
        }

    def fetch_ticker(self) -> dict:
        data = self._get("/fapi/v1/ticker/24hr", {"symbol": self.symbol})
        if data:
            return {
                "price": float(data.get("lastPrice", 0.0)),
                "volume_24h": float(data.get("volume", 0.0)),
                "price_change_pct": float(data.get("priceChangePercent", 0.0))
            }
        return {"price": 0.0, "volume_24h": 0.0, "price_change_pct": 0.0}

    def fetch_klines(self, interval: str = "15m", limit: int = 50) -> list:
        """ATR aur volume average ke liye candles."""
        data = self._get(
            "/fapi/v1/klines",
            {"symbol": self.symbol, "interval": interval, "limit": limit}
        )
        if isinstance(data, list):
            return data
        return []

    def fetch_order_book(self, limit: int = 100) -> dict:
        """L2 depth — absorption confirm karne ke liye."""
        data = self._get("/fapi/v1/depth", {"symbol": self.symbol, "limit": limit})
        if data:
            bids = [(float(p), float(q)) for p, q in data.get("bids", [])]
            asks = [(float(p), float(q)) for p, q in data.get("asks", [])]
            return {"bids": bids, "asks": asks}
        return {"bids": [], "asks": []}

    def fetch_market_data(self) -> dict:
        """Saara data ek saath."""
        try:
            price = 0.0
            oi = self.fetch_open_interest()
            trades = self.fetch_recent_trades()
            ticker = self.fetch_ticker()
            klines = self.fetch_klines()
            order_book = self.fetch_order_book()

            price = ticker["price"]

            # ATR calculate karo klines se
            atr = 0.0
            volume_avg = 0.0
            if len(klines) >= 15:
                highs = [float(k[2]) for k in klines]
                lows = [float(k[3]) for k in klines]
                closes = [float(k[4]) for k in klines]
                volumes = [float(k[5]) for k in klines]

                trs = []
                for i in range(1, len(klines)):
                    tr = max(
                        highs[i] - lows[i],
                        abs(highs[i] - closes[i-1]),
                        abs(lows[i] - closes[i-1])
                    )
                    trs.append(tr)
                atr = sum(trs[-14:]) / 14 if len(trs) >= 14 else 0.0
                volume_avg = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else 0.0

            return {
                "symbol": self.symbol,
                "price": price,
                "open_interest": oi,
                "delta": trades["delta"],
                "volume_chunk": trades["volume_chunk"],
                "buy_volume": trades["buy_volume"],
                "sell_volume": trades["sell_volume"],
                "volume_24h": ticker["volume_24h"],
                "price_change_pct": ticker["price_change_pct"],
                "atr": atr,
                "volume_avg": volume_avg,
                "order_book": order_book,
                "klines": klines
            }
        except Exception as e:
            logger.error(f"Error fetching market data for {self.symbol}: {e}")
            return {
                "symbol": self.symbol, "price": 0.0, "open_interest": 0.0,
                "delta": 0.0, "volume_chunk": 0.0, "buy_volume": 0.0,
                "sell_volume": 0.0, "volume_24h": 0.0, "price_change_pct": 0.0,
                "atr": 0.0, "volume_avg": 0.0, "order_book": {"bids": [], "asks": []},
                "klines": []
            }
