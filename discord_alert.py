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
            "color": 3447003, # Blue color for summary
            "footer": {"text": "Institutional Bot • Periodic Session Check"}
        }

        payload = {"embeds": [embed]}
        try:
            requests.post(self.webhook_url, json=payload, timeout=5)
        except Exception as e:
            logger.error(f"Summary webhook failed: {e}")
