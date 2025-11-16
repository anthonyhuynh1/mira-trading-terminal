"""
Trading Terminal Application - Cursor-like Interface
Left: Stock Screener | Main: Charts/Fundamentals/News | Right: Context-Aware Chatbot
"""

import sys
import warnings
warnings.filterwarnings("ignore")

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QSplitter, QTextEdit, QLineEdit, 
                             QPushButton, QListWidget, QTabWidget, QLabel, QTableWidget,
                             QTableWidgetItem, QHeaderView, QComboBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor
import matplotlib.pyplot as plt
try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
except ImportError:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# Import our existing strategy code
import strategy
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime


class ChartWidget(QWidget):
    """Main chart display widget with tabs for price, fundamentals, news."""
    
    def __init__(self):
        super().__init__()
        self.current_ticker = None
        self.current_timeframe = "1h"
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Toolbar with timeframe selector
        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("Timeframe:"))
        self.timeframe_combo = QComboBox()
        self.timeframe_combo.addItems(["1h", "4h", "1d"])
        self.timeframe_combo.setCurrentText("1h")
        self.timeframe_combo.currentTextChanged.connect(self.on_timeframe_changed)
        toolbar.addWidget(self.timeframe_combo)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Tabs: Price Chart | Fundamentals | News
        self.tabs = QTabWidget()
        
        # Price Chart Tab
        self.chart_tab = QWidget()
        chart_layout = QVBoxLayout()
        self.figure = Figure(figsize=(12, 8))
        self.canvas = FigureCanvas(self.figure)
        chart_layout.addWidget(self.canvas)
        self.chart_tab.setLayout(chart_layout)
        
        # Fundamentals Tab
        self.fundamentals_tab = QWidget()
        fund_layout = QVBoxLayout()
        self.fundamentals_table = QTableWidget()
        self.fundamentals_table.setColumnCount(2)
        self.fundamentals_table.setHorizontalHeaderLabels(["Metric", "Value"])
        self.fundamentals_table.horizontalHeader().setStretchLastSection(True)
        fund_layout.addWidget(self.fundamentals_table)
        self.fundamentals_tab.setLayout(fund_layout)
        
        # News Tab
        self.news_tab = QWidget()
        news_layout = QVBoxLayout()
        self.news_list = QListWidget()
        news_layout.addWidget(self.news_list)
        self.news_tab.setLayout(news_layout)
        
        self.tabs.addTab(self.chart_tab, "📈 Chart")
        self.tabs.addTab(self.fundamentals_tab, "📊 Fundamentals")
        self.tabs.addTab(self.news_tab, "📰 News")
        
        layout.addWidget(self.tabs)
        self.setLayout(layout)
    
    def load_ticker(self, ticker: str):
        """Load and display ticker data."""
        self.current_ticker = ticker
        self.update_chart(ticker, self.current_timeframe)
        self.update_fundamentals(ticker)
        self.update_news(ticker)
    
    def on_timeframe_changed(self, timeframe: str):
        """Handle timeframe change."""
        self.current_timeframe = timeframe
        if self.current_ticker:
            self.update_chart(self.current_ticker, timeframe)
    
    def update_chart(self, ticker: str, timeframe: str = "1h"):
        """Update price chart with signals - TradingView style with candlesticks."""
        self.figure.clear()
        self.figure.patch.set_facecolor('#131722')  # Dark background
        
        # Map timeframe to period and interval
        timeframe_map = {
            "1h": ("60d", "1h"),
            "4h": ("180d", "4h"),
            "1d": ("1y", "1d")
        }
        period, interval = timeframe_map.get(timeframe, ("60d", "1h"))
        
        # Fetch data
        df = strategy.fetch_hourly_data(ticker, period=period, interval=interval)
        if df.empty:
            ax = self.figure.add_subplot(111)
            ax.set_facecolor('#131722')
            ax.text(0.5, 0.5, f"No data for {ticker}", ha='center', va='center', 
                   color='#787b86', fontsize=14)
            ax.axis('off')
            self.canvas.draw()
            return
        
        # Generate signals
        sigs = strategy.breakout_volume_signals(df)
        
        # Create subplots with dark theme
        ax1 = self.figure.add_subplot(211)
        ax2 = self.figure.add_subplot(212, sharex=ax1)
        
        # Apply dark theme to axes
        for ax in [ax1, ax2]:
            ax.set_facecolor('#131722')
            ax.tick_params(colors='#787b86')
            ax.spines['bottom'].set_color('#2a2e39')
            ax.spines['top'].set_color('#2a2e39')
            ax.spines['right'].set_color('#2a2e39')
            ax.spines['left'].set_color('#2a2e39')
            ax.xaxis.label.set_color('#787b86')
            ax.yaxis.label.set_color('#787b86')
        
        # Price chart - use candlesticks
        self.plot_candlesticks(ax1, df, ticker)
        ax1.plot(sigs.index, sigs["cons_high_prev"], label="Cons High", 
                color="#26a69a", linestyle="--", alpha=0.7, linewidth=1.5)
        ax1.plot(sigs.index, sigs["cons_low_prev"], label="Cons Low", 
                color="#ef5350", linestyle="--", alpha=0.7, linewidth=1.5)
        
        # Mark breakouts
        true_breakouts = sigs.index[sigs["signal"]]
        false_breakouts = sigs.index[sigs["false_breakout"]]
        
        if len(true_breakouts) > 0:
            ax1.scatter(true_breakouts, df.loc[true_breakouts, "Close"], 
                       color="#26a69a", marker="^", s=150, label="True Breakout", 
                       zorder=5, edgecolors="white", linewidths=1)
        if len(false_breakouts) > 0:
            ax1.scatter(false_breakouts, df.loc[false_breakouts, "Close"], 
                       color="#ef5350", marker="v", s=150, label="False Breakout", 
                       zorder=5, edgecolors="white", linewidths=1)
        
        ax1.set_ylabel("Price ($)", color='#787b86', fontsize=10)
        ax1.set_title(f"{ticker} - Consolidation Breakout Analysis ({timeframe})", 
                     color='#d1d4dc', fontsize=12, fontweight='bold')
        legend = ax1.legend(loc='upper left', framealpha=0.9, facecolor='#1e222d', 
                           edgecolor='#2a2e39')
        for text in legend.get_texts():
            text.set_color('#d1d4dc')
        ax1.grid(True, alpha=0.2, color='#2a2e39')
        
        # Volume chart
        colors = []
        vol_high = sigs["vol_high_threshold"]
        vol_low = sigs["vol_low_threshold"]
        
        for idx in df.index:
            if idx not in sigs.index:
                colors.append("gray")
                continue
            vol_val = df.loc[idx, "Volume"]
            high_thresh = vol_high.loc[idx] if idx in vol_high.index else np.nan
            low_thresh = vol_low.loc[idx] if idx in vol_low.index else np.nan
            
            if pd.isna(high_thresh) or pd.isna(low_thresh):
                colors.append("gray")
            elif vol_val >= high_thresh:
                colors.append("green")
            elif vol_val < low_thresh:
                colors.append("red")
            else:
                colors.append("gray")
        
        ax2.bar(df.index, df["Volume"], color=colors, alpha=0.7, width=0.8)
        ax2.plot(sigs.index, vol_high, color="#26a69a", linestyle="--", 
                alpha=0.7, linewidth=1.5, label="High Vol Threshold")
        ax2.plot(sigs.index, vol_low, color="#ef5350", linestyle="--", 
                alpha=0.7, linewidth=1.5, label="Low Vol Threshold")
        ax2.set_ylabel("Volume", color='#787b86', fontsize=10)
        ax2.set_xlabel("Time", color='#787b86', fontsize=10)
        ax2.grid(True, alpha=0.2, color='#2a2e39')
        
        self.figure.tight_layout()
        self.canvas.draw()
    
    def plot_candlesticks(self, ax, df, ticker):
        """Plot candlestick chart."""
        # Sample data for performance (show every Nth candle for large datasets)
        sample_rate = max(1, len(df) // 500)  # Max 500 candles for performance
        df_sample = df.iloc[::sample_rate] if sample_rate > 1 else df
        
        # Determine up/down colors
        up_color = "#26a69a"  # Green for up candles
        down_color = "#ef5350"  # Red for down candles
        
        # Plot candlesticks
        for idx, row in df_sample.iterrows():
            open_price = row["Open"]
            close_price = row["Close"]
            high_price = row["High"]
            low_price = row["Low"]
            
            # Determine if candle is up or down
            is_up = close_price >= open_price
            color = up_color if is_up else down_color
            
            # Draw wick
            ax.plot([idx, idx], [low_price, high_price], color=color, linewidth=1, alpha=0.8)
            
            # Draw body
            body_bottom = min(open_price, close_price)
            body_top = max(open_price, close_price)
            body_height = body_top - body_bottom
            
            if body_height > 0:
                # Rectangle for body
                ax.bar(idx, body_height, bottom=body_bottom, width=0.6, 
                      color=color, alpha=0.8, edgecolor=color, linewidth=1)
            else:
                # Doji - just a line
                ax.plot([idx, idx], [open_price - 0.01, open_price + 0.01], 
                       color=color, linewidth=2, alpha=0.8)
        
        # Also plot close line for reference
        ax.plot(df.index, df["Close"], label=f"{ticker}", 
               color="#2962ff", linewidth=1, alpha=0.3)
    
    def update_fundamentals(self, ticker: str):
        """Update fundamentals table."""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            self.fundamentals_table.setRowCount(0)
            
            metrics = [
                ("Market Cap", info.get("marketCap", "N/A")),
                ("P/E Ratio", info.get("trailingPE", "N/A")),
                ("Forward P/E", info.get("forwardPE", "N/A")),
                ("EPS", info.get("trailingEps", "N/A")),
                ("Dividend Yield", f"{info.get('dividendYield', 0) * 100:.2f}%" if info.get('dividendYield') else "N/A"),
                ("52 Week High", f"${info.get('fiftyTwoWeekHigh', 'N/A')}"),
                ("52 Week Low", f"${info.get('fiftyTwoWeekLow', 'N/A')}"),
                ("Volume (Avg)", info.get("averageVolume", "N/A")),
                ("Beta", info.get("beta", "N/A")),
            ]
            
            for metric, value in metrics:
                row = self.fundamentals_table.rowCount()
                self.fundamentals_table.insertRow(row)
                self.fundamentals_table.setItem(row, 0, QTableWidgetItem(str(metric)))
                self.fundamentals_table.setItem(row, 1, QTableWidgetItem(str(value)))
        
        except Exception as e:
            self.fundamentals_table.setRowCount(1)
            self.fundamentals_table.setItem(0, 0, QTableWidgetItem("Error"))
            self.fundamentals_table.setItem(0, 1, QTableWidgetItem(str(e)))
    
    def update_news(self, ticker: str):
        """Update news list."""
        try:
            stock = yf.Ticker(ticker)
            news = stock.news[:10]  # Get latest 10 news items
            
            self.news_list.clear()
            
            for item in news:
                title = item.get("title", "No title")
                pub_date = datetime.fromtimestamp(item.get("providerPublishTime", 0)).strftime("%Y-%m-%d")
                self.news_list.addItem(f"[{pub_date}] {title}")
        
        except Exception as e:
            self.news_list.addItem(f"Error loading news: {str(e)}")


class ChatbotWidget(QWidget):
    """Context-aware chatbot panel."""
    
    def __init__(self, context_callback):
        super().__init__()
        self.context_callback = context_callback  # Function to get current context
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Chat display
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont("Courier", 10))
        layout.addWidget(self.chat_display)
        
        # Input
        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Ask about the chart, strategy, or ticker...")
        self.input_field.returnPressed.connect(self.send_message)
        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self.send_message)
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_btn)
        layout.addLayout(input_layout)
        
        self.setLayout(layout)
        self.add_bot_message("👋 Hi! I'm your trading assistant. Ask me about charts, signals, or strategies!")
    
    def send_message(self):
        """Handle user message and generate response."""
        user_msg = self.input_field.text().strip()
        if not user_msg:
            return
        
        self.add_user_message(user_msg)
        self.input_field.clear()
        
        # Get context
        context = self.context_callback()
        
        # Generate response
        response = self.generate_response(user_msg, context)
        self.add_bot_message(response)
    
    def add_user_message(self, msg: str):
        """Add user message to chat."""
        self.chat_display.append(f"<b>You:</b> {msg}")
    
    def add_bot_message(self, msg: str):
        """Add bot message to chat."""
        self.chat_display.append(f"<b>Assistant:</b> {msg}")
    
    def generate_response(self, user_msg: str, context: dict) -> str:
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
            return f"""A **true breakout** happens when price breaks above consolidation high with **high volume** (≥ 75th percentile).

This indicates:
- Strong buying pressure
- Likely continuation move
- Good entry for long positions

The strategy enters long on true breakouts with a stop at consolidation low and 2R target."""
        
        if "consolidation" in msg_lower:
            return f"""**Consolidation** is when price trades in a tight range (≤ 2% of mean price) over the lookback period ({strategy.LOOKBACK_HOURS} hours).

For {ticker}, consolidation bands show:
- **Green line**: Consolidation high (resistance)
- **Red line**: Consolidation low (support)

When price breaks above the green line with volume, it's a breakout signal."""
        
        if "strategy" in msg_lower or "how does" in msg_lower:
            return f"""**Consolidation + Breakout + Volume Strategy**

1. **Identify Consolidation**: Price in tight range (≤ 2% over {strategy.LOOKBACK_HOURS} hours)
2. **Wait for Breakout**: Price breaks above consolidation high
3. **Check Volume**: 
   - High volume (≥ 75th percentile) = True breakout (long)
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
- **High volume**: ≥ 75th percentile (green bars)
- **Low volume**: < 25th percentile (red bars)
- **Normal**: Between thresholds (gray bars)

This adapts to each stock's volume profile - a high-volume stock like TSLA has different thresholds than a low-volume stock."""
        
        # Enhanced context-aware responses
        if ticker != "N/A":
            if "what" in msg_lower and ("signal" in msg_lower or "showing" in msg_lower):
                # Get current signal status with more detail
                try:
                    df = strategy.fetch_hourly_data(ticker, period="30d")
                    if not df.empty:
                        sigs = strategy.breakout_volume_signals(df)
                        last_sig = sigs.iloc[-1]
                        current_price = df["Close"].iloc[-1]
                        cons_high = float(last_sig["cons_high_prev"]) if not np.isnan(last_sig["cons_high_prev"]) else None
                        cons_low = float(last_sig["cons_low_prev"]) if not np.isnan(last_sig["cons_low_prev"]) else None
                        
                        if bool(last_sig["false_breakout"]):
                            return f"""**{ticker} - FALSE BREAKOUT Signal** ⚠️

Current Price: ${current_price:.2f}
Consolidation Range: ${cons_low:.2f} - ${cons_high:.2f}

**Analysis:**
- Price broke above consolidation high but on LOW volume (< 25th percentile)
- This suggests liquidity was taken but lacks follow-through
- **Potential short opportunity** if price rejects and returns below ${cons_high:.2f}

**Risk Management:**
- Stop: Above recent high
- Target: Back to consolidation low ${cons_low:.2f}"""
                        
                        elif bool(last_sig["signal"]):
                            return f"""**{ticker} - TRUE BREAKOUT Signal** 🔥

Current Price: ${current_price:.2f}
Consolidation Range: ${cons_low:.2f} - ${cons_high:.2f}

**Analysis:**
- Price broke above consolidation high with HIGH volume (≥ 75th percentile)
- Strong buying pressure indicates continuation
- **Long entry opportunity**

**Trade Setup:**
- Entry: Current price or pullback to ${cons_high:.2f}
- Stop: ${cons_low:.2f} (consolidation low)
- Target: ${current_price + (current_price - cons_low) * strategy.RR_TARGET:.2f} (2R target)
- Risk/Reward: 1:{strategy.RR_TARGET}"""
                        
                        elif bool(last_sig["cons_ok"]):
                            breakout_level = float(last_sig["breakout_level"])
                            dist_pct = ((breakout_level - current_price) / current_price) * 100
                            return f"""**{ticker} - CONSOLIDATION SETUP** 📊

Current Price: ${current_price:.2f}
Consolidation Range: ${cons_low:.2f} - ${cons_high:.2f}
Breakout Level: ${breakout_level:.2f}
Distance to Breakout: {dist_pct:.2f}%

**Status:** Waiting for breakout
**Action:** Monitor for volume confirmation when price approaches ${breakout_level:.2f}"""
                        else:
                            return f"{ticker} is not showing a setup currently. No consolidation detected in the last {strategy.LOOKBACK_HOURS} hours."
                except Exception as e:
                    return f"Error analyzing {ticker}: {str(e)}"
        
        # Default response
        return f"""I understand you're asking about: "{user_msg}"

For {ticker}, I can help with:
- Explaining signals (true/false breakouts)
- Strategy mechanics
- Risk/reward analysis
- Backtesting

Try asking: "What signal is {ticker} showing?" or "Explain false breakouts" """


