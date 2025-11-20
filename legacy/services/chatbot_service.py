"""
Chatbot service for the Trading Terminal.
"""
import strategy

def generate_response(user_msg: str, context: dict) -> str:
    """Generate chatbot response based on user message and context."""

    msg_lower = user_msg.lower()

    ticker = context.get("ticker", "N/A")

    # Signal explanations
    if "false breakout" in msg_lower or "false" in msg_lower:
        return f"""A **false breakout** occurs when price breaks above the consolidation high but on **low volume** (< 25th percentile).

This suggests:
- Liquidity was taken (stops above consolidation)
- Lack of follow-through (low volume)
- Likely to reverse back into consolidation

For {ticker}, this could be a **short opportunity** if confirmed."""

    if "true breakout" in msg_lower or "breakout" in msg_lower:
        return f"""A **true breakout** happens when price breaks above consolidation high with **high volume** (>= 75th percentile).

This indicates:
- Strong buying pressure
- Likely continuation move
- Good entry for long positions

The strategy enters long on true breakouts with a stop at consolidation low and 2R target."""

    if "consolidation" in msg_lower:
        return f"""**Consolidation** is when price trades in a tight range (<= 2% of mean price) over the lookback period ({strategy.LOOKBACK_HOURS} hours).

For {ticker}, consolidation bands show:
- **Green line**: Consolidation high (resistance)
- **Red line**: Consolidation low (support)

When price breaks above the green line with volume, it's a breakout signal."""

    if "strategy" in msg_lower or "how does" in msg_lower:
        return f"""**Consolidation + Breakout + Volume Strategy**

1. **Identify Consolidation**: Price in tight range (<= 2% over {strategy.LOOKBACK_HOURS} hours)
2. **Wait for Breakout**: Price breaks above consolidation high
3. **Check Volume**: 
   - High volume (>= 75th percentile) = True breakout (long)
   - Low volume (< 25th percentile) = False breakout (short opportunity)
4. **Enter**: Stop at consolidation low, target at 2R

Currently analyzing: {ticker}"""

    if "backtest" in msg_lower:
        return f"""I can run a backtest! The strategy uses:
- Risk: {strategy.RISK_FRACTION*100}% per trade
- R:R: {strategy.RR_TARGET}:1
- Stop: Consolidation low
- Target: Entry + {strategy.RR_TARGET}R

Would you like me to backtest {ticker} or the full universe?"""

    if "volume" in msg_lower:
        return f"""Volume analysis uses **dynamic thresholds** based on each stock's own distribution:
- **High volume**: >= 75th percentile (green bars)
- **Low volume**: < 25th percentile (red bars)
- **Normal**: Between thresholds (gray bars)

This adapts to each stock's volume profile - a high-volume stock like TSLA has different thresholds than a low-volume stock."""

    # Enhanced context-aware responses
    if ticker != "N/A":
        if "what" in msg_lower and ("signal" in msg_lower or "showing" in msg_lower):
            # Get current signal status with more detail
            # This is now handled by the main window to be reusable
            return "Please ask the main application for analysis."

    # Default response
    return f"""I understand you're asking about: "{user_msg}"

For {ticker}, I can help with:
- Explaining signals (true/false breakouts)
- Strategy mechanics
- Risk/reward analysis
- Backtesting

Try asking: "What signal is {ticker} showing?" or "Explain false breakouts" """
