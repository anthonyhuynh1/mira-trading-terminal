import warnings
warnings.filterwarnings("ignore")

import math
import sys
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf


# ----------------------------
# Configuration (edit freely)
# ----------------------------
TICKERS = [
    "SPY", "QQQ", "AAPL", "MSFT", "NVDA", "AMD", "TSLA", "META"
]

# Data
HOURLY_PERIOD = "180d"   # up to ~730d supported by yfinance for 1h on many tickers
HOURLY_INTERVAL = "1h"
DAILY_PERIOD = "365d"

# Strategy params (v0)
LOOKBACK_HOURS = 20              # consolidation lookback window
MAX_RANGE_PCT = 0.02             # max (high-low)/mean(close) over LOOKBACK_HOURS to qualify as "tight"
BREAKOUT_BUFFER_PCT = 0.001      # small buffer above consolidation high (0.1%) to confirm breakout
# Dynamic volume thresholds (percentiles relative to each stock's own volume distribution)
VOLUME_HIGH_PERCENTILE = 0.75    # high volume threshold: >= 75th percentile of rolling volume
VOLUME_LOW_PERCENTILE = 0.25     # low volume threshold: < 25th percentile of rolling volume
NEAR_BREAKOUT_PCT = 0.005        # scanner: within 0.5% of breakout level counts as "near"

# Backtest params
STARTING_CAPITAL = 100_000.0
RISK_FRACTION = 0.01             # risk 1% of current equity per trade
RR_TARGET = 2.0                  # 2R target
SLIPPAGE_PCT = 0.0005            # 5 bps slippage per fill (simple)
SHOW_PLOTS = True


# ----------------------------
# Data utilities
# ----------------------------
def fetch_hourly_data(ticker: str, period: str = HOURLY_PERIOD, interval: str = HOURLY_INTERVAL) -> pd.DataFrame:
    df = yf.download(ticker, period=period, interval=interval, auto_adjust=True, progress=False)
    if df is None or df.empty:
        return pd.DataFrame()
    # Handle MultiIndex columns if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    # Normalize column names to title case
    df.columns = [col.title() if isinstance(col, str) else col for col in df.columns]
    # Only dropna on columns that exist
    required_cols = ["Close", "High", "Low", "Open", "Volume"]
    existing_cols = [col for col in required_cols if col in df.columns]
    if existing_cols:
        df = df.dropna(subset=existing_cols)
    return df


def fetch_daily_data(ticker: str, period: str = DAILY_PERIOD) -> pd.DataFrame:
    df = yf.download(ticker, period=period, interval="1d", auto_adjust=True, progress=False)
    if df is None or df.empty:
        return pd.DataFrame()
    # Handle MultiIndex columns if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    # Normalize column names to title case
    df.columns = [col.title() if isinstance(col, str) else col for col in df.columns]
    # Only dropna on columns that exist
    required_cols = ["Close", "High", "Low", "Open", "Volume"]
    existing_cols = [col for col in required_cols if col in df.columns]
    if existing_cols:
        df = df.dropna(subset=existing_cols)
    return df


def fetch_many_hourly(tickers: list[str]) -> dict[str, pd.DataFrame]:
    data = {}
    for t in tickers:
        df = fetch_hourly_data(t)
        if not df.empty:
            data[t] = df
    return data


# ----------------------------
# Indicators & signals
# ----------------------------
def rolling_consolidation_bands(df: pd.DataFrame, lookback: int) -> pd.DataFrame:
    """
    Compute prior-window consolidation bands excluding current bar.
    Returns DataFrame with:
      cons_high_prev, cons_low_prev, cons_range_pct, cons_ok
    """
    high_prev = df["High"].shift(1).rolling(lookback, min_periods=lookback).max()
    low_prev = df["Low"].shift(1).rolling(lookback, min_periods=lookback).min()
    mean_close_prev = df["Close"].shift(1).rolling(lookback, min_periods=lookback).mean()
    cons_range = (high_prev - low_prev)
    cons_range_pct = cons_range / mean_close_prev
    cons_ok = cons_range_pct <= MAX_RANGE_PCT
    out = pd.DataFrame({
        "cons_high_prev": high_prev,
        "cons_low_prev": low_prev,
        "cons_range_pct": cons_range_pct,
        "cons_ok": cons_ok
    }, index=df.index)
    return out


