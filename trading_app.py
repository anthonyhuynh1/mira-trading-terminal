"""
Trading Terminal Application - Cursor-like Interface
Left: Stock Screener | Main: Charts/Fundamentals/News | Right: Context-Aware Chatbot
"""

import sys
import warnings
import colorsys
from collections import defaultdict
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()
warnings.filterwarnings("ignore")

import os

os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu")

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QTextEdit, QLineEdit,
                             QPushButton, QListWidget, QLabel, QTableWidget,
                             QTableWidgetItem, QHeaderView, QDockWidget,
                             QSizePolicy, QFrame, QToolButton, QMenu, QToolBar,
                             QComboBox, QTabWidget, QTabBar, QStackedWidget,
                             QStyle)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize, QEvent
from PyQt6.QtGui import QFont, QAction, QIcon, QCursor
from threading import Lock
from typing import Callable, Dict
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings



import alpaca_trade_api as tradeapi
from alpaca_trade_api.rest import TimeFrame, APIError

# Import our existing strategy code
import strategy
import numpy as np


# Alpaca API global client
api = tradeapi.REST(
    os.environ.get('APCA_API_KEY_ID'),
    os.environ.get('APCA_API_SECRET_KEY'),
    base_url=os.environ.get('APCA_API_BASE_URL'),
    api_version='v2'
)


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
        "tab_bg": "#17171b",
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
        "tab_bg": "#000000",
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


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return r, g, b


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def mix_colors(color_a: str, color_b: str, ratio: float) -> str:
    r1, g1, b1 = hex_to_rgb(color_a)
    r2, g2, b2 = hex_to_rgb(color_b)
    r = int(r1 * (1 - ratio) + r2 * ratio)
    g = int(g1 * (1 - ratio) + g2 * ratio)
    b = int(b1 * (1 - ratio) + b2 * ratio)
    return rgb_to_hex((r, g, b))


def soften_color(color: str, amount: float = 0.4) -> str:
    return mix_colors(color, "#ffffff", amount)


def darken_color(color: str, amount: float = 0.15) -> str:
    return mix_colors(color, "#000000", amount)


def hsv_to_hex(h: float, s: float, v: float) -> str:
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return "#{:02x}{:02x}{:02x}".format(int(r * 255), int(g * 255), int(b * 255))


def ticker_hash_color(ticker: str) -> str:
    if not ticker:
        return "#888888"
    ticker = ticker.upper()
    seed = 0
    for ch in ticker:
        seed = (seed * 31 + ord(ch)) % 360
    hue = seed / 360.0
    saturation = 0.35
    value = 0.78
    return hsv_to_hex(hue, saturation, value)


def ideal_text_color(hex_color: str) -> str:
    if not hex_color:
        return "#000000"
    r, g, b = hex_to_rgb(hex_color)
    luminance = (0.299 * r + 0.587 * g + 0.114 * b)
    return "#000000" if luminance > 150 else "#ffffff"