class ScreenerWidget(QWidget):
    """Left sidebar: Stock screener and search."""
    
    def __init__(self, ticker_callback):
        super().__init__()
        self.ticker_callback = ticker_callback  # Callback when ticker selected
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Search box
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search ticker...")
        self.search_input.returnPressed.connect(self.search_ticker)
        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self.search_ticker)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_btn)
        layout.addLayout(search_layout)
        
        # Quick scan button
        scan_btn = QPushButton("🔍 Scan Universe")
        scan_btn.clicked.connect(self.scan_universe)
        layout.addWidget(scan_btn)
        
        # Ticker list
        self.ticker_list = QListWidget()
        self.ticker_list.itemDoubleClicked.connect(self.on_ticker_selected)
        layout.addWidget(QLabel("Watchlist:"))
        layout.addWidget(self.ticker_list)
        
        # Load default tickers
        for ticker in strategy.TICKERS:
            self.ticker_list.addItem(ticker)
        
        self.setLayout(layout)
    
    def search_ticker(self):
        """Search and add ticker."""
        ticker = self.search_input.text().strip().upper()
        if ticker and ticker not in [self.ticker_list.item(i).text() for i in range(self.ticker_list.count())]:
            self.ticker_list.addItem(ticker)
            self.ticker_list.setCurrentRow(self.ticker_list.count() - 1)
            self.ticker_callback(ticker)
        self.search_input.clear()
    
    def scan_universe(self):
        """Run scanner on universe."""
        # This would trigger scanner - for now just show message
        self.ticker_list.addItem("🔍 Scanning...")
    
    def on_ticker_selected(self, item):
        """Handle ticker selection."""
        ticker = item.text().replace("🔍 ", "")
        self.ticker_callback(ticker)


