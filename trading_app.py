"""
Trading Terminal Application - Cursor-like Interface
Left: Stock Screener | Main: Charts/Fundamentals/News | Right: Context-Aware Chatbot
"""

import sys
import warnings
warnings.filterwarnings("ignore")

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QTextEdit, QLineEdit,
                             QPushButton, QListWidget, QTabWidget, QLabel, QTableWidget,
                             QTableWidgetItem, QHeaderView, QDockWidget, QToolBar,
                             QSizePolicy)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QUrl, QSize
from PyQt6.QtGui import QFont
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings

# Import our existing strategy code
import strategy
import yfinance as yf
import numpy as np
from datetime import datetime


THEMES = {
    "dark": {
        "window_bg": "#050b18",
        "panel_bg": "#0b1222",
        "surface": "#090f1d",
        "border": "#1f2539",
        "text": "#f4f6ff",
        "muted": "#9aa3be",
        "accent": "#363944",
        "accent_hover": "#4a4d59",
        "input_bg": "#050b17",
        "chart_theme": "dark",
        "chart_bg": "#050b18",
        "chart_toolbar": "#050b18"
    },
    "light": {
        "window_bg": "#f7f8fc",
        "panel_bg": "#ffffff",
        "surface": "#eef1f7",
        "border": "#d9deeb",
        "text": "#111322",
        "muted": "#4f5b75",
        "accent": "#e4e7f2",
        "accent_hover": "#d4d8ee",
        "input_bg": "#ffffff",
        "chart_theme": "light",
        "chart_bg": "#ffffff",
        "chart_toolbar": "#f7f8fc"
    }
}


class ChartWidget(QWidget):
    """Main chart display widget with tabs for price, fundamentals, news."""
    
    def __init__(self, theme_provider):
        super().__init__()
        self.theme_provider = theme_provider
        self.current_ticker = None
        self.default_interval = "60"  # TradingView interval codes (60 = 1h)
        self.current_interval = self.default_interval
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Tabs: Price Chart | Fundamentals | News
        self.tabs = QTabWidget()
        
        # Price Chart Tab - Using TradingView Lightweight Charts
        self.chart_tab = QWidget()
        chart_layout = QVBoxLayout()
        self.chart_view = QWebEngineView()
        self.chart_view.settings().setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True
        )
        self.chart_view.setMinimumHeight(600)
        chart_layout.addWidget(self.chart_view)
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
        self.update_chart(ticker)
        self.update_fundamentals(ticker)
        self.update_news(ticker)
    
    def update_chart(self, ticker: str, interval: str | None = None):
        """Update chart using TradingView's official widget for a native experience."""
        interval = interval or self.current_interval or self.default_interval
        self.current_interval = interval
        html = self.create_tradingview_widget_html(ticker, interval)
        self.chart_view.setHtml(html)
    
    def create_tradingview_widget_html(self, ticker: str, interval: str) -> str:
        """Embed TradingView Advanced Chart widget."""
        theme = self.theme_provider()
        safe_ticker = ticker.replace(" ", "")
        background = theme["chart_bg"]
        toolbar_bg = theme["chart_toolbar"]
        chart_theme = theme["chart_theme"]
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{safe_ticker} Chart</title>
    <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
    <style>
        body {{
            margin: 0;
            padding: 0;
            background: {background};
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }}
        #tv_chart {{
            width: 100%;
            height: 640px;
        }}
    </style>
</head>
<body>
    <div id="tv_chart"></div>
    <script type="text/javascript">
        function initTradingView() {{
            if (typeof TradingView === 'undefined' || !TradingView.widget) {{
                setTimeout(initTradingView, 100);
                return;
            }}
            new TradingView.widget({{
                container_id: "tv_chart",
                autosize: true,
                symbol: "{safe_ticker}",
                interval: "{interval}",
                timezone: "Etc/UTC",
                theme: "{chart_theme}",
                style: "1",
                backgroundColor: "{background}",
                toolbar_bg: "{toolbar_bg}",
                hide_side_toolbar: false,
                hide_top_toolbar: false,
                allow_symbol_change: true,
                save_image: false,
                locale: "en",
                studies: [],
                enable_publishing: false,
            }});
        }}
        initTradingView();
    </script>