class TickerDataProvider:
    """Centralized, cache-aware access layer for Alpaca API payloads."""

    SNAPSHOT_TTL = timedelta(seconds=15)
    FUNDAMENTALS_TTL = timedelta(minutes=8)
    NEWS_TTL = timedelta(minutes=2)

    def __init__(self):
        self._lock = Lock()
        self._snapshot_cache: dict[str, tuple[datetime, dict]] = {}
        self._fundamentals_cache: dict[str, tuple[datetime, dict]] = {}
        self._news_cache: dict[str, tuple[datetime, dict]] = {}

    def fetch_snapshot_payload(self, ticker: str) -> dict:
        symbol = (ticker or "").strip().upper()
        if not symbol:
            return {"symbol": "", "status": "No symbol"}
        cached = self._get_cached(self._snapshot_cache, symbol, self.SNAPSHOT_TTL)
        if cached:
            return cached
        payload = self._build_snapshot(symbol)
        self._store_cached(self._snapshot_cache, symbol, payload)
        return payload

    def fetch_fundamentals_payload(self, ticker: str) -> dict:
        symbol = (ticker or "").strip().upper()
        if not symbol:
            return {"ticker": "", "error": "No ticker provided"}
        cached = self._get_cached(self._fundamentals_cache, symbol, self.FUNDAMENTALS_TTL)
        if cached:
            return cached
        payload = self._build_fundamentals(symbol)
        self._store_cached(self._fundamentals_cache, symbol, payload)
        return payload

    def fetch_news_payload(self, ticker: str) -> dict:
        symbol = (ticker or "").strip().upper()
        if not symbol:
            return {"ticker": "", "items": []}
        cached = self._get_cached(self._news_cache, symbol, self.NEWS_TTL)
        if cached:
            return cached
        payload = self._build_news(symbol)
        self._store_cached(self._news_cache, symbol, payload)
        return payload

    def _get_cached(self, cache: dict, symbol: str, ttl: timedelta) -> dict | None:
        with self._lock:
            entry = cache.get(symbol)
            if not entry:
                return None
            ts, payload = entry
            if datetime.utcnow() - ts > ttl:
                cache.pop(symbol, None)
                return None
            return payload

    def _store_cached(self, cache: dict, symbol: str, payload: dict):
        with self._lock:
            cache[symbol] = (datetime.utcnow(), payload)

    def _build_snapshot(self, symbol: str) -> dict:
        snapshot = {"symbol": symbol}
        print(f"Building snapshot for {symbol}")
        try:
            latest_quote = api.get_latest_quote(symbol)
            asset = api.get_asset(symbol)

            price = latest_quote.ap  # Ask price
            # Fetch previous day's close for change calculation
            end_dt = datetime.now(ZoneInfo("UTC")) - timedelta(days=1)
            start_dt = end_dt - timedelta(days=4) # Go back a few days to ensure we get a trading day
            prev_day_bars = api.get_bars(symbol, TimeFrame.Day, start=start_dt.strftime('%Y-%m-%d'), end=end_dt.strftime('%Y-%m-%d')).df
            prev_close = prev_day_bars['close'].iloc[-1] if not prev_day_bars.empty else None

            if price is not None and prev_close is not None:
                change = price - prev_close
                change_pct = (change / prev_close) * 100 if prev_close else None
            else:
                change = None
                change_pct = None

            # Get daily volume from latest daily bar
            latest_daily_bar = api.get_bars(symbol, TimeFrame.Day, limit=1).df
            volume = latest_daily_bar['volume'].iloc[0] if not latest_daily_bar.empty else None
            
            snapshot.update({
                "name": asset.name,
                "price": price,
                "change": change,
                "change_pct": change_pct,
                "volume": volume,
                "volume_label": "Session volume",
                "time": datetime.now().strftime("%b %d - %H:%M"),
                "status": "Live Data" if asset.tradable else "Not Tradable",
            })
            print(f"Snapshot data for {symbol}: {snapshot}")
        except APIError as e:
            snapshot["status"] = "Data issue"
            snapshot["error"] = str(e)
            print(f"API Error for {symbol}: {e}")
        except Exception as exc:
            snapshot["status"] = "Data issue"
            snapshot["error"] = str(exc)
            print(f"Generic Error for {symbol}: {exc}")
        return snapshot

    def _build_fundamentals(self, symbol: str) -> dict:
        try:
            asset = api.get_asset(symbol)
            metrics = [
                ("Symbol", asset.symbol),
                ("Exchange", asset.exchange),
                ("Asset Class", asset.asset_class),
                ("Status", asset.status),
                ("Tradable", asset.tradable),
                ("Marginable", asset.marginable),
                ("Shortable", asset.shortable),
            ]
            return {"ticker": symbol, "metrics": metrics}
        except Exception as exc:
            return {"ticker": symbol, "error": str(exc)}

    def _build_news(self, symbol: str) -> dict:
        try:
            news_items = api.get_news(symbol, limit=12)
            items = []
            for item in news_items:
                title = item.headline
                timestamp = item.created_at
                date_str = timestamp.strftime("%b %d") if timestamp else "--"
                items.append(f"[{date_str}] {title}")
            return {"ticker": symbol, "items": items}
        except Exception as exc:
            return {"ticker": symbol, "error": str(exc)}

    @staticmethod
    def _market_status_text(fast_info: dict, info: dict) -> str:
        # This method is no longer used with Alpaca, but we keep it for reference
        # or if we want to re-implement a similar logic based on Alpaca's market status endpoints
        return "Live Data"



class SnapshotWorker(QThread):
    """Background worker to fetch ticker snapshots off the UI thread."""

    result_ready = pyqtSignal(dict)

    def __init__(self, fetch_callable: Callable[[], dict]):
        super().__init__()
        self.fetch_callable = fetch_callable

    def run(self):
        try:
            snapshot = self.fetch_callable()
        except Exception as exc:
            snapshot = {"status": "Data issue", "error": str(exc)}
        self.result_ready.emit(snapshot)