class TradingTerminal(QMainWindow):
    """Main application window - Cursor-like interface."""
    
    def __init__(self):
        super().__init__()
        self.current_ticker = None
        self.current_timeframe = "1h"  # Track current timeframe for context
        self.init_ui()
        self.apply_dark_theme()
    
    def apply_dark_theme(self):
        """Apply TradingView-like dark theme."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e222d;
            }
            QWidget {
                background-color: #1e222d;
                color: #d1d4dc;
            }
            QListWidget {
                background-color: #131722;
                border: 1px solid #2a2e39;
                color: #d1d4dc;
            }
            QListWidget::item:selected {
                background-color: #2962ff;
                color: white;
            }
            QLineEdit {
                background-color: #131722;
                border: 1px solid #2a2e39;
                color: #d1d4dc;
                padding: 5px;
            }
            QPushButton {
                background-color: #2962ff;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1e53e5;
            }
            QTabWidget::pane {
                background-color: #131722;
                border: 1px solid #2a2e39;
            }
            QTabBar::tab {
                background-color: #1e222d;
                color: #787b86;
                padding: 8px 16px;
                border: none;
            }
            QTabBar::tab:selected {
                background-color: #131722;
                color: #2962ff;
                border-bottom: 2px solid #2962ff;
            }
            QTextEdit {
                background-color: #131722;
                border: 1px solid #2a2e39;
                color: #d1d4dc;
            }
            QTableWidget {
                background-color: #131722;
                border: 1px solid #2a2e39;
                color: #d1d4dc;
                gridline-color: #2a2e39;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #1e222d;
                color: #787b86;
                padding: 5px;
                border: none;
            }
        """)
    
    def init_ui(self):
        self.setWindowTitle("Trading Terminal - AI Assistant")
        self.setGeometry(100, 100, 1600, 900)
        
        # Central widget with splitter
        central_widget = QWidget()
        main_layout = QHBoxLayout()
        
        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left: Screener (20%)
        self.screener = ScreenerWidget(self.on_ticker_selected)
        splitter.addWidget(self.screener)
        
        # Middle: Charts (60%)
        self.chart_widget = ChartWidget()
        splitter.addWidget(self.chart_widget)
        
        # Right: Chatbot (20%)
        self.chatbot = ChatbotWidget(self.get_context)
        splitter.addWidget(self.chatbot)
        
        # Set splitter sizes
        splitter.setSizes([300, 900, 400])
        
        main_layout.addWidget(splitter)
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        
        # Load first ticker by default
        if strategy.TICKERS:
            self.on_ticker_selected(strategy.TICKERS[0])
    
    def on_ticker_selected(self, ticker: str):
        """Handle ticker selection."""
        self.current_ticker = ticker
        self.current_timeframe = self.chart_widget.current_timeframe
        self.chart_widget.load_ticker(ticker)
        self.chatbot.add_bot_message(f"📊 Loaded {ticker} ({self.current_timeframe}). Ask me about its signals or strategy!")
    
    def get_context(self) -> dict:
        """Get current context for chatbot - enhanced with more details."""
        return {
            "ticker": self.current_ticker or "N/A",
            "timeframe": self.chart_widget.current_timeframe if hasattr(self.chart_widget, 'current_timeframe') else self.current_timeframe,
            "timestamp": datetime.now().isoformat(),
            "chart_type": "candlestick_with_signals",
            "view": "main_chart"
        }


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Modern look
    
    window = TradingTerminal()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

