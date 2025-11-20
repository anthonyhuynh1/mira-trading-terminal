"""
Trading Terminal Application - Cursor-like Interface
Left: Stock Screener | Main: Charts/Fundamentals/News | Right: Context-Aware Chatbot
"""

import sys
import warnings
from collections import defaultdict
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
warnings.filterwarnings("ignore")

import os

os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu")

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QDockWidget,
                             QSizePolicy, QFrame, QToolButton, QMenu, QToolBar,
                             QTabWidget)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction, QIcon, QCursor
from typing import Callable, Dict
import pandas as pd
import numpy as np

# Import our existing strategy code
import strategy

# Import app components
from components.workspace_dock import WorkspaceDock
from data.ticker_data_provider import TickerDataProvider
from threads import SnapshotWorker
from utils import (
    soften_color,
    mix_colors,
    ticker_hash_color,
)
from widgets.chart_widget import ChartWidget
from widgets.chatbot_widget import ChatbotWidget
from widgets.fundamentals_widget import FundamentalsWidget
from widgets.market_clock_widget import MarketClockWidget
from widgets.news_widget import NewsWidget
from widgets.quote_widget import QuoteWidget
from widgets.screener_widget import ScreenerWidget


BASE_RADIUS = 12
BASE_SPACING = 12
TOUCH_TARGET = 44

THEMES = {
    "dark": {
        "window_bg": "#000000",
        "panel_bg": "#000000",
        "surface": "#000000",
        "surface_alt": "#000000",
        "border": "#ffffff",
        "text": "#ffffff",
        "muted": "#ffffff",
        "accent": "#ffffff",
        "accent_hover": "#000000",
        "button_text": "#000000",
        "button_hover_text": "#ffffff",
        "input_bg": "#000000",
        "tab_bg": "#1e1e1e",
        "tab_text": "#f5f5f5",
        "chart_theme": "dark",
        "chart_bg": "#000000",
        "chart_toolbar": "#000000",
        "divider": "#ffffff"
    },
    "light": {
        "window_bg": "#ffffff",
        "panel_bg": "#ffffff",
        "surface": "#ffffff",
        "surface_alt": "#ffffff",
        "border": "#000000",
        "text": "#000000",
        "muted": "#000000",
        "accent": "#000000",
        "accent_hover": "#ffffff",
        "button_text": "#ffffff",
        "button_hover_text": "#000000",
        "input_bg": "#ffffff",
        "tab_bg": "#f0f0f0",
        "tab_text": "#000000",
        "chart_theme": "light",
        "chart_bg": "#ffffff",
        "chart_toolbar": "#ffffff",
        "divider": "#000000"
    }
}

BRAND_COLORS = {
    "NVDA": "#76b900",
    "AAPL": "#a2aaad",
    "TSLA": "#e82127",
    "MSFT": "#00a4ef",
    "AMZN": "#ff9900",
    "META": "#0a66ff",
    "GOOG": "#1a73e8",
    "NFLX": "#e50914",
    "SPY": "#1159a4",
    "QQQ": "#5c6bc0",
    "AMD": "#ff6f00",
}