class WorkspaceDock(QDockWidget):
    """Dock widget with Mira header, inline tabs, and stacked content."""

    closed = pyqtSignal(object)
    collapsed_changed = pyqtSignal(object, bool)
    tab_removed = pyqtSignal(str)
    tab_added = pyqtSignal(str)
    active_tab_changed = pyqtSignal(str)

    def __init__(self, dock_id: str, initial_key: str, widget: QWidget, parent: QMainWindow,
                 link_callback: Callable[[str, int | None], None] | None = None,
                 widget_menu_callback: Callable[[object, QWidget | None], None] | None = None):
        super().__init__(initial_key, parent)
        self.dock_id = dock_id
        self.setObjectName(dock_id)
        self.setContentsMargins(0, 0, 0, 0)
        self.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetClosable |
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.collapsed = False
        self._collapsed_height = 48
        self.link_callback = link_callback
        self.widget_menu_callback = widget_menu_callback
        self._link_group: int | None = None
        self._options_menu: QMenu | None = None
        self.tab_widgets: dict[str, QWidget] = {}
        self.tab_order: list[str] = []

        self._init_title_bar()
        self._init_body()
        self.add_tab(initial_key, widget, initial_key)

    def _init_title_bar(self):
        title_bar = QWidget()
        title_bar.setObjectName("DockTitleBar")
        layout = QHBoxLayout(title_bar)
        layout.setContentsMargins(12, 6, 8, 6)
        layout.setSpacing(6)

        self.title_label = QLabel("")
        self.title_label.setObjectName("DockTitleLabel")
        self.title_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        layout.addWidget(self.title_label)

        self.tab_bar = QTabBar()
        self.tab_bar.setObjectName("DockTabBar")
        self.tab_bar.setExpanding(False)
        self.tab_bar.setMovable(True)
        self.tab_bar.setDrawBase(False)
        self.tab_bar.setUsesScrollButtons(True)
        self.tab_bar.currentChanged.connect(self._on_tab_changed)
        self.tab_bar.tabMoved.connect(self._on_tab_moved)
        layout.addWidget(self.tab_bar, stretch=1)

        self.menu_btn = self._create_options_button()
        layout.addWidget(self.menu_btn)

        self.min_btn = self._create_icon_button("icons/minimize.svg", self.toggle_collapsed, "Minimize")
        self.expand_btn = self._create_icon_button("icons/expand.svg", self.expand_to_fill, "Expand to fit space")
        self.float_btn = self._create_icon_button("icons/float.svg", self._toggle_floating, "Float / Dock")
        self.close_btn = self._create_icon_button("icons/close.svg", self._handle_close_clicked, "Close")

        for btn in (self.min_btn, self.expand_btn, self.float_btn, self.close_btn):
            layout.addWidget(btn)

        self.setTitleBarWidget(title_bar)
        title_bar.installEventFilter(self)
        self._rebuild_options_menu()

    def _init_body(self):
        body = QFrame()
        body.setObjectName("DockBody")
        layout = QVBoxLayout(body)
        layout.setContentsMargins(BASE_SPACING, BASE_SPACING, BASE_SPACING, BASE_SPACING)
        layout.setSpacing(BASE_SPACING)
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)
        self.setWidget(body)

    def _create_button(self, text: str, handler: Callable, tooltip: str) -> QToolButton:
        btn = QToolButton()
        btn.setText(text)
        btn.setToolTip(tooltip)
        btn.clicked.connect(handler)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedSize(QSize(26, 22))
        btn.setObjectName("DockButton")
        return btn

    def _create_icon_button(self, icon_name: str, handler: Callable, tooltip: str) -> QToolButton:
        btn = QToolButton()
        btn.setToolTip(tooltip)
        btn.clicked.connect(handler)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedSize(QSize(24, 24))
        btn.setObjectName("DockIconButton")
        btn.setIconSize(QSize(12, 12))
        btn.setProperty("icon_name", icon_name)
        icon_map = {
            "icons/minimize.svg": QStyle.StandardPixmap.SP_TitleBarMinButton,
            "icons/expand.svg": QStyle.StandardPixmap.SP_TitleBarMaxButton,
            "icons/float.svg": QStyle.StandardPixmap.SP_TitleBarNormalButton,
            "icons/close.svg": QStyle.StandardPixmap.SP_TitleBarCloseButton,
        }
        btn.setIcon(self.style().standardIcon(icon_map.get(icon_name, QStyle.StandardPixmap.SP_TitleBarMenuButton)))
        btn.setText("")
        return btn

    def _create_options_button(self) -> QToolButton:
        btn = QToolButton()
        btn.setObjectName("DockIconButton")
        btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarMenuButton))
        btn.setToolTip("Widget options")
        btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedSize(QSize(24, 24))
        return btn

    def _rebuild_options_menu(self):
        if self._options_menu:
            self._options_menu.deleteLater()
        menu = QMenu(self)
        add_action = menu.addAction("Add Widget…")
        add_action.triggered.connect(self._handle_add_widget)
        menu.addSeparator()
        link_menu = menu.addMenu("Link Group")
        none_action = link_menu.addAction("No Link")
        none_action.setCheckable(True)
        none_action.setChecked(self._link_group is None)
        none_action.triggered.connect(lambda: self._set_link_group(None))
        for group in range(1, 7):
            action = link_menu.addAction(f"Group {group}")
            action.setCheckable(True)
            action.setChecked(self._link_group == group)
            action.triggered.connect(lambda checked=False, g=group: self._set_link_group(g))
        menu.addSeparator()
        float_action = menu.addAction("Float / Dock")
        float_action.triggered.connect(self._toggle_floating)
        self.menu_btn.setMenu(menu)
        self._options_menu = menu

    def _handle_add_widget(self):
        if self.widget_menu_callback:
            anchor = self.titleBarWidget() or self
            self.widget_menu_callback(self, anchor)

    def _set_link_group(self, group: int | None):
        current_key = self.current_tab_key()
        if current_key and self.link_callback:
            self.link_callback(current_key, group)
        self._link_group = group
        self._rebuild_options_menu()

    def add_tab(self, key: str, widget: QWidget, title: str):
        if key in self.tab_widgets:
            self.focus_tab(key)
            return
        widget.setParent(self.stack)
        self.stack.addWidget(widget)
        tab_index = self.tab_bar.addTab(title)
        self.tab_bar.setTabData(tab_index, key)
        self.tab_widgets[key] = widget
        self.tab_order.insert(tab_index, key)
        self.tab_bar.setCurrentIndex(tab_index)
        self.tab_added.emit(key)
        self._update_title_label()

    def take_tab(self, key: str) -> QWidget | None:
        idx = self._index_for_key(key)
        if idx is None:
            return None
        return self._remove_tab_at(idx, delete=False, emit_signal=False)

    def focus_tab(self, key: str):
        idx = self._index_for_key(key)
        if idx is None:
            return
        self.tab_bar.setCurrentIndex(idx)

    def current_tab_key(self) -> str | None:
        idx = self.tab_bar.currentIndex()
        if idx < 0 or idx >= len(self.tab_order):
            return None
        return self.tab_order[idx]

    def list_tab_keys(self) -> list[str]:
        return list(self.tab_order)

    def is_empty(self) -> bool:
        return not self.tab_order

    def _index_for_key(self, key: str) -> int | None:
        try:
            return self.tab_order.index(key)
        except ValueError:
            return None

    def _on_tab_changed(self, index: int):
        if index < 0:
            return
        self.stack.setCurrentIndex(index)
        self._update_title_label()
        key = self.current_tab_key()
        if key:
            self.active_tab_changed.emit(key)

    def _on_tab_moved(self, from_index: int, to_index: int):
        if from_index == to_index:
            return
        key = self.tab_order.pop(from_index)
        self.tab_order.insert(to_index, key)
        widget = self.stack.widget(from_index)
        self.stack.removeWidget(widget)
        self.stack.insertWidget(to_index, widget)

    def _remove_tab_at(self, index: int, delete: bool = True, emit_signal: bool = True) -> QWidget | None:
        if index < 0 or index >= len(self.tab_order):
            return None
        key = self.tab_order.pop(index)
        widget = self.stack.widget(index)
        self.stack.removeWidget(widget)
        self.tab_bar.blockSignals(True)
        self.tab_bar.removeTab(index)
        self.tab_bar.blockSignals(False)
        self.tab_widgets.pop(key, None)
        if emit_signal:
            self.tab_removed.emit(key)
        if delete:
            widget.deleteLater()
        else:
            widget.setParent(None)
        if self.tab_bar.count():
            next_index = min(index, self.tab_bar.count() - 1)
            self.tab_bar.setCurrentIndex(next_index)
        else:
            QTimer.singleShot(0, self.close)
        self._update_title_label()
        return widget

    def _handle_close_clicked(self):
        idx = self.tab_bar.currentIndex()
        self._remove_tab_at(idx, delete=True, emit_signal=True)

    def toggle_collapsed(self):
        self.set_collapsed(not self.collapsed)

    def set_collapsed(self, collapsed: bool):
        if self.collapsed == collapsed:
            return
        self.collapsed = collapsed
        if self.widget():
            self.widget().setVisible(not self.collapsed)
        self.setVisible(not self.collapsed)
        if not self.collapsed:
            self.setMaximumHeight(16777215)
            self.setMinimumHeight(0)
        self.collapsed_changed.emit(self, self.collapsed)

    def _toggle_floating(self):
        self.setFloating(not self.isFloating())

    def expand_to_fill(self):
        mw = self.parent()
        while mw and not isinstance(mw, QMainWindow):
            mw = mw.parent()
        if not mw:
            return
        mw.resizeDocks([self], [mw.width()], Qt.Orientation.Horizontal)
        mw.resizeDocks([self], [mw.height()], Qt.Orientation.Vertical)

    def closeEvent(self, event):
        # Always allow close - emit signal so parent can clean up
        self.closed.emit(self)
        super().closeEvent(event)

    def eventFilter(self, obj, event):
        if obj is self.titleBarWidget():
            if event.type() == QEvent.Type.MouseButtonDblClick and event.button() == Qt.MouseButton.LeftButton:
                self._toggle_floating()
                return True
            if event.type() in (QEvent.Type.MouseButtonPress,
                                QEvent.Type.MouseButtonRelease,
                                QEvent.Type.MouseMove):
                QApplication.sendEvent(self, event)
                return False
        return super().eventFilter(obj, event)

    def set_link_group_display(self, group: int | None):
        self._link_group = group
        self._update_title_label()
        self._rebuild_options_menu()

    def _update_title_label(self):
        if not hasattr(self, "title_label"):
            return
        text = self.current_tab_key() or ""
        if self._link_group:
            text = f"{text} · #{self._link_group}"
        display = text.upper()
        # Hide title label when tabs exist (tabs show the names)
        self.title_label.setVisible(self.tab_bar.count() == 0)
        self.title_label.setText(display)
        super().setWindowTitle(display)


