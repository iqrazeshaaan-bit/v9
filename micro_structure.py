import logging

logger = logging.getLogger("MicroStructure")


class MicroStructureAnalyzer:
    def __init__(self, delta_threshold: float = 35.0, oi_surge_pct: float = 0.001):
        self.base_delta_threshold = delta_threshold
        self.base_oi_surge_pct = oi_surge_pct

    def _check_order_book_wall(self, order_book: dict, price: float, side: str) -> bool:
        """
        Check karta hai ke price ke paas bara limit wall hai ya nahi.
        side = 'bid' for long absorption, 'ask' for short absorption.
        """
        levels = order_book.get("bids" if side == "bid" else "asks", [])
        if not levels:
            return False

        # Top 10 levels ka total volume
        top_levels = levels[:10]
        total_qty = sum(q for _, q in top_levels)
        avg_qty = total_qty / len(top_levels) if top_levels else 0

        # Agar koi level average se 3x zyada hai, wall maano
        for p, q in top_levels:
            if q > avg_qty * 3 and q > 0:
                return True
        return False

    def _dynamic_thresholds(self, current_data: dict) -> tuple:
        """ATR aur volume ke hisaab se thresholds adjust karo."""
        atr = current_data.get("atr", 0.0)
        price = current_data.get("price", 1.0)
        volume_avg = current_data.get("volume_avg", 0.0)
        volume_chunk = current_data.get("volume_chunk", 0.0)

        # ATR-based delta threshold
        delta_threshold = self.base_delta_threshold
        if atr > 0 and price > 0:
            atr_pct = atr / price
            # Agar volatility zyada hai toh threshold bhi zyada
            delta_threshold = self.base_delta_threshold * (1 + atr_pct * 100)

        # Volume-based OI threshold
        oi_threshold = self.base_oi_surge_pct
        if volume_avg > 0 and volume_chunk > 0:
            vol_ratio = volume_chunk / volume_avg
            # Agar volume zyada hai toh OI threshold thoda kam kar do
            if vol_ratio > 1.5:
                oi_threshold = self.base_oi_surge_pct * 0.8

        return delta_threshold, oi_threshold

    def _calculate_confidence(self, base_conf: int, current_data: dict, delta_threshold: float) -> int:
        """Confidence ko dynamic banao — delta, volume, OI sab dekh kar."""
        conf = base_conf

        delta = abs(current_data.get("delta", 0.0))
        volume_avg = current_data.get("volume_avg", 0.0)
        volume_chunk = current_data.get("volume_chunk", 0.0)

        # Delta threshold se kitna zyada hai
        if delta_threshold > 0:
            delta_ratio = delta / delta_threshold
            if delta_ratio > 2.0:
                conf += 5
            elif delta_ratio > 1.5:
                conf += 3
            elif delta_ratio < 1.1:
                conf -= 5

        # Volume average se kitna zyada hai
        if volume_avg > 0:
            vol_ratio = volume_chunk / volume_avg
            if vol_ratio > 2.0:
                conf += 5
            elif vol_ratio > 1.5:
                conf += 3
            elif vol_ratio < 0.8:
                conf -= 5

        return max(0, min(100, conf))

    def evaluate(self, current_data: dict, prev_state: dict) -> dict:
        price = current_data["price"]
        delta = current_data["delta"]
        oi = current_data["open_interest"]

        signal = {
            "status": "NEUTRAL",
            "reason": "No micro-structure edge identified.",
            "confidence": 0,
            "metrics": current_data
        }

        prev_oi = prev_state.get("oi", 0.0)
        prev_price = prev_state.get("price", 0.0)

        if prev_oi == 0.0 or prev_price == 0.0 or price == 0.0:
            return signal

        price_change = price - prev_price
        oi_change_pct = (oi - prev_oi) / prev_oi

        # Dynamic thresholds
        delta_threshold, oi_threshold = self._dynamic_thresholds(current_data)

        # Order book wall check
        bid_wall = self._check_order_book_wall(
            current_data.get("order_book", {}), price, "bid"
        )
        ask_wall = self._check_order_book_wall(
            current_data.get("order_book", {}), price, "ask"
        )

        # Rule 1: Long Absorption — sirf tab jab bid wall ho
        if price_change <= 0 and delta > delta_threshold and bid_wall:
            conf = self._calculate_confidence(85, current_data, delta_threshold)
            signal = {
                "status": "LONG_ABSORPTION",
                "reason": "Aggressive market buying delta absorbed by passive bid wall (L2 confirmed).",
                "confidence": conf,
                "metrics": current_data
            }
        # Rule 2: Short Absorption — sirf tab jab ask wall ho
        elif price_change >= 0 and delta < -delta_threshold and ask_wall:
            conf = self._calculate_confidence(85, current_data, delta_threshold)
            signal = {
                "status": "SHORT_ABSORPTION",
                "reason": "Aggressive market selling delta absorbed by passive ask wall (L2 confirmed).",
                "confidence": conf,
                "metrics": current_data
            }
        # Rule 3: Long Fresh Capital
        elif oi_change_pct > oi_threshold and price_change > 0:
            conf = self._calculate_confidence(90, current_data, delta_threshold)
            signal = {
                "status": "LONG_FRESH_CAPITAL",
                "reason": "Price expansion backed by Open Interest expansion (new longs opening).",
                "confidence": conf,
                "metrics": current_data
            }
        # Rule 4: Short Fresh Capital
        elif oi_change_pct > oi_threshold and price_change < 0:
            conf = self._calculate_confidence(90, current_data, delta_threshold)
            signal = {
                "status": "SHORT_FRESH_CAPITAL",
                "reason": "Price collapse backed by Open Interest expansion (new shorts opening).",
                "confidence": conf,
                "metrics": current_data
            }

        return signal
