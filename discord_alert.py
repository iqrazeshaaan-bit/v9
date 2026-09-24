import requests
import logging

logger = logging.getLogger("DiscordAlert")


class DiscordNotifier:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def _calculate_risk_levels(self, analysis: dict):
        """ATR ke hisaab se stop loss aur take profit."""
        metrics = analysis["metrics"]
        price = metrics["price"]
        atr = metrics.get("atr", 0.0)

        if atr <= 0 or price <= 0:
            return None, None

        sl_mult = 1.5
        tp_mult = 2.5

        if "LONG" in analysis["status"]:
            sl = price - (atr * sl_mult)
            tp = price + (atr * tp_mult)
        else:
            sl = price + (atr * sl_mult)
            tp = price - (atr * tp_mult)

        return round(sl, 2), round(tp, 2)

    def send_signal(self, analysis: dict):
        if not self.webhook_url or analysis["status"] == "NEUTRAL":
            return

        metrics = analysis["metrics"]
        color = 3066993 if "LONG" in analysis["status"] else 15158332

        sl, tp = self._calculate_risk_levels(analysis)

        fields = [
            {"name": "Signal", "value": f"**{analysis['status']}**", "inline": False},
            {"name": "Rationale", "value": analysis["reason"], "inline": False},
            {"name": "Price", "value": f"${metrics['price']:,.2f}", "inline": True},
            {"name": "Delta", "value": f"{metrics['delta']:,.2f}", "inline": True},
            {"name": "Open Interest", "value": f"{metrics['open_interest']:,.2f}", "inline": True},
            {"name": "Confidence", "value": f"{analysis['confidence']}%", "inline": True},
            {"name": "ATR", "value": f"{metrics.get('atr', 0):,.2f}", "inline": True},
            {"name": "Volume vs Avg", "value": f"{metrics.get('volume_chunk', 0):,.0f} / {metrics.get('volume_avg', 0):,.0f}", "inline": True},
        ]

        if sl and tp:
            fields.append({"name": "Stop Loss", "value": f"${sl:,.2f}", "inline": True})
            fields.append({"name": "Take Profit", "value": f"${tp:,.2f}", "inline": True})

        embed = {
            "title": f"🚨 ORDER FLOW SIGNAL: {metrics['symbol']}",
            "color": color,
            "fields": fields,
            "footer": {"text": "Deterministic Quantitative Engine • Multi-Coin GitHub Runner"}
        }

        payload = {"embeds": [embed]}

        try:
            response = requests.post(self.webhook_url, json=payload, timeout=5)
            if response.status_code != 204:
                logger.error(f"Discord alert failed. Status: {response.status_code}")
        except Exception as e:
            logger.error(f"Discord notification exception: {e}")

    def send_session_summary(self, results: list):
        if not self.webhook_url:
            return
        
        description = "Scanned all target coins. Market status overview:\n\n"
        for r in results:
            icon = "🟢" if r["status"] != "NEUTRAL" else "⚪"
            description += f"{icon} **{r['symbol']}**: `{r['status']}` (${r['price']:,.2f})\n"

        embed = {
            "title": "📊 15-Min Market Scan Summary",
            "description": description,
            "color": 3447003,
            "footer": {"text": "Institutional Bot • Periodic Session Check"}
        }

        payload = {"embeds": [embed]}
        try:
            requests.post(self.webhook_url, json=payload, timeout=5)
        except Exception as e:
            logger.error(f"Summary webhook failed: {e}")