class StatPill(QFrame):
    """Small stat widget used in the hero section."""

    def __init__(self, label: str):
        super().__init__()
        self.setObjectName("StatPill")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(2)

        self.label = QLabel(label.upper())
        self.label.setObjectName("StatLabel")
        self.value = QLabel("--")
        self.value.setObjectName("StatValue")
        self.subtext = QLabel("")
        self.subtext.setObjectName("StatSubtext")

        layout.addWidget(self.label)
        layout.addWidget(self.value)
        layout.addWidget(self.subtext)

    def set_value(self, text: str):
        self.value.setText(text)

    def set_subtext(self, text: str):
        self.subtext.setText(text)

    def set_trend(self, trend: str | None):
        self.setProperty("trend", trend or "")
        self.style().unpolish(self)
        self.style().polish(self)


class QuoteWidget(QFrame):
    """Headline card showcasing the active ticker and quick controls."""

    def __init__(self, interval_callback):
        super().__init__()
        self.interval_callback = interval_callback
        self.setObjectName("QuoteCard")
        self.active_interval = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(BASE_SPACING)

        self.header_frame = QFrame()
        self.header_frame.setObjectName("ModuleHeader")
        header_layout = QHBoxLayout(self.header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)

        self.ticker_label = QLabel("--")
        self.ticker_label.setObjectName("QuoteTicker")
        self.subtitle_label = QLabel("Pick a ticker from the watchlist to get started.")
        self.subtitle_label.setObjectName("QuoteSubtitle")

        title_stack = QVBoxLayout()
        title_stack.setSpacing(2)
        title_stack.addWidget(self.ticker_label)
        title_stack.addWidget(self.subtitle_label)

        header_layout.addLayout(title_stack)
        header_layout.addStretch()

        self.status_badge = QLabel("Status: --")
        self.status_badge.setObjectName("StatusBadge")
        header_layout.addWidget(self.status_badge)

        layout.addWidget(self.header_frame)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(BASE_SPACING)

        self.stat_widgets = {
            "price": StatPill("Last Price"),
            "change": StatPill("Session Change"),
            "volume": StatPill("Volume"),
            "range": StatPill("Range"),
        }
        for pill in self.stat_widgets.values():
            stats_row.addWidget(pill)

        layout.addLayout(stats_row)

        self.brand_color = None
        self.set_active_interval("60")
        self.apply_brand_color(None)

    def apply_brand_color(self, color: str | None):
        self.brand_color = color
        if color:
            text_color = ideal_text_color(color)
            self.status_badge.setStyleSheet(
                f"background-color: {color}; color: {text_color}; padding: 6px 14px; border-radius: 0px;"
            )
            self.status_badge.setVisible(True)
            for pill in self.stat_widgets.values():
                pill.setStyleSheet(f"QFrame#StatPill{{ border: 1px solid {color}; }}")
        else:
            self.status_badge.setStyleSheet("background: transparent; border: none; padding: 0; color: inherit;")
            self.status_badge.setVisible(False)
            for pill in self.stat_widgets.values():
                pill.setStyleSheet("")

    def set_active_interval(self, interval: str):
        self.active_interval = interval

    def set_tab_mode(self, tabbed: bool):
        if hasattr(self, "header_frame"):
            self.header_frame.setVisible(not tabbed)

    def show_loading(self, ticker: str):
        symbol = (ticker or "--").upper()
        self.ticker_label.setText(symbol)
        self.subtitle_label.setText("Fetching latest snapshot...")
        self.status_badge.setText("Loading...")
        self.status_badge.setVisible(True)
        for pill in self.stat_widgets.values():
            pill.set_value("--")
            pill.set_subtext("Loading")
            pill.set_trend("")

    def update_snapshot(self, snapshot: dict):
        symbol = snapshot.get("symbol") or "--"
        name = snapshot.get("name") or "Awaiting selection"
        price = snapshot.get("price")
        change = snapshot.get("change")
        change_pct = snapshot.get("change_pct")
        volume = snapshot.get("volume")
        range_text = snapshot.get("range")
        status = snapshot.get("status") or "Live"

        self.ticker_label.setText(symbol)
        self.subtitle_label.setText(name)
        self.status_badge.setText(self._format_status(status))

        if price is not None:
            self.stat_widgets["price"].set_value(f"${price:,.2f}")
        else:
            self.stat_widgets["price"].set_value("--")
        self.stat_widgets["price"].set_subtext(snapshot.get("time") or "")

        if change is not None and change_pct is not None:
            sign = "+" if change >= 0 else "-"
            self.stat_widgets["change"].set_value(f"{sign}${abs(change):,.2f}")
            self.stat_widgets["change"].set_subtext(f"{sign}{abs(change_pct):.2f}% session")
            trend = "positive" if change >= 0 else "negative"
            self.stat_widgets["change"].set_trend(trend)
        else:
            self.stat_widgets["change"].set_value("--")
            self.stat_widgets["change"].set_subtext("No data")
            self.stat_widgets["change"].set_trend("")

        if volume is not None:
            try:
                vol_value = float(volume)
                if abs(vol_value) >= 1_000_000:
                    volume_display = f"{vol_value/1_000_000:.2f}M"
                else:
                    volume_display = f"{vol_value:,.0f}"
            except (TypeError, ValueError):
                volume_display = str(volume)
            self.stat_widgets["volume"].set_value(volume_display)
            self.stat_widgets["volume"].set_subtext(snapshot.get("volume_label", "Latest"))
        else:
            self.stat_widgets["volume"].set_value("--")
            self.stat_widgets["volume"].set_subtext("No data")

        if range_text:
            self.stat_widgets["range"].set_value(range_text)
            self.stat_widgets["range"].set_subtext(snapshot.get("range_label", "52W range"))
        else:
            self.stat_widgets["range"].set_value("--")
            self.stat_widgets["range"].set_subtext("")

    def _format_status(self, raw_status: str) -> str:
        status = (raw_status or "").strip().lower().replace("_", " ")
        if status.startswith("pre"):
            return "Status: Pre-market"
        if status.startswith("post") or status.startswith("after"):
            return "Status: After hours"
        if status.startswith("live") or status.startswith("regular"):
            return "Status: Open"
        if status.startswith("close"):
            return "Status: Closed"
        if not status:
            return "Status: --"
        return f"Status: {raw_status.title()}"