</body>
</html>
        """
        return html
    
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
        self.current_theme_name = "dark"
        self.theme_button = None
        self.init_ui()
        self.apply_theme()
    
    def init_ui(self):
        self.setWindowTitle("Trading Terminal - AI Assistant")
        self.setGeometry(80, 80, 1600, 940)
        self.setDockOptions(QMainWindow.DockOption.AllowTabbedDocks | QMainWindow.DockOption.AnimatedDocks)
        
        # Top toolbar
        self.create_toolbar()
        
        # Widgets
        self.screener = ScreenerWidget(self.on_ticker_selected)
        self.chart_widget = ChartWidget(self.get_current_theme)
        self.chatbot = ChatbotWidget(self.get_context)
        
        # Central chart
        self.setCentralWidget(self.chart_widget)
        
        # Watchlist dock
        self.watchlist_dock = QDockWidget("Watchlist", self)
        self.watchlist_dock.setWidget(self.screener)
        self.watchlist_dock.setObjectName("WatchlistDock")
        self.watchlist_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        dock_features = (QDockWidget.DockWidgetFeature.DockWidgetMovable |
                         QDockWidget.DockWidgetFeature.DockWidgetFloatable)
        self.watchlist_dock.setFeatures(dock_features)
        self.watchlist_dock.setMinimumWidth(260)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.watchlist_dock)
        
        # Assistant dock
        self.chatbot_dock = QDockWidget("Assistant", self)
        self.chatbot_dock.setWidget(self.chatbot)
        self.chatbot_dock.setObjectName("AssistantDock")
        self.chatbot_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.chatbot_dock.setFeatures(dock_features)
        self.chatbot_dock.setMinimumWidth(320)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.chatbot_dock)
        
        # Load first ticker by default
        if strategy.TICKERS:
            self.on_ticker_selected(strategy.TICKERS[0])
    
    def create_toolbar(self):
        toolbar = QToolBar("Main")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setIconSize(QSize(16, 16))
        toolbar.setObjectName("TopToolbar")
        
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)
        
        self.theme_button = QPushButton("☀ Light Mode")
        self.theme_button.clicked.connect(self.toggle_theme)
        toolbar.addWidget(self.theme_button)
        
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)
        self.toolbar = toolbar
    
    def get_current_theme(self):
        return THEMES[self.current_theme_name]
    
    def apply_theme(self):
        theme = self.get_current_theme()
        stylesheet = f"""
        QMainWindow {{
            background-color: {theme['window_bg']};
            color: {theme['text']};
            font-family: 'Inter', 'SF Pro Display', 'Segoe UI', sans-serif;
        }}
        QWidget {{
            background-color: {theme['panel_bg']};
            color: {theme['text']};
        }}
        QDockWidget {{
            background-color: {theme['panel_bg']};
            border: 1px solid {theme['border']};
        }}
        QDockWidget::title {{
            background-color: {theme['surface']};
            color: {theme['muted']};
            padding: 6px 10px;
            border-bottom: 1px solid {theme['border']};
        }}
        QListWidget {{
            background-color: {theme['surface']};
            border: 1px solid {theme['border']};
            padding: 6px;
        }}
        QListWidget::item {{
            padding: 6px;
        }}
        QListWidget::item:selected {{
            background-color: {theme['accent']};
            color: {theme['text']};
        }}
        QLineEdit {{
            background-color: {theme['input_bg']};
            border: 1px solid {theme['border']};
            color: {theme['text']};
            padding: 8px 10px;
            border-radius: 8px;
        }}
        QLineEdit::placeholder {{
            color: {theme['muted']};
        }}
        QPushButton {{
            background-color: {theme['accent']};
            color: {theme['text']};
            border: none;
            border-radius: 8px;
            padding: 10px 16px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            background-color: {theme['accent_hover']};
        }}
        QTabWidget::pane {{
            background-color: {theme['surface']};
            border: 1px solid {theme['border']};
            border-radius: 10px;
            margin-top: 8px;
        }}
        QTabBar::tab {{
            background-color: transparent;
            color: {theme['muted']};
            padding: 10px 18px;
            border: none;
            font-weight: 600;
        }}
        QTabBar::tab:selected {{
            color: {theme['text']};
            border-bottom: 3px solid {theme['text']};
            margin-bottom: -3px;
        }}
        QTextEdit {{
            background-color: {theme['surface']};
            border: 1px solid {theme['border']};
            color: {theme['text']};
            border-radius: 10px;
            padding: 12px;
        }}
        QTableWidget {{
            background-color: {theme['surface']};
            border: 1px solid {theme['border']};
            color: {theme['text']};
            gridline-color: {theme['border']};
            border-radius: 10px;
        }}
        QHeaderView::section {{
            background-color: {theme['panel_bg']};
            color: {theme['muted']};
            padding: 6px;
            border: none;
        }}
        QToolBar {{
            background: {theme['window_bg']};
            border: none;
        }}
        QLabel {{
            color: {theme['muted']};
            font-weight: 600;
        }}
        """
        self.setStyleSheet(stylesheet)
        if self.theme_button:
            if self.current_theme_name == "dark":
                self.theme_button.setText("☀ Light Mode")
            else:
                self.theme_button.setText("🌙 Dark Mode")
        if self.current_ticker:
            self.chart_widget.load_ticker(self.current_ticker)
    
    def toggle_theme(self):
        self.current_theme_name = "light" if self.current_theme_name == "dark" else "dark"
        self.apply_theme()
    
    def on_ticker_selected(self, ticker: str):
        """Handle ticker selection."""
        self.current_ticker = ticker
        self.chart_widget.load_ticker(ticker)
        self.chatbot.add_bot_message(f"📊 Loaded {ticker}. Ask me about its signals or strategy!")
    
    def get_context(self) -> dict:
        """Get current context for chatbot - enhanced with more details."""
        return {
            "ticker": self.current_ticker or "N/A",
            "timeframe": getattr(self.chart_widget, 'current_interval', self.chart_widget.default_interval),
            "timestamp": datetime.now().isoformat(),
            "chart_type": "tradingview_widget",
            "view": "main_chart",
            "theme": self.current_theme_name
        }


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Modern look
    
    window = TradingTerminal()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

