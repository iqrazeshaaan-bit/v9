# Ek list bana lo saare results collect karne ke liye
    summary_results = []

    for symbol in config.SYMBOLS_LIST:
        logger.info(f"--- {symbol} ---")
        engine = DataEngine(symbol=symbol)

        market_data = engine.fetch_market_data()
        if market_data["price"] == 0.0:
            logger.warning(f"Empty price for {symbol}, skipping.")
            continue

        market_data["timestamp"] = datetime.now(timezone.utc).isoformat()

        prev_state = all_states.get(symbol, {"price": 0.0, "oi": 0.0})
        analysis = analyzer.evaluate(market_data, prev_state)

        logger.info(
            f"{symbol} -> {analysis['status']} | "
            f"Price: ${market_data['price']:,.2f} | "
            f"Conf: {analysis['confidence']}%"
        )

        # Result save karo summary ke liye
        summary_results.append({
            "symbol": symbol,
            "status": analysis["status"],
            "price": market_data["price"]
        })

        if analysis["status"] != "NEUTRAL":
            notifier.send_signal(analysis)
            state_mgr.log_signal(analysis)
            logger.info(f"Signal dispatched: {analysis['status']}")

        all_states[symbol] = {
            "price": market_data["price"],
            "oi": market_data["open_interest"]
        }

    state_mgr.save_state(all_states)

    # --- Yahan hum ek Session Summary Discord par bhejenge ---
    notifier.send_session_summary(summary_results)