class MarketClockWidget(QWidget):
    """Displays market time and open/closed status with timezone selector."""

    MARKETS = {
        "New York (NYSE)": {
            "tz": "America/New_York",
            "open": time(9, 30),
            "close": time(16, 0),
            "pre": timedelta(hours=2),
            "after": timedelta(hours=4),
        },
        "London (LSE)": {
            "tz": "Europe/London",
            "open": time(8, 0),
            "close": time(16, 30),
            "pre": timedelta(hours=1),
            "after": timedelta(hours=2),
        },
        "Tokyo (TSE)": {
            "tz": "Asia/Tokyo",
            "open": time(9, 0),
            "close": time(15, 0),
            "pre": timedelta(hours=1),
            "after": timedelta(hours=2),
        },
    }

    def __init__(self):
        super().__init__()
        self.setObjectName("ClockCard")
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        self.selector = QComboBox()
        self.selector.setObjectName("ClockSelector")
        for name in self.MARKETS:
            self.selector.addItem(name)
        self.selector.currentIndexChanged.connect(self.update_time)
        layout.addWidget(self.selector)

        self.time_label = QLabel("--:--:--")
        self.time_label.setObjectName("ClockTime")
        self.status_label = QLabel("Status: --")
        self.status_label.setObjectName("ClockStatus")
        layout.addWidget(self.time_label)
        layout.addWidget(self.status_label)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1_000)
        self.update_time()

    def update_time(self):
        market = self.MARKETS[self.selector.currentText()]
        tz = ZoneInfo(market["tz"])
        now = datetime.now(tz)
        self.time_label.setText(now.strftime("%H:%M:%S"))
        status = self._determine_status(now, market)
        self.status_label.setText(f"{status} - {now.strftime('%b %d')}")

    def _determine_status(self, now: datetime, market: dict) -> str:
        open_dt = now.replace(hour=market["open"].hour, minute=market["open"].minute,
                              second=0, microsecond=0)
        close_dt = now.replace(hour=market["close"].hour, minute=market["close"].minute,
                               second=0, microsecond=0)
        pre_start = open_dt - market["pre"]
        after_end = close_dt + market["after"]

        if pre_start <= now < open_dt:
            return "Pre-market"
        if open_dt <= now <= close_dt:
            return "Open"
        if close_dt < now <= after_end:
            return "After hours"
        return "Closed"