class TradingTerminal(QMainWindow):
    """Main application window - Cursor-like interface."""
    
    def __init__(self):
        super().__init__()
        self.current_ticker = None
        self.current_theme_name = "dark"
        self.theme_button = None
        self.refresh_button = None
        self.status_badge = None
        self.widget_button = None
        self.quote_widget = None
        self.chart_widget = None
        self.chatbot = None
        self.screener = None
        self.fundamentals_widget = None
        self.news_widget = None
        self.stowed_actions: dict[str, QAction] = {}
        self.widget_link_groups: dict[str, int | None] = {}
        self.link_groups: defaultdict[int, set[str]] = defaultdict(set)
        self.link_group_tickers: dict[int, str] = {}
        self.snapshot_worker: SnapshotWorker | None = None
        self.snapshot_workers: list[SnapshotWorker] = []
        self.widget_factories: Dict[str, Callable[[], QWidget]] = {}
        self.dock_widgets: Dict[str, WorkspaceDock] = {}
        self.dock_by_id: Dict[str, WorkspaceDock] = {}
        self.pending_widget_target_dock: WorkspaceDock | None = None
        self.data_provider = TickerDataProvider()
        self.init_ui()
        self.apply_theme()
    
    def init_ui(self):
        self.setWindowTitle("Mira - Trading Terminal")
        self.resize(1600, 940)
        
        self.setDockNestingEnabled(True)
        self.setDockOptions(
            QMainWindow.DockOption.AllowNestedDocks |
            QMainWindow.DockOption.AnimatedDocks |
            QMainWindow.DockOption.GroupedDragging
        )
        self.setTabPosition(Qt.DockWidgetArea.AllDockWidgetAreas, QTabWidget.TabPosition.North)
        
        central = QWidget()
        central.setObjectName("Workspace")
        self.setCentralWidget(central)
        
        header = self.create_header()
        self.setMenuWidget(header)
        self.setup_stow_bar()

        self.widget_factories = {
            "Quotes": lambda: QuoteWidget(self.handle_interval_change),
            "Chart": lambda: ChartWidget(self.get_current_theme),
            "Screener": lambda: ScreenerWidget(self.on_ticker_selected, self.run_and_display_analysis),
            "Fundamentals": lambda: FundamentalsWidget(self.data_provider),
            "News": lambda: NewsWidget(self.data_provider),
            "Copilot": lambda: ChatbotWidget(self.get_context),
        }

        self.create_widget_menu()
        self.create_default_layout()

        if strategy.TICKERS:
            self.on_ticker_selected(strategy.TICKERS[0])

    def create_widget_menu(self):
        """Create add-widget menu for re-spawning docks."""
        self.widget_menu = QMenu(self)
        for key in self.widget_factories.keys():
            action = self.widget_menu.addAction(key)
            action.triggered.connect(lambda checked=False, n=key: self.handle_widget_menu_selection(n))
        if self.widget_button:
            self.widget_button.setMenu(self.widget_menu)
            self.widget_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
    
    def create_default_layout(self):
        # Create primary docks
        screener = self.ensure_widget("Screener", Qt.DockWidgetArea.LeftDockWidgetArea)
        quotes = self.ensure_widget("Quotes", Qt.DockWidgetArea.TopDockWidgetArea)
        chart = self.ensure_widget("Chart", Qt.DockWidgetArea.RightDockWidgetArea)
        fundamentals = self.ensure_widget("Fundamentals", Qt.DockWidgetArea.BottomDockWidgetArea)
        
        # Arrange primary layout
        self.splitDockWidget(screener, chart, Qt.Orientation.Horizontal)
        self.splitDockWidget(quotes, chart, Qt.Orientation.Vertical)
        self.splitDockWidget(chart, fundamentals, Qt.Orientation.Vertical)

        # Set initial sizes to provide a more balanced layout
        self.resizeDocks([screener, quotes, chart, fundamentals], [300, 150, 800, 300], Qt.Orientation.Horizontal)
        self.resizeDocks([quotes, chart], [150, 700], Qt.Orientation.Vertical)
        
        # Add secondary widgets as tabs
        if fundamentals:
            self.add_widget_tab(fundamentals, "News")
        if chart:
            self.add_widget_tab(chart, "Copilot")

    def show_widget_menu_at(self, dock: WorkspaceDock | None, anchor: QWidget | None):
        if not hasattr(self, "widget_menu") or not self.widget_menu:
            return
        self.pending_widget_target_dock = dock
        if anchor:
            pos = anchor.mapToGlobal(anchor.rect().bottomRight())
        else:
            pos = QCursor.pos()
        self.widget_menu.popup(pos)

    def handle_widget_menu_selection(self, key: str):
        target = self.pending_widget_target_dock
        self.pending_widget_target_dock = None
        if target and isinstance(target, WorkspaceDock):
            self.add_widget_tab(target, key)
        else:
            self.ensure_widget(key)

    def add_widget_tab(self, target_dock: WorkspaceDock, key: str):
        if not target_dock:
            return
        # Find if widget already exists in another dock
        existing_dock = self.find_dock_for_widget(key)
        widget = None
        if existing_dock:
            if existing_dock is target_dock:
                target_dock.focus_tab(key)
                return
            # Move widget from existing dock to target dock
            widget = existing_dock.take_tab(key)
            if existing_dock.is_empty():
                existing_dock.close()
        else:
            # Create new widget instance
            factory = self.widget_factories.get(key)
            if not factory:
                return
            widget = factory()
            self.register_widget_instance(key, widget)
        target_dock.add_tab(key, widget, key)
        # Update the mapping to point to the new dock
        self.dock_widgets[key] = target_dock
        target_dock.set_link_group_display(self.widget_link_groups.get(key))
        if hasattr(widget, "load_ticker") and self.current_ticker:
            widget.load_ticker(self.current_ticker)
    
    def ensure_widget(self, key: str, area: Qt.DockWidgetArea | None = None):
        """Make sure a widget dock exists and is visible."""
        # Find the dock that actually contains this widget
        dock = self.find_dock_for_widget(key)
        if dock:
            dock.show()
            dock.raise_()
            dock.focus_tab(key)
            return dock
        factory = self.widget_factories.get(key)
        if not factory:
            return None
        widget = factory()
        dock_id = f"Dock_{key}_{len(self.dock_by_id) + 1}"
        dock = WorkspaceDock(
            dock_id,
            key,
            widget,
            self,
            link_callback=self.set_widget_link,
            widget_menu_callback=self.show_widget_menu_at
        )
        dock.closed.connect(self.on_dock_closed)
        dock.collapsed_changed.connect(self.on_dock_collapsed)
        dock.tab_removed.connect(lambda removed_key, d=dock: self.on_dock_tab_removed(d, removed_key))
        dock.active_tab_changed.connect(self.on_dock_active_tab_changed)
        dock.setMinimumSize(QSize(150, 120))
        dock.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.addDockWidget(area or Qt.DockWidgetArea.LeftDockWidgetArea, dock)
        self.dock_by_id[dock.dock_id] = dock
        self.dock_widgets[key] = dock
        self.register_widget_instance(key, widget)
        dock.set_link_group_display(self.widget_link_groups.get(key))
        if hasattr(widget, "load_ticker") and self.current_ticker:
            widget.load_ticker(self.current_ticker)
        return dock
    
    def on_dock_closed(self, dock: WorkspaceDock):
        for key in dock.list_tab_keys():
            self._untrack_widget(key)
        self.remove_stowed_tab(dock.dock_id)
        self.dock_by_id.pop(dock.dock_id, None)

    def on_dock_tab_removed(self, dock: WorkspaceDock, key: str):
        self._untrack_widget(key)
    
    def on_dock_active_tab_changed(self, key: str):
        # Update the dock_widgets mapping to reflect the active tab's dock
        dock = self.find_dock_for_widget(key)
        if dock:
            self.dock_widgets[key] = dock
            dock.set_link_group_display(self.widget_link_groups.get(key))

    def register_widget_instance(self, key: str, widget: QWidget):
        if key == "Chart":
            self.chart_widget = widget
        elif key == "Quotes":
            self.quote_widget = widget
        elif key == "Fundamentals":
            self.fundamentals_widget = widget
        elif key == "News":
            self.news_widget = widget
        elif key == "Copilot":
            self.chatbot = widget
        elif key == "Screener":
            self.screener = widget
        self.widget_link_groups.setdefault(key, None)

    def unregister_widget_instance(self, key: str):
        if key == "Chart":
            self.chart_widget = None
        elif key == "Quotes":
            self.quote_widget = None
        elif key == "Fundamentals":
            self.fundamentals_widget = None
        elif key == "News":
            self.news_widget = None
        elif key == "Copilot":
            self.chatbot = None
        elif key == "Screener":
            self.screener = None

    def _untrack_widget(self, key: str):
        # Remove from dock_widgets mapping
        self.dock_widgets.pop(key, None)
        group = self.widget_link_groups.pop(key, None)
        if group and key in self.link_groups[group]:
            self.link_groups[group].remove(key)
        self.unregister_widget_instance(key)
    
    def find_dock_for_widget(self, key: str) -> WorkspaceDock | None:
        """Find which dock currently hosts a widget key."""
        for dock in self.dock_by_id.values():
            if key in dock.tab_widgets:
                return dock
        return None
    
    def get_widget_instance(self, key: str) -> QWidget | None:
        """Get the actual widget instance for a key, regardless of which dock it's in."""
        dock = self.find_dock_for_widget(key)
        if dock:
            return dock.tab_widgets.get(key)
        return None

    def set_widget_link(self, key: str, group: int | None):
        prev = self.widget_link_groups.get(key)
        if prev == group:
            return
        if prev and key in self.link_groups[prev]:
            self.link_groups[prev].remove(key)
        self.widget_link_groups[key] = group
        # Find the actual dock hosting this widget
        dock = self.find_dock_for_widget(key)
        if dock and dock.current_tab_key() == key:
            dock.set_link_group_display(group)
        if group:
            self.link_groups[group].add(key)
            if self.current_ticker:
                ticker = self.current_ticker
            else:
                ticker = self.link_group_tickers.get(group)
            if ticker:
                self.link_group_tickers[group] = ticker
                self.load_widget_ticker(key, ticker, propagate=False)
        else:
            # revert to main ticker feed
            if key in ("Chart", "Fundamentals", "News"):
                self.load_widget_ticker(key, self.current_ticker, propagate=False)

    def on_dock_collapsed(self, dock: WorkspaceDock, collapsed: bool):
        if not dock:
            return
        if collapsed:
            self.add_stowed_tab(dock)
        else:
            self.remove_stowed_tab(dock.dock_id)

    def add_stowed_tab(self, dock: WorkspaceDock):
        dock_id = dock.dock_id
        if dock_id in self.stowed_actions:
            return
        action = self.stow_bar.addAction(dock.windowTitle())
        action.triggered.connect(lambda checked=False, d_id=dock_id: self.restore_stowed(d_id))
        self.stowed_actions[dock_id] = action
        self.stow_bar.show()

    def remove_stowed_tab(self, dock_id: str):
        action = self.stowed_actions.pop(dock_id, None)
        if action:
            self.stow_bar.removeAction(action)
        if not self.stowed_actions and hasattr(self, "stow_bar"):
            self.stow_bar.hide()

    def restore_stowed(self, dock_id: str):
        dock = self.dock_by_id.get(dock_id)
        if not dock:
            return
        if dock.collapsed:
            dock.toggle_collapsed()

        self.remove_stowed_tab(dock_id)

    def load_widget_ticker(self, key: str, ticker: str, propagate: bool = False):
        loaded = False
        if key == "Chart" and self.chart_widget:
            self.chart_widget.load_ticker(ticker)
            loaded = True
        elif key == "Fundamentals" and self.fundamentals_widget:
            self.fundamentals_widget.load_ticker(ticker)
            loaded = True
        elif key == "News" and self.news_widget:
            self.news_widget.load_ticker(ticker)
            loaded = True
        elif key == "Quotes" and self.quote_widget:
            self.quote_widget.show_loading(ticker)
            self.update_brand_accent(ticker)
            self.request_snapshot(ticker)
            loaded = True
        if propagate:
            self.broadcast_link_update(key, ticker)

    def broadcast_link_update(self, source_key: str, ticker: str):
        group = self.widget_link_groups.get(source_key)
        if not group:
            return
        self.link_group_tickers[group] = ticker
        for key in self.link_groups[group]:
            if key == source_key:
                continue
            self.load_widget_ticker(key, ticker, propagate=False)

    def handle_interval_change(self, interval: str):
        """Update chart interval from hero buttons."""
        if not self.current_ticker:
            return
        self.chart_widget.update_chart(self.current_ticker, interval)
        if self.quote_widget:
            self.quote_widget.set_active_interval(interval)

    def refresh_snapshot(self):
        """Manually refresh ticker snapshot data."""
        self.request_snapshot()

    def request_snapshot(self, ticker: str | None = None):
        """Spawn/refresh background worker for ticker quotes."""
        target = (ticker or self.current_ticker or "").strip()
        if not target:
            return
        symbol = target.upper()
        worker = SnapshotWorker(lambda: self.fetch_ticker_snapshot(symbol))
        worker.result_ready.connect(lambda snapshot, w=worker, expected=symbol: self.on_snapshot_ready(snapshot, w, expected))
        worker.finished.connect(lambda w=worker: self.cleanup_worker(w))
        self.snapshot_worker = worker
        self.snapshot_workers.append(worker)
        worker.start()

    def on_snapshot_ready(self, snapshot: dict, worker: SnapshotWorker | None = None,
                          expected_symbol: str | None = None):
        current_symbol = (self.current_ticker or "").upper()
        if expected_symbol and expected_symbol != current_symbol:
            return
        target_symbol = expected_symbol or current_symbol
        snapshot_symbol = snapshot.get("symbol", "").upper()
        if target_symbol and snapshot_symbol and snapshot_symbol != target_symbol:
            return
        self.update_snapshot_ui(snapshot)
        if worker is self.snapshot_worker:
            self.snapshot_worker = None

    def cleanup_worker(self, worker: SnapshotWorker):
        if worker in self.snapshot_workers:
            self.snapshot_workers.remove(worker)
        worker.deleteLater()

    def fetch_ticker_snapshot(self, ticker: str) -> dict:
        """Lightweight ticker overview used by the hero section."""
        return self.data_provider.fetch_snapshot_payload(ticker)

    def update_snapshot_ui(self, snapshot: dict):
        if self.quote_widget:
            self.quote_widget.update_snapshot(snapshot)

    def update_brand_accent(self, ticker: str):
        if not self.quote_widget:
            return
        ticker = (ticker or "").strip().upper()
        accent = None
        if ticker:
            brand_color = BRAND_COLORS.get(ticker) or ticker_hash_color(ticker)
            if self.current_theme_name == "dark":
                pastel = soften_color(brand_color, 0.85)
                accent = mix_colors("#101013", pastel, 0.55)
            else:
                pastel = soften_color(brand_color, 0.45)
                accent = mix_colors("#ffffff", pastel, 0.25)
        self.quote_widget.apply_brand_color(accent)
    
    def run_and_display_analysis(self, ticker: str):
        """Run strategy analysis and display in chatbot."""
        if not self.chatbot:
            return
        self.chatbot.add_bot_message(f"Analyzing {ticker} for consolidation breakout...")
        # This should be async in a real app, but for prototype, we do it sync
        analysis_text, sigs = self.get_signal_analysis_text(ticker)
        self.chatbot.add_bot_message(analysis_text)
        if self.chart_widget:
            self.chart_widget.set_signals(sigs)

    def get_signal_analysis_text(self, ticker: str) -> tuple[str, pd.DataFrame]:
        """Fetches data and returns a formatted string of the current signal analysis."""
        try:
            df = strategy.fetch_hourly_data(ticker, period_days=30)
            if df.empty:
                return f"Could not retrieve data for {ticker}.", None
            
            sigs = strategy.breakout_volume_signals(df)
            last_sig = sigs.iloc[-1]
            current_price = df["Close"].iloc[-1]
            cons_high = float(last_sig["cons_high_prev"]) if not np.isnan(last_sig["cons_high_prev"]) else None
            cons_low = float(last_sig["cons_low_prev"]) if not np.isnan(last_sig["cons_low_prev"]) else None
            
            if bool(last_sig["false_breakout"]):
                text = f"""**{ticker} - FALSE BREAKOUT Signal**

Current Price: ${current_price:.2f}
Consolidation Range: ${cons_low:.2f} - ${cons_high:.2f}

**Analysis:**
- Price broke above consolidation high but on LOW volume (< 25th percentile)
- This suggests liquidity was taken but lacks follow-through
- **Potential short opportunity** if price rejects and returns below ${cons_high:.2f}

**Risk Management:**
- Stop: Above recent high
- Target: Back to consolidation low ${cons_low:.2f}"""
                return text, sigs
            
            elif bool(last_sig["signal"]):
                text = f"""**{ticker} - TRUE BREAKOUT Signal**

Current Price: ${current_price:.2f}
Consolidation Range: ${cons_low:.2f} - ${cons_high:.2f}

**Analysis:**
- Price broke above consolidation high with HIGH volume (>= 75th percentile)
- Strong buying pressure indicates continuation
- **Long entry opportunity**

**Trade Setup:**
- Entry: Current price or pullback to ${cons_high:.2f}
- Stop: ${cons_low:.2f} (consolidation low)
- Target: ${current_price + (current_price - cons_low) * strategy.RR_TARGET:.2f} (2R target)
- Risk/Reward: 1:{strategy.RR_TARGET}"""
                return text, sigs
            
            elif bool(last_sig["cons_ok"]):
                breakout_level = float(last_sig["breakout_level"])
                dist_pct = ((breakout_level - current_price) / current_price) * 100
                text = f"""**{ticker} - CONSOLIDATION SETUP**

Current Price: ${current_price:.2f}
Consolidation Range: ${cons_low:.2f} - ${cons_high:.2f}
Breakout Level: ${breakout_level:.2f}
Distance to Breakout: {dist_pct:.2f}%

**Status:** Waiting for breakout
**Action:** Monitor for volume confirmation when price approaches ${breakout_level:.2f}"""
                return text, sigs
            else:
                text = f"{ticker} is not showing a setup currently. No consolidation detected in the last {strategy.LOOKBACK_HOURS} hours."
                return text, sigs
        except Exception as e:
            return f"Error analyzing {ticker}: {str(e)}", None

    def _build_header_button(self, glyph: str, tooltip: str) -> QToolButton:
        btn = QToolButton()
        btn.setObjectName("UtilityIconButton")
        btn.setText(glyph)
        btn.setToolTip(tooltip)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setAutoRaise(False)
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn.setCheckable(False)
        btn.setIcon(QIcon())
        btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        btn.setFixedSize(QSize(36, 36))
        return btn
    
    def create_header(self):
        header = QFrame()
        header.setObjectName("Header")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(24, 16, 24, 16)
        
        title = QLabel("Mira")
        title.setObjectName("HeaderTitle")
        subtitle = QLabel("Adaptive Trading Workspace")
        subtitle.setObjectName("HeaderSubtitle")
        title_block = QVBoxLayout()
        title_block.setSpacing(2)
        title_block.addWidget(title)
        title_block.addWidget(subtitle)
        layout.addLayout(title_block)

        layout.addSpacing(24)

        self.market_clock = MarketClockWidget()
        self.market_clock.setFixedWidth(220)
        layout.addWidget(self.market_clock)

        layout.addStretch()
        
        controls_container = QWidget()
        controls_container.setObjectName("HeaderControls")
        controls_layout = QHBoxLayout(controls_container)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(4)

        self.refresh_button = self._build_header_button("↻", "Refresh market data")
        self.refresh_button.clicked.connect(self.refresh_snapshot)
        controls_layout.addWidget(self.refresh_button)

        self.widget_button = self._build_header_button("+", "Add widget")
        self.widget_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.widget_button.pressed.connect(lambda: setattr(self, 'pending_widget_target_dock', None))
        controls_layout.addWidget(self.widget_button)
        
        self.theme_button = self._build_header_button("", "Toggle theme")
        self.theme_button.clicked.connect(self.toggle_theme)
        controls_layout.addWidget(self.theme_button)

        controls_container.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout.addWidget(controls_container)
        return header

    def setup_stow_bar(self):
        self.stow_bar = QToolBar("Stowed")
        self.stow_bar.setObjectName("StowBar")
        self.stow_bar.setMovable(False)
        self.stow_bar.setFloatable(False)
        self.stow_bar.setAllowedAreas(Qt.ToolBarArea.BottomToolBarArea)
        self.stow_bar.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)
        self.addToolBar(Qt.ToolBarArea.BottomToolBarArea, self.stow_bar)
        self.stow_bar.hide()

    def get_current_theme(self):
        return THEMES[self.current_theme_name]
    
    def apply_theme(self):
        theme = self.get_current_theme()
        radius = BASE_RADIUS
        spacing = BASE_SPACING
        touch = TOUCH_TARGET
        quote_gradient = theme['surface']
        card_radius = 0
        stylesheet = f"""
        QMainWindow {{
            background-color: {theme['window_bg']};
            color: {theme['text']};
            font-family: 'Inter', 'SF Pro Display', 'Segoe UI', sans-serif;
        }}
        QWidget#Workspace {{
            background-color: {theme['window_bg']};
        }}
        QWidget {{
            background-color: {theme['panel_bg']};
            color: {theme['text']};
        }}
        QLabel {{
            color: {theme['text']};
            background-color: transparent;
        }}
        QLabel#SectionHint {{
            color: {theme['muted']};
            font-size: 13px;
            font-weight: 500;
        }}
        QFrame#Header {{
            background-color: {theme['surface']};
            border: 1px solid {theme['divider']};
            border-radius: {card_radius}px;
        }}
        QLabel#HeaderTitle {{
            color: {theme['text']};
            font-size: 20px;
            font-weight: 700;
        }}
        QLabel#HeaderSubtitle {{
            color: {theme['muted']};
            font-size: 13px;
        }}
        QLabel#QuoteTicker {{
            color: {theme['text']};
            font-size: 28px;
            font-weight: 700;
        }}
        QLabel#QuoteSubtitle {{
            color: {theme['muted']};
            font-size: 14px;
        }}
        QFrame#QuoteCard {{
            background: {quote_gradient};
            border: 1px solid {theme['divider']};
            border-radius: {card_radius}px;
        }}
        QFrame#ClockCard {{
            border: 1px solid {theme['divider']};
            border-radius: {radius}px;
            background-color: {theme['panel_bg']};
        }}
        QLabel#SectionTitle {{
            color: {theme['text']};
            font-size: 16px;
            font-weight: 600;
        }}
        QLabel#ClockTime {{
            font-size: 14px;
            font-weight: 600;
        }}
        QLabel#ClockStatus {{
            font-size: 11px;
            color: {theme['muted']};
        }}
        QComboBox#ClockSelector {{
            background-color: {theme['panel_bg']};
            color: {theme['text']};
            border: 1px solid {theme['divider']};
            padding: 4px 8px;
        }}
        QComboBox {{
            background-color: {theme['panel_bg']};
            border: 1px solid {theme['divider']};
            color: {theme['text']};
            padding: 4px 8px;
        }}
        QComboBox::drop-down {{
            border: none;
        }}
        QLabel#StatusBadge {{
            background-color: {theme['panel_bg']};
            color: {theme['text']};
            border-radius: 0px;
            padding: 6px 14px;
            font-size: 12px;
            letter-spacing: 0.08em;
            border: 1px solid {theme['divider']};
        }}
        QListWidget {{
            background-color: {theme['surface']};
            border: 1px solid {theme['divider']};
            padding: {spacing - 4}px;
            border-radius: {card_radius}px;
        }}
        QListWidget::item {{
            padding: 6px;
            margin-bottom: 2px;
            border-radius: 0;
            background-color: transparent;
            color: {theme['text']};
        }}
        QListWidget::item:selected {{
            background-color: {theme['tab_bg']};
            color: {theme['tab_text']};
            border: 1px solid {theme['tab_text']};
        }}
        QFrame#StatPill {{
            background-color: {theme['surface']};
            border: 1px solid {theme['divider']};
            border-radius: {card_radius}px;
        }}
        QLabel#StatLabel {{
            color: {theme['muted']};
            font-size: 11px;
            letter-spacing: 0.12em;
        }}
        QLabel#StatValue {{
            color: {theme['text']};
            font-size: 20px;
            font-weight: 700;
        }}
        QLabel#StatSubtext {{
            color: {theme['muted']};
            font-size: 12px;
        }}
        QFrame#StatPill[trend="positive"] QLabel#StatValue {{
            color: #4ade80;
        }}
        QFrame#StatPill[trend="negative"] QLabel#StatValue {{
            color: #f43f5e;
        }}
        QDockWidget {{
            background-color: {theme['panel_bg']};
            border: 1px solid {theme['divider']};
            border-radius: {card_radius}px;
        }}
        QWidget#DockTitleBar {{
            background-color: {theme['tab_bg']};
            border-bottom: 1px solid {theme['divider']};
        }}
        QWidget#DockTitleBar[tabbed="true"] {{
            border-bottom: none;
        }}
        QLabel#DockTitleLabel {{
            color: {theme['tab_text']};
            font-weight: 600;
            letter-spacing: 0.05em;
        }}
        QTabBar::tab {{
            background: {theme['tab_bg']};
            color: {theme['tab_text']};
            padding: 6px 14px;
            margin-right: 4px;
            border: 1px solid {theme['divider']};
            border-bottom: none;
            border-top-left-radius: {radius}px;
            border-top-right-radius: {radius}px;
        }}
        QTabBar::tab:selected {{
            background-color: {theme['panel_bg']};
            color: {theme['text']};
        }}
        QTabBar::tab:!selected {{
            opacity: 0.7;
        }}
        QTabBar::tab:hover {{
            color: {theme['accent']};
        }}
        QTabWidget::pane {{
            border: 1px solid {theme['divider']};
            top: -1px;
        }}
        QDockWidget::title {{
            padding: 0;
            margin: 0;
            color: {theme['tab_text']};
            background-color: {theme['tab_bg']};
        }}
        QFrame#DockBody {{
            border: 1px solid {theme['divider']};
            border-radius: {card_radius}px;
            background-color: {theme['panel_bg']};
        }}
        QToolButton#DockButton, QToolButton#DockIconButton {{
            background-color: transparent;
            border: 1px solid {theme['divider']};
            border-radius: 4px;
            color: {theme['tab_text']};
            padding: 0;
        }}
        QToolButton#DockButton:hover, QToolButton#DockIconButton:hover {{
            background-color: {theme['accent']};
            color: {theme['button_text']};
        }}
        QTabBar#DockTabBar {{
            background: transparent;
        }}
        QTabBar#DockTabBar::tab {{
            background-color: transparent;
            color: {theme['muted']};
            padding: 2px 10px;
            margin-left: 8px;
            border: 1px solid {theme['divider']};
            border-radius: 10px;
        }}
        QTabBar#DockTabBar::tab:selected {{
            color: {theme['text']};
            border-color: {theme['accent']};
        }}
        QTabBar#DockTabBar::tab:hover {{
            color: {theme['accent']};
        }}
        QToolBar#StowBar {{
            background-color: {theme['panel_bg']};
            border-top: 1px solid {theme['divider']};
            spacing: 6px;
        }}
        QToolBar#StowBar QToolButton {{
            background-color: transparent;
            border: 1px dashed {theme['divider']};
            color: {theme['muted']};
            padding: 6px 12px;
            border-radius: {card_radius}px;
        }}
        QToolBar#StowBar QToolButton:hover {{
            background-color: {theme['accent']};
            color: {theme['text']};
        }}
        QLineEdit {{
            background-color: {theme['input_bg']};
            border: 1px solid {theme['divider']};
            color: {theme['text']};
            padding: 0 {spacing}px;
            border-radius: {radius}px;
            min-height: {touch}px;
        }}
        QLineEdit::placeholder {{
            color: {theme['muted']};
        }}
        QPushButton {{
            background-color: {theme['accent']};
            color: {theme['button_text']};
            border: 1px solid {theme['accent']};
            border-radius: {radius}px;
            padding: 0 {spacing + 4}px;
            font-weight: 600;
            min-height: {touch}px;
        }}
        QPushButton:hover {{
            background-color: {theme['accent_hover']};
            color: {theme['button_hover_text']};
            border-color: {theme['accent_hover']};
        }}
        QPushButton#SegmentButton {{
            background-color: transparent;
            color: {theme['text']};
            border: 1px solid {theme['divider']};
            border-radius: {radius}px;
            padding: 6px 12px;
            min-height: auto;
        }}
        QPushButton#SegmentButton:hover {{
            color: {theme['button_hover_text']};
            border-color: {theme['accent_hover']};
        }}
        QPushButton#TimeframeButton {{
            background-color: transparent;
            border: 1px solid {theme['divider']};
            border-radius: {radius}px;
            padding: 6px 16px;
            color: {theme['muted']};
            font-weight: 600;
            min-height: auto;
        }}
        QPushButton#TimeframeButton:checked {{
            background-color: {theme['accent']};
            color: {theme['text']};
            border-color: {theme['accent_hover']};
        }}
        QPushButton#UtilityButton, QToolButton#UtilityButton {{
            background-color: transparent;
            color: {theme['text']};
            border: 1px solid {theme['text']};
            border-radius: 0px;
            padding: 0 {spacing + 6}px;
            font-weight: 600;
        }}
        QPushButton#UtilityButton:hover, QToolButton#UtilityButton:hover {{
            background-color: {theme['accent_hover']};
            color: {theme['button_hover_text']};
            border-color: {theme['accent_hover']};
        }}
        QToolButton#UtilityIconButton {{
            background-color: transparent;
            border: 1px solid {theme['text']};
            border-radius: 6px;
            padding: 0;
            color: {theme['text']};
        }}
        QToolButton#UtilityIconButton:hover {{
            background-color: {theme['accent']};
            color: {theme['button_text']};
            border-color: {theme['accent']};
        }}
        QPushButton#ToggleButton {{
            background-color: transparent;
            border: 1px solid {theme['text']};
            border-radius: 0px;
            padding: 0 {spacing + 6}px;
            color: {theme['text']};
        }}
        QPushButton#ToggleButton:hover {{
            background-color: {theme['accent_hover']};
            color: {theme['button_hover_text']};
            border-color: {theme['accent_hover']};
        }}
        QTextEdit {{
            background-color: {theme['surface']};
            border: 1px solid {theme['divider']};
            color: {theme['text']};
            border-radius: {card_radius}px;
            padding: {spacing}px;
        }}
        QTextEdit#ChatDisplay {{
            background-color: {theme['surface']};
            border-radius: {card_radius}px;
        }}
        QTableWidget {{
            background-color: {theme['surface']};
            border: 1px solid {theme['divider']};
            color: {theme['text']};
            gridline-color: {theme['border']};
            border-radius: {card_radius}px;
        }}
        QTableWidget::item {{
            padding: {spacing - 4}px;
            background-color: transparent;
        }}
        QHeaderView::section {{
            background-color: {theme['surface_alt']};
            color: {theme['muted']};
            padding: 6px;
            border: none;
        }}
        QToolBar {{
            background: {theme['surface_alt']};
            border: none;
            padding: {spacing - 6}px {spacing}px;
        }}
        """
        self.setStyleSheet(stylesheet)
        if self.theme_button:
            if self.current_theme_name == "dark":
                self.theme_button.setText("☀")
                self.theme_button.setToolTip("Switch to light mode")
            else:
                self.theme_button.setText("☾")
                self.theme_button.setToolTip("Switch to dark mode")
        if self.current_ticker and self.chart_widget:
            self.chart_widget.refresh_theme()
            if self.quote_widget:
                self.quote_widget.set_active_interval(self.chart_widget.current_interval)
    
    def toggle_theme(self):
        self.current_theme_name = "light" if self.current_theme_name == "dark" else "dark"
        self.apply_theme()
    
    def on_ticker_selected(self, ticker: str):
        """Handle ticker selection from the main screener, ensuring all widgets update correctly."""
        if not ticker or self.current_ticker == ticker.upper():
            return
        
        ticker = ticker.upper()
        self.current_ticker = ticker

        # Directly update the brand accent color.
        self.update_brand_accent(ticker)

        # Explicitly update the main hero widget and other primary displays.
        # This ensures they always follow the main selection regardless of linking.
        self.load_widget_ticker("Quotes", ticker)
        if self.chart_widget:
            self.chart_widget.load_ticker(ticker)
        if self.fundamentals_widget:
            self.fundamentals_widget.load_ticker(ticker)
        if self.news_widget:
            self.news_widget.load_ticker(ticker)

        # Also broadcast the ticker to any widgets the user has explicitly linked to the Screener.
        self.broadcast_link_update("Screener", ticker)

        # Update associated UI elements.
        if self.quote_widget and self.chart_widget:
            self.quote_widget.set_active_interval(self.chart_widget.current_interval)
        if self.refresh_button:
            self.refresh_button.setEnabled(True)
        if self.chatbot:
            self.chatbot.add_bot_message(f"Context updated to {ticker}.")
    
    def get_context(self, fetch_analysis=False) -> dict:
        """Get current context for chatbot - enhanced with more details."""
        if fetch_analysis:
            return self.get_signal_analysis_text(self.current_ticker)[0]
        return {
            "ticker": self.current_ticker or "N/A",
            "timeframe": getattr(self.chart_widget, 'current_interval', self.chart_widget.default_interval),
            "timestamp": datetime.now().isoformat(),
            "chart_type": "tradingview_widget",
            "view": "main_chart",
            "theme": self.current_theme_name
        }


def main():
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Modern look
    
    window = TradingTerminal()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