def breakout_volume_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate breakout + volume signals using dynamic, stock-specific volume thresholds.
    Uses percentiles relative to each stock's own volume distribution.
    Signals:
      - signal: true breakout (breakout + high volume >= 75th percentile)
      - false_breakout: false breakout (breakout + low volume < 25th percentile)
    """
    cons = rolling_consolidation_bands(df, LOOKBACK_HOURS)
    
    # Dynamic volume thresholds based on each stock's own volume distribution
    # Use rolling percentiles to adapt to each stock's volume characteristics
    vol_high_threshold = df["Volume"].rolling(LOOKBACK_HOURS, min_periods=LOOKBACK_HOURS).quantile(VOLUME_HIGH_PERCENTILE)
    vol_low_threshold = df["Volume"].rolling(LOOKBACK_HOURS, min_periods=LOOKBACK_HOURS).quantile(VOLUME_LOW_PERCENTILE)
    avg_vol = df["Volume"].rolling(LOOKBACK_HOURS, min_periods=LOOKBACK_HOURS).mean()
    
    breakout_level = cons["cons_high_prev"] * (1.0 + BREAKOUT_BUFFER_PCT)
    breakout = (df["Close"] > breakout_level) & cons["cons_ok"]
    
    # Volume conditions - dynamic thresholds relative to each stock
    vol_ok = df["Volume"] >= vol_high_threshold
    vol_low = df["Volume"] < vol_low_threshold
    
    # True breakout: breakout + high volume (>= 75th percentile)
    signal = breakout & vol_ok
    
    # False breakout: breakout + low volume (< 25th percentile, takes liquidity but likely to reverse)
    false_breakout = breakout & vol_low & cons["cons_ok"]
    
    out = pd.DataFrame({
        "breakout_level": breakout_level,
        "signal": signal,
        "false_breakout": false_breakout,
        "vol_ok": vol_ok,
        "vol_high_threshold": vol_high_threshold,  # dynamic high threshold
        "vol_low_threshold": vol_low_threshold,    # dynamic low threshold
        "vol_ratio": df["Volume"] / avg_vol  # volume relative to average (for display)
    }, index=df.index)
    out = pd.concat([out, cons], axis=1)
    return out


# ----------------------------
# Backtest engine (long-only)
# ----------------------------
def simulate_trades_for_ticker(ticker: str, df: pd.DataFrame) -> tuple[list[dict], pd.Series]:
    """
    Enter on signal bar at close (with slippage), stop at cons_low_prev, target = entry + RR * (entry - stop).
    If both stop and target touch in same bar after entry, assume stop first (conservative).
    Returns:
      - trades: list of dicts
      - equity_steps: Series indexed by exit time with cumulative equity
    """
    sigs = breakout_volume_signals(df)
    trades: list[dict] = []
    equity = STARTING_CAPITAL
    cum_equity_by_exit: list[tuple[pd.Timestamp, float]] = []
    in_position = False
    entry_price = None
    stop_price = None
    target_price = None
    shares = 0
    entry_time = None

    for ts, row in df.iterrows():
        if not in_position:
            if bool(sigs.loc[ts, "signal"]):
                entry_raw = row["Close"]
                entry_price = entry_raw * (1.0 + SLIPPAGE_PCT)
                stop_price = float(sigs.loc[ts, "cons_low_prev"])
                if np.isnan(stop_price) or stop_price <= 0 or stop_price >= entry_price:
                    continue
                risk_per_share = entry_price - stop_price
                risk_amount = equity * RISK_FRACTION
                if risk_per_share <= 0:
                    continue
                shares = math.floor(risk_amount / risk_per_share)
                if shares <= 0:
                    continue
                target_price = entry_price + RR_TARGET * risk_per_share
                entry_time = ts
                in_position = True
        else:
            low = row["Low"]
            high = row["High"]
            exit_ts = ts
            exit_reason = None
            exit_price = None

            # Conservative sequencing: stop before target if both touched
            if low <= stop_price:
                exit_price = stop_price * (1.0 - SLIPPAGE_PCT)
                exit_reason = "STOP"
            elif high >= target_price:
                exit_price = target_price * (1.0 - SLIPPAGE_PCT)
                exit_reason = "TARGET"

            # If last bar and still open, close at close
            is_last_bar = (ts == df.index[-1])
            if exit_reason is None and is_last_bar:
                exit_price = row["Close"] * (1.0 - SLIPPAGE_PCT)
                exit_reason = "EOD"

            if exit_reason is not None:
                pnl = (exit_price - entry_price) * shares
                equity += pnl
                trade = {
                    "ticker": ticker,
                    "entry_time": entry_time,
                    "entry": entry_price,
                    "stop": stop_price,
                    "target": target_price,
                    "shares": shares,
                    "exit_time": exit_ts,
                    "exit": exit_price,
                    "pnl": pnl,
                    "return_pct": pnl / (entry_price * max(shares, 1)) if shares > 0 else 0.0,
                    "reason": exit_reason
                }
                trades.append(trade)
                cum_equity_by_exit.append((exit_ts, equity))
                in_position = False
                entry_price = stop_price = target_price = None
                shares = 0
                entry_time = None

    if cum_equity_by_exit:
        times, values = zip(*sorted(cum_equity_by_exit, key=lambda x: x[0]))
        equity_series = pd.Series(values, index=pd.DatetimeIndex(times, name="exit_time"))
    else:
        # Return empty Series if no trades
        equity_series = pd.Series(dtype=float)
    return trades, equity_series


def run_backtest(tickers: list[str]) -> tuple[pd.DataFrame, pd.Series]:
    all_trades: list[dict] = []
    all_equity_steps: list[pd.Series] = []

    for i, t in enumerate(tickers, 1):
        print(f"  Processing {t} ({i}/{len(tickers)})...", end=" ", flush=True)
        df = fetch_hourly_data(t)
        if df.empty:
            print("(no data)")
            continue
        trades, eq = simulate_trades_for_ticker(t, df)
        all_trades.extend(trades)
        if not eq.empty:
            all_equity_steps.append(eq)
        print(f"(found {len(trades)} trades)")

    trades_df = pd.DataFrame(all_trades)
    if all_equity_steps:
        combined = pd.concat(all_equity_steps).sort_index()
        # Handle duplicate indices by taking the last value at each timestamp
        equity_curve = combined.groupby(combined.index).last()
        equity_curve = equity_curve.ffill()
        equity_curve = pd.concat([pd.Series([STARTING_CAPITAL], index=pd.DatetimeIndex([equity_curve.index[0] - pd.Timedelta(minutes=1)])), equity_curve])
    else:
        equity_curve = pd.Series([STARTING_CAPITAL], index=pd.DatetimeIndex([pd.Timestamp.utcnow()]))
    return trades_df, equity_curve


# ----------------------------
# Scanner
# ----------------------------
def scan_setups(tickers: list[str]) -> pd.DataFrame:
    rows = []
    for i, t in enumerate(tickers, 1):
        print(f"  Scanning {t} ({i}/{len(tickers)})...", end=" ", flush=True)
        try:
            # For scanner, we only need recent data (30 days is plenty)
            df = fetch_hourly_data(t, period="30d", interval=HOURLY_INTERVAL)
        except Exception as e:
            print(f"(error: {str(e)[:30]})")
            continue
        if df.empty or len(df) < LOOKBACK_HOURS + 2:
            print("(insufficient data)")
            continue
        try:
            sigs = breakout_volume_signals(df)
            last = df.iloc[-1]
            last_sig = sigs.iloc[-1]
            breakout_level = float(last_sig["breakout_level"])
            cons_high = float(last_sig["cons_high_prev"]) if not np.isnan(last_sig["cons_high_prev"]) else np.nan
            cons_low = float(last_sig["cons_low_prev"]) if not np.isnan(last_sig["cons_low_prev"]) else np.nan
            cons_ok = bool(last_sig["cons_ok"])
            vol_ok = bool(last_sig["vol_ok"])
            price = float(last["Close"])
            vol_ratio = float(last_sig["vol_ratio"]) if not np.isnan(last_sig["vol_ratio"]) else 0.0
            
            # Calculate distance to breakout level
            if not np.isnan(breakout_level) and breakout_level > 0:
                dist_to_breakout_pct = ((breakout_level - price) / price) * 100.0
            else:
                dist_to_breakout_pct = np.nan
            
            near = cons_ok and (0.0 <= dist_to_breakout_pct <= NEAR_BREAKOUT_PCT * 100) if not np.isnan(dist_to_breakout_pct) else False
            just_broke = bool(last_sig["signal"])  # true breakout + volume on last bar
            false_broke = bool(last_sig["false_breakout"])  # false breakout (low volume) on last bar
            
            status = "NONE"
            if false_broke:
                status = "FALSE_BREAKOUT"  # Low volume breakout - likely reversal
            elif just_broke:
                status = "BREAKOUT"  # High volume breakout - continuation
            elif cons_ok and vol_ok and near:
                status = "NEAR"
            elif cons_ok:
                status = "SETUP"
            
            rows.append({
                "Ticker": t,
                "Status": status,
                "Price": round(price, 2),
                "ConsHigh": round(cons_high, 2) if not np.isnan(cons_high) else np.nan,
                "ConsLow": round(cons_low, 2) if not np.isnan(cons_low) else np.nan,
                "DistToBreakout%": round(dist_to_breakout_pct, 2) if not np.isnan(dist_to_breakout_pct) else np.nan,
                "RangePct": round(float(last_sig["cons_range_pct"]) * 100.0, 2) if not np.isnan(last_sig["cons_range_pct"]) else np.nan,
                "VolRatio": round(vol_ratio, 2)
            })
            print(f"({status})")
        except Exception as e:
            print(f"(processing error: {str(e)[:30]})")
            continue
    scan_df = pd.DataFrame(rows).sort_values(by=["Status", "RangePct"], ascending=[True, True])
    return scan_df


# ----------------------------
# Reporting & plots
# ----------------------------
def print_backtest_summary(trades_df: pd.DataFrame) -> None:
    """Print comprehensive backtest summary with detailed statistics."""
    if trades_df.empty:
        print("No trades generated.")
        return
    
    total_trades = len(trades_df)
    wins = int((trades_df["pnl"] > 0).sum())
    losses = total_trades - wins
    win_rate = wins / total_trades if total_trades > 0 else 0.0
    
    total_pnl = trades_df["pnl"].sum()
    avg_pnl = trades_df["pnl"].mean()
    
    winning_trades = trades_df[trades_df["pnl"] > 0]
    losing_trades = trades_df[trades_df["pnl"] <= 0]
    
    avg_win = winning_trades["pnl"].mean() if len(winning_trades) > 0 else 0.0
    avg_loss = losing_trades["pnl"].mean() if len(losing_trades) > 0 else 0.0
    profit_factor = abs(winning_trades["pnl"].sum() / losing_trades["pnl"].sum()) if len(losing_trades) > 0 and losing_trades["pnl"].sum() != 0 else float('inf')
    
    rr_hits = int((trades_df["reason"] == "TARGET").sum())
    stops = int((trades_df["reason"] == "STOP").sum())
    eod_closes = int((trades_df["reason"] == "EOD").sum())
    
    # Calculate return percentage
    total_return_pct = (total_pnl / STARTING_CAPITAL) * 100
    
    print("\n" + "="*80)
    print("BACKTEST RESULTS SUMMARY")
    print("="*80)
    print(f"\n📊 Trade Statistics:")
    print(f"   Total Trades: {total_trades}")
    print(f"   Wins: {wins} ({win_rate:.1%}) | Losses: {losses} ({1-win_rate:.1%})")
    print(f"   Target Hits: {rr_hits} | Stops: {stops} | EOD Closes: {eod_closes}")
    
    print(f"\n💰 P&L Summary:")
    print(f"   Total P&L: ${total_pnl:,.2f} ({total_return_pct:+.2f}%)")
    print(f"   Average P&L per Trade: ${avg_pnl:,.2f}")
    print(f"   Average Win: ${avg_win:,.2f} | Average Loss: ${avg_loss:,.2f}")
    print(f"   Profit Factor: {profit_factor:.2f}" if profit_factor != float('inf') else "   Profit Factor: N/A (no losses)")
    
    print(f"\n📈 Performance Metrics:")
    print(f"   Starting Capital: ${STARTING_CAPITAL:,.2f}")
    print(f"   Ending Equity: ${STARTING_CAPITAL + total_pnl:,.2f}")
    print(f"   Risk per Trade: {RISK_FRACTION*100:.1f}% | Target R:R: {RR_TARGET:.1f}:1")
    print("="*80)


def plot_equity_curve(equity_curve: pd.Series) -> None:
    """Plot equity curve with drawdown overlay."""
    if equity_curve.empty:
        return
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 6), height_ratios=[3, 1], sharex=True)
    
    # Equity curve
    ax1.plot(equity_curve.index, equity_curve.values, label="Equity", color="blue", linewidth=2)
    ax1.axhline(y=STARTING_CAPITAL, color="gray", linestyle="--", alpha=0.5, label="Starting Capital")
    ax1.fill_between(equity_curve.index, STARTING_CAPITAL, equity_curve.values, 
                     where=(equity_curve.values >= STARTING_CAPITAL), alpha=0.3, color="green", label="Profit")
    ax1.fill_between(equity_curve.index, STARTING_CAPITAL, equity_curve.values, 
                     where=(equity_curve.values < STARTING_CAPITAL), alpha=0.3, color="red", label="Loss")
    ax1.set_ylabel("Equity ($)", fontsize=11)
    ax1.set_title("Backtest Equity Curve (by trade exits)", fontsize=12, fontweight="bold")
    ax1.legend(loc="best", fontsize=9)
    ax1.grid(True, alpha=0.3)
    
    # Drawdown
    running_max = equity_curve.expanding().max()
    drawdown = ((equity_curve - running_max) / running_max) * 100
    ax2.fill_between(drawdown.index, 0, drawdown.values, alpha=0.5, color="red", label="Drawdown")
    ax2.set_ylabel("Drawdown (%)", fontsize=11)
    ax2.set_xlabel("Time", fontsize=11)
    ax2.legend(loc="best", fontsize=9)
    ax2.grid(True, alpha=0.3)
    ax2.invert_yaxis()
    
    plt.tight_layout()
    plt.show()


def plot_example_ticker(ticker: str) -> None:
    df = fetch_hourly_data(ticker)
    if df.empty:
        return
    sigs = breakout_volume_signals(df)
    plt.figure(figsize=(10, 5))
    plt.plot(df.index, df["Close"], label=f"{ticker} Close", color="black", linewidth=1)
    # Plot consolidation bands
    plt.plot(sigs.index, sigs["cons_high_prev"], label="Cons High", color="green", alpha=0.7)
    plt.plot(sigs.index, sigs["cons_low_prev"], label="Cons Low", color="red", alpha=0.7)
    # Mark true breakouts (high volume)
    signals_idx = sigs.index[sigs["signal"]]
    plt.scatter(signals_idx, df.loc[signals_idx, "Close"], color="blue", marker="^", s=100, label="True Breakout (High Vol)", zorder=5)
    # Mark false breakouts (low volume)
    false_breakout_idx = sigs.index[sigs["false_breakout"]]
    plt.scatter(false_breakout_idx, df.loc[false_breakout_idx, "Close"], color="orange", marker="v", s=100, label="False Breakout (Low Vol)", zorder=5)
    plt.title(f"{ticker} - 1h Consolidation/Breakout/Volume (True vs False)")
    plt.xlabel("Time")
    plt.ylabel("Price")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()


# ----------------------------
# Main
# ----------------------------
def main() -> None:
    print("="*80)
    print("CONSOLIDATION + BREAKOUT + VOLUME STRATEGY")
    print("="*80)
    print("\nPart 1: Backtesting historical performance...")
    trades_df, equity_curve = run_backtest(TICKERS)
    print_backtest_summary(trades_df)
    if SHOW_PLOTS:
        plot_equity_curve(equity_curve)
        # Show one example plot from the universe (first available)
        for t in TICKERS:
            plot_example_ticker(t)
            break

    print("\n" + "="*80)
    print("DAILY SCANNER - Current Trading Setups (1h timeframe)")
    print("="*80)
    scan_df = scan_setups(TICKERS)
    if scan_df.empty:
        print("No valid data or setups found.")
    else:
        # Separate by status for clarity
        false_breakouts = scan_df[scan_df["Status"] == "FALSE_BREAKOUT"]
        breakouts = scan_df[scan_df["Status"] == "BREAKOUT"]
        near = scan_df[scan_df["Status"] == "NEAR"]
        setups = scan_df[scan_df["Status"] == "SETUP"]
        
        if not false_breakouts.empty:
            print("\n⚠️  FALSE BREAKOUTS (Low volume breakout - likely reversal, consider short):")
            print(false_breakouts[["Ticker", "Price", "ConsHigh", "DistToBreakout%", "RangePct", "VolRatio"]].to_string(index=False))
        
        if not breakouts.empty:
            print("\n🔥 BREAKOUTS (High volume breakout - continuation, review now!):")
            print(breakouts[["Ticker", "Price", "ConsHigh", "DistToBreakout%", "RangePct", "VolRatio"]].to_string(index=False))
        
        if not near.empty:
            print("\n⚡ NEAR BREAKOUT (Close to breaking out - watch closely):")
            print(near[["Ticker", "Price", "ConsHigh", "DistToBreakout%", "RangePct", "VolRatio"]].to_string(index=False))
        
        if not setups.empty:
            print("\n📊 SETUPS (Consolidating - waiting for breakout):")
            print(setups[["Ticker", "Price", "ConsHigh", "DistToBreakout%", "RangePct", "VolRatio"]].to_string(index=False))
        
        print("\n" + "="*80)
        print(f"Total tickers scanned: {len(scan_df)}")
        print(f"⚠️  False Breakouts: {len(false_breakouts)} | 🔥 Breakouts: {len(breakouts)} | ⚡ Near: {len(near)} | 📊 Setups: {len(setups)}")
        print("="*80)


if __name__ == "__main__":
    main()