class ChartWidget(QWidget):
    """Standalone chart widget (TradingView embed)."""
    
    def __init__(self, theme_provider):
        super().__init__()
        self.theme_provider = theme_provider
        self.current_ticker = None
        self.default_interval = "60"  # TradingView interval codes (60 = 1h)
        self.current_interval = self.default_interval
        self.last_chart_signature: tuple[str, str, str] | None = None
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
    
    def update_chart(self, ticker: str, interval: str | None = None):
        """Update chart using TradingView's official widget for a native experience."""
        interval = interval or self.current_interval or self.default_interval
        self.current_interval = interval
        theme = self.theme_provider()
        signature = (ticker.upper(), interval, theme["chart_theme"])
        if signature == self.last_chart_signature:
            return
        self.last_chart_signature = signature
        html = self.create_tradingview_widget_html(ticker, interval)
        self.chart_view.setHtml(html)
    
    def refresh_theme(self):
        self.last_chart_signature = None
        if self.current_ticker:
            self.update_chart(self.current_ticker, self.current_interval)
    
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
    

class FundamentalsWidget(QWidget):
    """Standalone fundamentals table widget."""

    def __init__(self, data_provider: TickerDataProvider):
        super().__init__()
        self.data_provider = data_provider
        layout = QVBoxLayout(self)
        layout.setContentsMargins(BASE_SPACING, BASE_SPACING, BASE_SPACING, BASE_SPACING)
        layout.setSpacing(BASE_SPACING)

        self.header_frame = QFrame()
        header_layout = QVBoxLayout(self.header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(2)
        title = QLabel("Fundamentals")
        title.setObjectName("SectionTitle")
        subtitle = QLabel("Key valuation metrics and ratios.")
        subtitle.setObjectName("SectionHint")
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        layout.addWidget(self.header_frame)

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Metric", "Value"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        self._pending_ticker: str | None = None
        self._workers: list[SnapshotWorker] = []

    def load_ticker(self, ticker: str):
        ticker = (ticker or "").strip().upper()
        if not ticker:
            return
        self._pending_ticker = ticker
        self._show_loading_state()
        self._run_async_task(lambda t=ticker: self._fetch_fundamentals(t), self._apply_fundamentals_payload)

    def _run_async_task(self, fetcher: Callable[[], dict], handler: Callable[[dict], None]):
        worker = SnapshotWorker(fetcher)
        worker.result_ready.connect(handler)
        worker.finished.connect(lambda w=worker: self._finalize_worker(w))
        self._workers.append(worker)
        worker.start()

    def _finalize_worker(self, worker: SnapshotWorker):
        if worker in self._workers:
            self._workers.remove(worker)
        worker.deleteLater()

    def _show_loading_state(self):
        self.table.setRowCount(1)
        self.table.setItem(0, 0, QTableWidgetItem("Loading"))
        self.table.setItem(0, 1, QTableWidgetItem("Fetching fundamentals..."))

    def _fetch_fundamentals(self, ticker: str) -> dict:
        if not self.data_provider:
            return {"ticker": ticker, "error": "Data provider unavailable"}
        return self.data_provider.fetch_fundamentals_payload(ticker)

    def _apply_fundamentals_payload(self, payload: dict):
        ticker = payload.get("ticker")
        if self._pending_ticker and ticker != self._pending_ticker:
            return
        if payload.get("error"):
            self._display_error(payload["error"])
            return
        metrics = payload.get("metrics", [])
        self.table.setRowCount(len(metrics))
        for row, (metric, value) in enumerate(metrics):
            self.table.setItem(row, 0, QTableWidgetItem(str(metric)))
            self.table.setItem(row, 1, QTableWidgetItem(str(value)))

    def _display_error(self, message: str):
        self.table.setRowCount(1)
        self.table.setItem(0, 0, QTableWidgetItem("Error"))
        self.table.setItem(0, 1, QTableWidgetItem(message))
    
    def set_tab_mode(self, tabbed: bool):
        if hasattr(self, "header_frame"):
            self.header_frame.setVisible(not tabbed)


class NewsWidget(QWidget):
    """Standalone news list widget."""

    def __init__(self, data_provider: TickerDataProvider):
        super().__init__()
        self.data_provider = data_provider
        layout = QVBoxLayout(self)
        layout.setContentsMargins(BASE_SPACING, BASE_SPACING, BASE_SPACING, BASE_SPACING)
        layout.setSpacing(BASE_SPACING)

        self.header_frame = QFrame()
        header_layout = QVBoxLayout(self.header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(2)
        title = QLabel("Market News")
        title.setObjectName("SectionTitle")
        subtitle = QLabel("Latest headlines for the active symbol.")
        subtitle.setObjectName("SectionHint")
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        layout.addWidget(self.header_frame)

        self.news_list = QListWidget()
        self.news_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.news_list)

        self._pending_ticker: str | None = None
        self._workers: list[SnapshotWorker] = []

    def load_ticker(self, ticker: str):
        ticker = (ticker or "").strip().upper()
        if not ticker:
            return
        self._pending_ticker = ticker
        self._show_loading_state()
        self._run_async_task(lambda t=ticker: self._fetch_news(t), self._apply_news_payload)

    def _run_async_task(self, fetcher: Callable[[], dict], handler: Callable[[dict], None]):
        worker = SnapshotWorker(fetcher)
        worker.result_ready.connect(handler)
        worker.finished.connect(lambda w=worker: self._finalize_worker(w))
        self._workers.append(worker)
        worker.start()

    def _finalize_worker(self, worker: SnapshotWorker):
        if worker in self._workers:
            self._workers.remove(worker)
        worker.deleteLater()

    def _show_loading_state(self):
        self.news_list.clear()
        self.news_list.addItem("Loading headlines...")

    def _fetch_news(self, ticker: str) -> dict:
        if not self.data_provider:
            return {"ticker": ticker, "error": "Data provider unavailable"}
        return self.data_provider.fetch_news_payload(ticker)

    def _apply_news_payload(self, payload: dict):
        ticker = payload.get("ticker")
        if self._pending_ticker and ticker != self._pending_ticker:
            return
        if payload.get("error"):
            self._display_error(payload["error"])
            return
        entries = payload.get("items", [])
        self.news_list.clear()
        if not entries:
            self.news_list.addItem("No recent news.")
            return
        for entry in entries:
            self.news_list.addItem(entry)

    def _display_error(self, message: str):
        self.news_list.clear()
        self.news_list.addItem(f"Error loading news: {message}")

    def set_tab_mode(self, tabbed: bool):
        if hasattr(self, "header_frame"):
            self.header_frame.setVisible(not tabbed)


class ChatbotWidget(QWidget):
    """Context-aware chatbot panel."""
    
    def __init__(self, context_callback):
        super().__init__()
        self.context_callback = context_callback  # Function to get current context
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(BASE_SPACING)
        layout.setContentsMargins(BASE_SPACING, BASE_SPACING, BASE_SPACING, BASE_SPACING)

        self.header_frame = QFrame()
        header_layout = QVBoxLayout(self.header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(2)
        title = QLabel("AI Copilot")
        title.setObjectName("SectionTitle")
        subtitle = QLabel("Context-aware assistant that knows your current view.")
        subtitle.setObjectName("SectionHint")
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        layout.addWidget(self.header_frame)
        
        # Chat display
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont("Courier", 10))
        self.chat_display.setObjectName("ChatDisplay")
        self.chat_display.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.chat_display)
        
        # Input
        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Ask about the chart, strategy, or ticker...")
        self.input_field.returnPressed.connect(self.send_message)
        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self.send_message)
        self.input_field.setMinimumHeight(TOUCH_TARGET)
        self.send_btn.setMinimumHeight(TOUCH_TARGET)
        self.input_field.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.send_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_btn)
        layout.addLayout(input_layout)
        
        self.setLayout(layout)
        self.add_bot_message("Hi! I'm your trading assistant. Ask me about charts, signals, or strategies!")
    
    def set_tab_mode(self, tabbed: bool):
        if hasattr(self, "header_frame"):
            self.header_frame.setVisible(not tabbed)
    
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
    
                    return self.context_callback(fetch_analysis=True)
    
            
    
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
    
    def __init__(self, ticker_callback, analysis_callback):
        super().__init__()
        self.ticker_callback = ticker_callback  # Callback when ticker selected
        self.analysis_callback = analysis_callback # Callback to trigger AI analysis
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(BASE_SPACING)
        layout.setContentsMargins(BASE_SPACING, BASE_SPACING, BASE_SPACING, BASE_SPACING)

        self.header_frame = QFrame()
        header_layout = QVBoxLayout(self.header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(2)
        title = QLabel("Market Scanner")
        title.setObjectName("SectionTitle")
        subtitle = QLabel("Search, filter, and monitor breakout-ready names.")
        subtitle.setObjectName("SectionHint")
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        layout.addWidget(self.header_frame)
        
        # Search box
        search_layout = QHBoxLayout()
        search_layout.setSpacing(8)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search ticker...")
        self.search_input.returnPressed.connect(self.search_ticker)
        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self.search_ticker)
        self.search_btn.setMinimumHeight(TOUCH_TARGET)
        self.search_input.setMinimumHeight(TOUCH_TARGET)
        self.search_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.search_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_btn)
        layout.addLayout(search_layout)
        
        # Quick filters
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)
        filters = [
            ("Breakouts", "breakout"),
            ("False breaks", "false"),
            ("Tight ranges", "consolidation"),
            ("Volume spikes", "volume"),
        ]
        for label, key in filters:
            btn = QPushButton(label)
            btn.setObjectName("SegmentButton")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(lambda checked, l=label, k=key: self.apply_filter(l, k))
            filter_row.addWidget(btn)
        layout.addLayout(filter_row)

        self.filter_summary = QLabel("Focus: All setups")
        self.filter_summary.setObjectName("SectionHint")
        layout.addWidget(self.filter_summary)
        
        # Quick scan button
        scan_btn = QPushButton("Scan Universe")
        scan_btn.clicked.connect(self.scan_universe)
        scan_btn.setMinimumHeight(TOUCH_TARGET)
        scan_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(scan_btn)
        
        # Ticker list
        self.ticker_list = QListWidget()
        self.ticker_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.ticker_list.customContextMenuRequested.connect(self._show_ticker_context_menu)
        self.ticker_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.ticker_list.itemClicked.connect(self.on_ticker_selected)
        watchlist_label = QLabel("Watchlist")
        watchlist_label.setObjectName("SectionTitle")
        layout.addWidget(watchlist_label)
        layout.addWidget(self.ticker_list)
        
        # Load default tickers
        for ticker in strategy.TICKERS:
            self.ticker_list.addItem(ticker)
        
        self.setLayout(layout)
        self.active_filter = "all"
    
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
        self.ticker_list.addItem("Scanning...")
        self.filter_summary.setText("Focus: Running scan...")
    
    def apply_filter(self, label: str, key: str):
        """Update selected filter badge."""
        self.active_filter = key
        self.filter_summary.setText(f"Focus: {label}")
    
    def on_ticker_selected(self, item):
        """Handle ticker selection."""
        text = item.text().strip()
        if text.lower().startswith("scanning"):
            return
        self.ticker_callback(text)

    def _show_ticker_context_menu(self, position):
        """Show context menu for ticker list."""
        item = self.ticker_list.itemAt(position)
        if not item:
            return
        
        ticker = item.text().strip()
        
        menu = QMenu()
        ai_menu = menu.addMenu("AI Copilot")
        
        analyze_action = QAction("Analyze Consolidation Breakout", self)
        analyze_action.triggered.connect(lambda checked, t=ticker: self.analysis_callback(t))
        ai_menu.addAction(analyze_action)
        
        menu.exec(self.ticker_list.mapToGlobal(position))
    
    def set_tab_mode(self, tabbed: bool):
        if hasattr(self, "header_frame"):
            self.header_frame.setVisible(not tabbed)


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
        quotes = self.ensure_widget("Quotes", Qt.DockWidgetArea.TopDockWidgetArea)
        chart = self.ensure_widget("Chart", Qt.DockWidgetArea.RightDockWidgetArea)
        screener = self.ensure_widget("Screener", Qt.DockWidgetArea.LeftDockWidgetArea)
        fundamentals = self.ensure_widget("Fundamentals", Qt.DockWidgetArea.BottomDockWidgetArea)

        # Arrange primary layout
        if chart and fundamentals:
            self.splitDockWidget(chart, fundamentals, Qt.Orientation.Vertical)
        if quotes and chart:
            self.splitDockWidget(quotes, chart, Qt.Orientation.Vertical)
        if screener and chart:
            self.splitDockWidget(screener, chart, Qt.Orientation.Horizontal)
        
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
        analysis_text = self.get_signal_analysis_text(ticker)
        self.chatbot.add_bot_message(analysis_text)

    def get_signal_analysis_text(self, ticker: str) -> str:
        """Fetches data and returns a formatted string of the current signal analysis."""
        try:
            df = strategy.fetch_hourly_data(ticker, period_days=30)
            if df.empty:
                return f"Could not retrieve data for {ticker}."
            
            sigs = strategy.breakout_volume_signals(df)
            last_sig = sigs.iloc[-1]
            current_price = df["Close"].iloc[-1]
            cons_high = float(last_sig["cons_high_prev"]) if not np.isnan(last_sig["cons_high_prev"]) else None
            cons_low = float(last_sig["cons_low_prev"]) if not np.isnan(last_sig["cons_low_prev"]) else None
            
            if bool(last_sig["false_breakout"]):
                return f"""**{ticker} - FALSE BREAKOUT Signal**

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
                return f"""**{ticker} - TRUE BREAKOUT Signal**

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
            
            elif bool(last_sig["cons_ok"]):
                breakout_level = float(last_sig["breakout_level"])
                dist_pct = ((breakout_level - current_price) / current_price) * 100
                return f"""**{ticker} - CONSOLIDATION SETUP**

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
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Modern look
    
    window = TradingTerminal()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

