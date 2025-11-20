"""
Chart widget for the Trading Terminal.
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QSizePolicy
from PyQt6.QtCore import QSize
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings
import pandas as pd

BASE_SPACING = 12

class ChartWidget(QWidget):
    """Standalone chart widget (TradingView embed)."""
    
    def __init__(self, theme_provider):
        super().__init__()
        self.theme_provider = theme_provider
        self.current_ticker = None
        self.default_interval = "60"  # TradingView interval codes (60 = 1h)
        self.current_interval = self.default_interval
        self.last_chart_signature: tuple[str, str, str] | None = None
        self.signals = None
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(BASE_SPACING)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.chart_view = QWebEngineView()
        self.chart_view.settings().setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True
        )
        self.chart_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.chart_view.setMinimumSize(QSize(420, 320))
        layout.addWidget(self.chart_view)
    
    def load_ticker(self, ticker: str):
        """Load and display ticker data."""
        self.current_ticker = ticker
        self.update_chart(ticker)

    def set_signals(self, signals):
        self.signals = signals
        self.update_chart(self.current_ticker)
    
    def update_chart(self, ticker: str, interval: str | None = None):
        """Update chart using TradingView's official widget for a native experience."""
        interval = interval or self.current_interval or self.default_interval
        self.current_interval = interval
        theme = self.theme_provider()
        signature = (ticker.upper(), interval, theme["chart_theme"])
        if signature == self.last_chart_signature and self.signals is None:
            return
        self.last_chart_signature = signature
        html = self.create_tradingview_widget_html(ticker, interval, self.signals)
        self.chart_view.setHtml(html)
    
    def refresh_theme(self):
        self.last_chart_signature = None
        if self.current_ticker:
            self.update_chart(self.current_ticker, self.current_interval)
    
    def create_tradingview_widget_html(self, ticker: str, interval: str, signals: pd.DataFrame = None) -> str:
        """Embed TradingView Advanced Chart widget."""
        theme = self.theme_provider()
        safe_ticker = ticker.replace(" ", "")
        background = theme["chart_bg"]
        toolbar_bg = theme["chart_toolbar"]
        chart_theme = theme["chart_theme"]
        
        markers_data = "[]"
        if signals is not None and not signals.empty:
            true_breakouts = signals[signals["signal"]]
            false_breakouts = signals[signals["false_breakout"]]
            
            markers = []
            for _, row in true_breakouts.iterrows():
                markers.append({
                    "time": row.name.timestamp(),
                    "position": "aboveBar",
                    "color": "#4ade80",
                    "shape": "arrowUp",
                    "text": "True Breakout"
                })
            for _, row in false_breakouts.iterrows():
                markers.append({
                    "time": row.name.timestamp(),
                    "position": "aboveBar",
                    "color": "#f43f5e",
                    "shape": "arrowDown",
                    "text": "False Breakout"
                })
            markers_data = pd.io.json.dumps(markers)

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{safe_ticker} Chart</title>
    <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
    <style>
        html, body {{
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            background: {background};
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }}
        #tv_chart {{
            width: 100%;
            height: 100%;
            min-height: 620px;
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
            var widget = new TradingView.widget({{
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
            
            widget.onChartReady(function() {{
                var markers = {markers_data};
                if (markers.length > 0) {{
                    widget.chart().getSeries().setMarkers(markers);
                }}
            }});
        }}
        initTradingView();
    </script>
</body>
</html>
        """
        return html
