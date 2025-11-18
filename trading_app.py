"""
Trading Terminal Application - Cursor-like Interface
Left: Stock Screener | Main: Charts/Fundamentals/News | Right: Context-Aware Chatbot
"""

import sys
import warnings
import colorsys
from collections import defaultdict
from functools import partial
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
warnings.filterwarnings("ignore")

import os

os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu")

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGridLayout, QTextEdit, QLineEdit,
                             QPushButton, QListWidget, QLabel, QTableWidget,
                             QTableWidgetItem, QHeaderView, QDockWidget,
                             QSizePolicy, QFrame, QToolButton, QMenu, QToolBar,
                             QComboBox, QTabWidget, QSplitter, QStyle, QTabBar)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QUrl, QSize, QEvent, QObject
from PyQt6.QtGui import QFont, QAction, QIcon
from typing import Any, Callable, Dict
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings


class DockTabBarFilter(QObject):
    """Hide Qt's built-in dock tab bars so custom headers can render tabs."""

    def __init__(self, parent=None):
        super().__init__(parent)

    def _is_dock_tabbar(self, obj):
        if isinstance(obj, QTabBar):
            return True
        return bool(getattr(obj, "inherits", lambda *_: False)("QTabBar"))

    def eventFilter(self, obj, event):
        if self._is_dock_tabbar(obj):
            parent = obj.parent()
            dock_related = False
            while parent is not None:
                meta = getattr(parent, "metaObject", None)
                if callable(meta) and "Dock" in meta().className():
                    dock_related = True
                    break
                parent = parent.parent()
            if dock_related and event.type() in (
                QEvent.Type.Show,
                QEvent.Type.ShowToParent,
                QEvent.Type.Resize,
                QEvent.Type.Paint,
                QEvent.Type.Enter,
            ):
                obj.setMaximumHeight(0)
                obj.setMinimumHeight(0)
                obj.hide()
                obj.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
                return True
        return super().eventFilter(obj, event)


# Import our existing strategy code
import strategy
import yfinance as yf
import numpy as np


BASE_RADIUS = 12
BASE_SPACING = 12
TOUCH_TARGET = 44

THEMES = {
    "dark": {
        "window_bg": "#05070B",
        "panel_bg": "#0C111B",
        "surface": "#111726",
        "surface_alt": "#1B2234",
        "border": "#20283D",
        "divider": "#252F45",
        "divider_subtle": "#161C2B",
        "text": "#F5F7FF",
        "muted": "#A1A8C3",
        "accent": "#F9E09A",
        "accent_hover": "#FFE8B5",
        "button_text": "#111318",
        "button_hover_text": "#05070B",
        "input_bg": "#0F1522",
        "tab_bg": "#0A0F18",
        "tab_text": "#F5F7FF",
        "chart_theme": "dark",
        "chart_bg": "#060910",
        "chart_toolbar": "#0D1421",
        "chip_bg": "#151C2C",
        "chip_text": "#D5DCF2",
        "positive": "#4ADE80",
        "negative": "#F87171",
        "hero_top": "#161F32",
        "hero_bottom": "#080B12"
    },
    "light": {
        "window_bg": "#F5F6FA",
        "panel_bg": "#FFFFFF",
        "surface": "#FFFFFF",
        "surface_alt": "#F2F4FA",
        "border": "#E1E5EE",
        "divider": "#E3E7F2",
        "divider_subtle": "#ECEFF6",
        "text": "#14151A",
        "muted": "#5F6578",
        "accent": "#14151A",
        "accent_hover": "#2F3747",
        "button_text": "#F8F9FF",
        "button_hover_text": "#F5F7FF",
        "input_bg": "#F8F9FF",
        "tab_bg": "#14151A",
        "tab_text": "#F8F9FF",
        "chart_theme": "light",
        "chart_bg": "#FFFFFF",
        "chart_toolbar": "#F4F5FB",
        "chip_bg": "#EEF1F8",
        "chip_text": "#3A3F52",
        "positive": "#10B981",
        "negative": "#DC2626",
        "hero_top": "#FFFFFF",
        "hero_bottom": "#EDEFF6"
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

CURRENCY_SYMBOLS = {
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "JPY": "¥",
    "CNY": "¥",
    "CAD": "$",
    "AUD": "$",
    "CHF": "CHF",
}


def compute_market_status(fast_info: dict | None, info: dict | None) -> str:
    fast_info = fast_info or {}
    info = info or {}
    state = (fast_info.get("market_state") or fast_info.get("marketState") or
             info.get("marketState") or "Live data")
    state = str(state).replace("_", " ").strip()
    return state.title() or "Live Data"


def build_snapshot(ticker: str, fast_info: dict | None = None, info: dict | None = None) -> dict:
    fast_info = fast_info or {}
    info = info or {}
    snapshot = {"symbol": ticker.upper()}

    price = (fast_info.get("last_price") or fast_info.get("lastPrice") or
             fast_info.get("lastSalePrice") or info.get("regularMarketPrice") or
             info.get("currentPrice"))
    prev_close = (fast_info.get("previous_close") or fast_info.get("previousClose") or
                  info.get("previousClose"))
    open_price = (fast_info.get("open") or fast_info.get("regularMarketOpen") or
                  info.get("open"))
    day_high = (fast_info.get("day_high") or fast_info.get("dayHigh") or
                info.get("dayHigh") or info.get("regularMarketDayHigh"))
    day_low = (fast_info.get("day_low") or fast_info.get("dayLow") or
               info.get("dayLow") or info.get("regularMarketDayLow"))
    avg_volume = (fast_info.get("tenDayAverageVolume") or fast_info.get("avgVolume") or
                  info.get("averageVolume10days") or info.get("averageDailyVolume10Day") or
                  info.get("averageVolume"))
    market_cap = info.get("marketCap")
    shares_outstanding = info.get("sharesOutstanding") or info.get("floatShares")
    pe_ratio = info.get("trailingPE") or info.get("forwardPE")
    dividend_yield = info.get("dividendYield")
    currency = (info.get("currency") or info.get("financialCurrency") or "USD").upper()
    exchange = (info.get("fullExchangeName") or info.get("exchange") or info.get("market") or
                info.get("quoteType") or "Global").upper()
    pre_price = (fast_info.get("pre_market_price") or fast_info.get("preMarketPrice") or
                 info.get("preMarketPrice"))
    pre_time = fast_info.get("preMarketTime") or info.get("preMarketTime")
    pre_change = None
    pre_change_pct = None
    if pre_price is not None and prev_close:
        pre_change = pre_price - prev_close
        pre_change_pct = (pre_change / prev_close) * 100 if prev_close else None
    if pre_time:
        try:
            pre_time = datetime.fromtimestamp(float(pre_time)).strftime("%b %d - %H:%M")
        except Exception:
            pre_time = str(pre_time)

    if price is not None and prev_close is not None:
        change = price - prev_close
        change_pct = (change / prev_close) * 100 if prev_close else None
    else:
        change = None
        change_pct = None

    volume = fast_info.get("volume") or info.get("volume") or info.get("averageVolume")
    high_52 = fast_info.get("yearHigh") or info.get("fiftyTwoWeekHigh")
    low_52 = fast_info.get("yearLow") or info.get("fiftyTwoWeekLow")

    snapshot.update({
        "name": info.get("shortName") or info.get("longName") or ticker.upper(),
        "price": price,
        "change": change,
        "change_pct": change_pct,
        "volume": volume,
        "volume_label": "Session volume" if fast_info.get("volume") else "Avg volume",
        "time": datetime.now().strftime("%b %d - %H:%M"),
        "status": compute_market_status(fast_info, info),
        "currency": currency,
        "exchange": exchange,
        "open": open_price,
        "day_high": day_high,
        "day_low": day_low,
        "prev_close": prev_close,
        "avg_volume": avg_volume,
        "market_cap": market_cap,
        "shares_outstanding": shares_outstanding,
        "pe_ratio": pe_ratio,
        "dividend_yield": dividend_yield,
        "pre_price": pre_price,
        "pre_change": pre_change,
        "pre_change_pct": pre_change_pct,
        "pre_status": "Pre",
        "pre_time": pre_time,
    })

    if high_52 and low_52:
        snapshot["range"] = f"${low_52:,.0f} - ${high_52:,.0f}"
        snapshot["range_label"] = "52W range"
        snapshot["fifty_two_week_low"] = low_52
        snapshot["fifty_two_week_high"] = high_52
    else:
        snapshot["range"] = None
        snapshot["fifty_two_week_low"] = low_52
        snapshot["fifty_two_week_high"] = high_52

    return snapshot


class TickerDataCache:
    """Lightweight TTL cache for expensive yfinance calls."""

    def __init__(self, ttl_seconds: int = 180):
        self.ttl = timedelta(seconds=ttl_seconds)
        self.cache: dict[str, dict[str, Any]] = {}

    def _key(self, ticker: str) -> str:
        return (ticker or "").upper()

    def peek(self, ticker: str) -> dict[str, Any] | None:
        key = self._key(ticker)
        entry = self.cache.get(key)
        if entry and datetime.utcnow() - entry["timestamp"] < self.ttl:
            return entry["payload"]
        return None

    def refresh(self, ticker: str) -> dict[str, Any]:
        key = self._key(ticker)
        payload = self._fetch_remote_data(key)
        self.cache[key] = {"timestamp": datetime.utcnow(), "payload": payload}
        return payload

    def _fetch_remote_data(self, ticker: str) -> dict[str, Any]:
        try:
            stock = yf.Ticker(ticker)
            fast_info = getattr(stock, "fast_info", {}) or {}
            try:
                info = stock.info or {}
            except Exception:
                info = {}
            try:
                news = list(getattr(stock, "news", []) or [])
            except Exception:
                news = []
        except Exception as exc:
            fast_info = {}
            info = {"shortName": ticker.upper()}
            news = []
            fallback_snapshot = {
                "symbol": ticker.upper(),
                "status": "Data issue",
                "error": str(exc),
                "name": ticker.upper(),
                "price": None,
                "change": None,
                "change_pct": None,
                "volume": None,
                "volume_label": "",
                "time": datetime.now().strftime("%b %d - %H:%M"),
                "range": None,
            }
            return {
                "ticker": ticker,
                "fast_info": fast_info,
                "info": info,
                "news": news,
                "snapshot": fallback_snapshot,
                "fetched_at": datetime.utcnow().isoformat()
            }
        snapshot = build_snapshot(ticker, fast_info, info)
        return {
            "ticker": ticker,
            "fast_info": fast_info,
            "info": info,
            "news": news,
            "snapshot": snapshot,
            "fetched_at": datetime.utcnow().isoformat()
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
    """Dock widget with custom title bar controls (minimize, float, close)."""

    closed = pyqtSignal(str)
    collapsed_changed = pyqtSignal(str, bool)

    def __init__(self, key: str, widget: QWidget, content_widget: QWidget | None, parent: QMainWindow,
                 link_callback: Callable[[str, int | None], None] | None = None):
        super().__init__(key, parent)
        self.key = key
        self.setWidget(widget)
        self.setObjectName(f"Dock_{key}")
        self.setContentsMargins(0, 0, 0, 0)
        self.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetClosable |
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.collapsed = False
        self._collapsed_height = 48
        self._base_title = self.windowTitle()
        self.link_callback = link_callback
        self._content_widget = content_widget
        self._init_title_bar()

    def _init_title_bar(self):
        title_bar = QWidget()
        title_bar.setObjectName("DockTitleBar")
        layout = QHBoxLayout(title_bar)
        layout.setContentsMargins(12, 6, 8, 6)
        layout.setSpacing(6)

        self.tab_strip = QWidget()
        self.tab_strip.setObjectName("DockTabStrip")
        self.tab_strip.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.tab_strip_layout = QHBoxLayout(self.tab_strip)
        self.tab_strip_layout.setContentsMargins(0, 0, 0, 0)
        self.tab_strip_layout.setSpacing(6)
        self.tab_strip.hide()

        layout.addWidget(self.tab_strip, stretch=1)

        self.min_btn = self._create_icon_button("icons/minimize.svg", self.toggle_collapsed, "Minimize")
        self.expand_btn = self._create_icon_button("icons/expand.svg", self.expand_to_fill, "Expand to fit space")
        self.float_btn = self._create_icon_button("icons/float.svg", self._toggle_floating, "Float / Dock")
        self.close_btn = self._create_icon_button("icons/close.svg", self.close, "Close")

        for btn in (self.min_btn, self.expand_btn, self.float_btn, self.close_btn):
            layout.addWidget(btn)

        self.setTitleBarWidget(title_bar)
        self._title_bar_widget = title_bar
        title_bar.installEventFilter(self)
        self._sync_tab_state()

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
        self.collapsed_changed.emit(self.key, self.collapsed)

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
        self.closed.emit(self.key)
        super().closeEvent(event)

    def setWindowTitle(self, title: str):
        super().setWindowTitle(title)
        self._base_title = title
        self._refresh_cluster_tabs()

    def eventFilter(self, obj, event):
        if obj is getattr(self, "_title_bar_widget", None):
            if event.type() == QEvent.Type.MouseButtonDblClick and event.button() == Qt.MouseButton.LeftButton:
                self.show_link_menu()
                return True
            if event.type() in (QEvent.Type.MouseButtonPress,
                                QEvent.Type.MouseButtonRelease,
                                QEvent.Type.MouseMove):
                QApplication.sendEvent(self, event)
                return True
        return super().eventFilter(obj, event)

    def event(self, event):
        watched = [
            QEvent.Type.ParentChange,
            QEvent.Type.ShowToParent,
            QEvent.Type.ZOrderChange,
            QEvent.Type.LayoutRequest,
        ]
        dock_change = getattr(QEvent.Type, "DockWidgetAreaChange", None)
        if dock_change:
            watched.append(dock_change)
        if event.type() in watched:
            QTimer.singleShot(0, self._sync_tab_state)
        return super().event(event)

    def set_link_group_display(self, group: int | None):
        self._link_group = group
        self._refresh_cluster_tabs()

    def show_link_menu(self):
        if not self.link_callback:
            return
        menu = QMenu(self)
        none_action = menu.addAction("No Link")
        none_action.triggered.connect(lambda: self.link_callback(self.key, None))
        menu.addSeparator()
        for group in range(1, 7):
            action = menu.addAction(f"Group {group}")
            action.triggered.connect(lambda checked=False, g=group: self.link_callback(self.key, g))
        anchor = self.tab_strip if self.tab_strip.isVisible() else self._title_bar_widget
        menu.exec(anchor.mapToGlobal(anchor.rect().bottomLeft()))

    def _is_tabbed(self) -> bool:
        parent = self.parentWidget()
        while parent:
            if parent.metaObject().className().startswith("QDockWidgetGroupWindow"):
                return True
            parent = parent.parentWidget()
        return False

    def _sync_tab_state(self):
        tabbed = self._is_tabbed()
        if getattr(self, "_title_bar_widget", None):
            self._title_bar_widget.setProperty("tabbed", tabbed)
            self._title_bar_widget.style().unpolish(self._title_bar_widget)
            self._title_bar_widget.style().polish(self._title_bar_widget)
        self._refresh_cluster_tabs()
        if getattr(self, "_content_widget", None) and hasattr(self._content_widget, "set_tab_mode"):
            self._content_widget.set_tab_mode(tabbed)

    def _clear_tab_strip(self):
        if not hasattr(self, "tab_strip_layout"):
            return
        while self.tab_strip_layout.count():
            item = self.tab_strip_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _display_title(self) -> str:
        title = self._base_title
        if getattr(self, "_link_group", None):
            title = f"{title} · #{self._link_group}"
        return title

    def _main_window(self):
        parent = self.parent()
        while parent and not isinstance(parent, QMainWindow):
            parent = parent.parent()
        return parent if isinstance(parent, QMainWindow) else None

    def _hide_native_tab_bars(self):
        container = self._tab_container_widget()
        if not container:
            return
        visited = set()
        for tabbar in container.findChildren(QTabBar):
            if tabbar in visited:
                continue
            visited.add(tabbar)
            if self._tabbar_belongs_to_dock_content(tabbar):
                continue
            tabbar.setVisible(False)
            tabbar.setMaximumHeight(0)
            tabbar.setMinimumHeight(0)
            tabbar.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def _tab_container_widget(self) -> QWidget | None:
        container = self.parentWidget()
        while container:
            if container.metaObject().className().startswith("QDockWidgetGroupWindow"):
                return container
            container = container.parentWidget()
        return None

    def _tabbar_belongs_to_dock_content(self, tabbar: QTabBar) -> bool:
        ancestor = tabbar.parentWidget()
        while ancestor:
            if isinstance(ancestor, QDockWidget):
                return True
            ancestor = ancestor.parentWidget()
        return False

    def _collect_tab_cluster(self) -> list["WorkspaceDock"]:
        main = self._main_window()
        if not main:
            return [self]
        cluster = [self]
        for dock in main.tabifiedDockWidgets(self):
            if isinstance(dock, WorkspaceDock):
                cluster.append(dock)
        ordered: list[WorkspaceDock] = []
        for dock in cluster:
            if dock not in ordered:
                ordered.append(dock)
        return ordered

    def _refresh_cluster_tabs(self):
        if not hasattr(self, "tab_strip"):
            return
        cluster = self._collect_tab_cluster()
        tabbed = len(cluster) > 1
        if tabbed:
            self._hide_native_tab_bars()
        active = next((dock for dock in cluster if dock.isVisible()), cluster[0])
        for dock in cluster:
            dock._apply_tab_ui(cluster, active, tabbed)

    def _apply_tab_ui(self, cluster: list["WorkspaceDock"], active: "WorkspaceDock", tabbed: bool):
        if not hasattr(self, "tab_strip"):
            return
        self.tab_strip.show()
        self._clear_tab_strip()
        multi = len(cluster) > 1
        for dock in cluster:
            btn = QToolButton()
            btn.setObjectName("DockTabButton")
            btn.setText(dock._display_title())
            btn.setProperty("solo", not multi)
            if multi:
                btn.setCheckable(True)
                btn.setChecked(dock is active)
                btn.clicked.connect(partial(self._activate_tab, dock))
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
            else:
                btn.setCheckable(False)
                btn.setCursor(Qt.CursorShape.ArrowCursor)
                btn.setEnabled(False)
            self.tab_strip_layout.addWidget(btn)
        self.tab_strip_layout.addStretch()

    def _activate_tab(self, target: "WorkspaceDock"):
        if not target:
            return
        target.raise_()
        target.show()
        target.activateWindow()


class QuoteMetricCell(QFrame):
    """Compact textual metric row for the quote header grid."""

    def __init__(self, label: str):
        super().__init__()
        self.setObjectName("QuoteMetric")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self.label = QLabel(label.upper())
        self.label.setObjectName("QuoteMetricLabel")
        self.value = QLabel("--")
        self.value.setObjectName("QuoteMetricValue")
        self.hint = QLabel("")
        self.hint.setObjectName("QuoteMetricHint")

        layout.addWidget(self.label)
        layout.addWidget(self.value)
        layout.addWidget(self.hint)

    def set_value(self, text: str | None):
        self.value.setText(text or "--")

    def set_hint(self, text: str | None):
        self.hint.setText(text or "")

    def set_label(self, text: str):
        self.label.setText(text.upper())


class HeroMicroPanel(QFrame):
    """Small contextual card used alongside the hero quote widget."""

    def __init__(self, title: str, caption: str):
        super().__init__()
        self.setObjectName("HeroMicroPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        self.title = QLabel(title.upper())
        self.title.setObjectName("MicroTitle")
        self.primary = QLabel("--")
        self.primary.setObjectName("MicroPrimary")
        self.meta = QLabel(caption)
        self.meta.setObjectName("MicroMeta")

        layout.addWidget(self.title)
        layout.addWidget(self.primary)
        layout.addWidget(self.meta)

    def set_primary(self, text: str):
        self.primary.setText(text or "--")

    def set_meta(self, text: str):
        self.meta.setText(text or "")

    def set_title(self, text: str):
        self.title.setText(text.upper())


class QuoteWidget(QFrame):
    """Headline card showcasing the active ticker in a Webull-inspired layout."""

    INTERVAL_OPTIONS = [
        ("1m", "1"),
        ("5m", "5"),
        ("15m", "15"),
        ("1h", "60"),
        ("4h", "240"),
        ("1D", "D"),
    ]

    def __init__(self, interval_callback):
        super().__init__()
        self.interval_callback = interval_callback
        self.setObjectName("QuoteCard")
        self.active_interval = None
        self.currency = "USD"
        self.brand_color = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(BASE_SPACING)

        self.header_frame = QFrame()
        self.header_frame.setObjectName("ModuleHeader")
        header_layout = QHBoxLayout(self.header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(16)

        title_stack = QVBoxLayout()
        title_stack.setSpacing(6)

        self.symbol_label = QLabel("--")
        self.symbol_label.setObjectName("QuoteSymbol")
        self.company_label = QLabel("Pick a ticker from the watchlist to get started.")
        self.company_label.setObjectName("QuoteCompany")

        meta_row = QHBoxLayout()
        meta_row.setSpacing(8)
        self.exchange_badge = QLabel("—")
        self.exchange_badge.setObjectName("QuoteExchange")
        self.session_badge = QLabel("STATUS")
        self.session_badge.setObjectName("QuoteSession")
        self.timestamp_label = QLabel("--")
        self.timestamp_label.setObjectName("QuoteTimestamp")
        meta_row.addWidget(self.exchange_badge)
        meta_row.addWidget(self.session_badge)
        meta_row.addWidget(self.timestamp_label)
        meta_row.addStretch()

        title_stack.addWidget(self.symbol_label)
        title_stack.addWidget(self.company_label)
        title_stack.addLayout(meta_row)

        header_layout.addLayout(title_stack, stretch=1)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        self.watch_button = self._build_action_button("★ Watch", "Add to watch bucket")
        self.alert_button = self._build_action_button("⏰ Alert", "Set price alert (coming soon)")
        actions.addWidget(self.watch_button)
        actions.addWidget(self.alert_button)
        header_layout.addLayout(actions, stretch=0)

        layout.addWidget(self.header_frame)

        price_row = QHBoxLayout()
        price_row.setSpacing(BASE_SPACING)

        price_stack = QVBoxLayout()
        price_stack.setSpacing(4)
        main_price = QHBoxLayout()
        main_price.setSpacing(12)
        self.price_label = QLabel("--")
        self.price_label.setObjectName("QuotePrice")
        self.change_label = QLabel("--")
        self.change_label.setObjectName("QuoteChange")
        self.change_pct_label = QLabel("--")
        self.change_pct_label.setObjectName("QuoteChangePct")
        main_price.addWidget(self.price_label)
        main_price.addWidget(self.change_label)
        main_price.addWidget(self.change_pct_label)
        main_price.addStretch()
        price_stack.addLayout(main_price)

        self.premarket_label = QLabel("Pre: --")
        self.premarket_label.setObjectName("QuotePremarket")
        price_stack.addWidget(self.premarket_label)

        price_row.addLayout(price_stack, stretch=2)

        self.interval_frame = QFrame()
        self.interval_frame.setObjectName("IntervalSelector")
        interval_layout = QHBoxLayout(self.interval_frame)
        interval_layout.setContentsMargins(0, 0, 0, 0)
        interval_layout.setSpacing(6)
        self.interval_buttons: dict[str, QPushButton] = {}
        for label, code in self.INTERVAL_OPTIONS:
            btn = QPushButton(label)
            btn.setObjectName("TimeframeButton")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked=False, value=code: self._on_interval_clicked(value))
            interval_layout.addWidget(btn)
            self.interval_buttons[code] = btn
        price_row.addWidget(self.interval_frame, stretch=0)

        layout.addLayout(price_row)

        metrics_frame = QFrame()
        metrics_frame.setObjectName("QuoteMetricGrid")
        metrics_layout = QGridLayout(metrics_frame)
        metrics_layout.setContentsMargins(0, 8, 0, 0)
        metrics_layout.setHorizontalSpacing(32)
        metrics_layout.setVerticalSpacing(10)

        metric_definitions = [
            ("open", "Open"),
            ("day_high", "Day High"),
            ("day_low", "Day Low"),
            ("prev_close", "Prev Close"),
            ("volume", "Volume"),
            ("avg_volume", "Avg Vol"),
            ("market_cap", "Market Cap"),
            ("pe_ratio", "P/E"),
            ("fifty_two_week_high", "52W High"),
            ("fifty_two_week_low", "52W Low"),
            ("dividend_yield", "Dividend"),
            ("shares_outstanding", "Shares Out"),
        ]
        self.metric_cells: dict[str, QuoteMetricCell] = {}
        for idx, (key, label) in enumerate(metric_definitions):
            cell = QuoteMetricCell(label)
            row = idx // 4
            col = idx % 4
            metrics_layout.addWidget(cell, row, col)
            self.metric_cells[key] = cell
        layout.addWidget(metrics_frame)

        micro_row = QHBoxLayout()
        micro_row.setSpacing(BASE_SPACING)
        self.filing_panel = HeroMicroPanel("Latest Filing", "Awaiting SEC feed")
        self.event_panel = HeroMicroPanel("Next Event", "Macro calendar humming")
        micro_row.addWidget(self.filing_panel)
        micro_row.addWidget(self.event_panel)
        layout.addLayout(micro_row)

        self.set_active_interval("60")
        self.show_loading("--")

    def _build_action_button(self, label: str, tooltip: str) -> QToolButton:
        btn = QToolButton()
        btn.setObjectName("UtilityButton")
        btn.setText(label)
        btn.setToolTip(tooltip)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setAutoRaise(False)
        btn.setCheckable(False)
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        return btn

    def _on_interval_clicked(self, interval: str):
        self.set_active_interval(interval)
        if self.interval_callback:
            self.interval_callback(interval)

    def _set_trend(self, widgets: list[QWidget], trend: str | None):
        for widget in widgets:
            widget.setProperty("trend", trend or "")
            widget.style().unpolish(widget)
            widget.style().polish(widget)

    def _format_currency(self, value: Any, decimals: int = 2) -> str:
        if value is None:
            return "--"
        try:
            amount = f"{float(value):,.{decimals}f}"
        except (TypeError, ValueError):
            return "--"
        symbol = CURRENCY_SYMBOLS.get(self.currency.upper(), self.currency.upper())
        if len(symbol) == 1 and not symbol.isalpha():
            return f"{symbol}{amount}"
        if len(symbol) == 1:
            return f"{symbol}{amount}"
        return f"{symbol} {amount}"

    def _format_number(self, value: Any, decimals: int = 2) -> str:
        try:
            return f"{float(value):,.{decimals}f}"
        except (TypeError, ValueError):
            return "--"

    def _format_compact(self, value: Any) -> str:
        try:
            num = float(value)
        except (TypeError, ValueError):
            return "--"
        for suffix, threshold in (("T", 1e12), ("B", 1e9), ("M", 1e6), ("K", 1e3)):
            if abs(num) >= threshold:
                return f"{num / threshold:.2f}{suffix}"
        return f"{num:,.0f}"

    def _set_metric(self, key: str, value: Any, formatter: Callable[[Any], str] | None = None,
                    hint: str | None = None):
        cell = self.metric_cells.get(key)
        if not cell:
            return
        if value is None:
            cell.set_value("--")
            cell.set_hint("")
            return
        if formatter:
            try:
                text = formatter(value)
            except Exception:
                text = str(value)
        else:
            text = str(value)
        cell.set_value(text or "--")
        cell.set_hint(hint or "")

    def apply_brand_color(self, color: str | None):
        self.brand_color = color
        if color:
            text_color = ideal_text_color(color)
            self.session_badge.setStyleSheet(
                f"background-color: {color}; color: {text_color}; padding: 4px 14px; "
                f"border-radius: 999px; border: 1px solid {color};"
            )
            self.filing_panel.setStyleSheet(f"QFrame#HeroMicroPanel{{ border: 1px solid {color}; }}")
            self.event_panel.setStyleSheet(f"QFrame#HeroMicroPanel{{ border: 1px solid {color}; }}")
        else:
            self.session_badge.setStyleSheet("")
            self.filing_panel.setStyleSheet("")
            self.event_panel.setStyleSheet("")

    def show_loading(self, ticker: str):
        display = (ticker or "--").upper()
        self.apply_brand_color(None)
        self.symbol_label.setText(display)
        self.company_label.setText("Fetching live data...")
        self.exchange_badge.setText("—")
        self.session_badge.setText("LOADING")
        self.timestamp_label.setText("--:--")
        self.price_label.setText("--")
        self.change_label.setText("--")
        self.change_pct_label.setText("--")
        self.premarket_label.setText("Pre: --")
        self._set_trend([self.change_label, self.change_pct_label, self.premarket_label], "")
        for cell in self.metric_cells.values():
            cell.set_value("--")
            cell.set_hint("")
        self.filing_panel.set_primary("Loading...")
        self.filing_panel.set_meta("")
        self.event_panel.set_primary("Loading...")
        self.event_panel.set_meta("")

    def set_active_interval(self, interval: str):
        self.active_interval = interval
        for code, button in self.interval_buttons.items():
            button.setChecked(code == interval)

    def set_tab_mode(self, tabbed: bool):
        if hasattr(self, "header_frame"):
            self.header_frame.setVisible(not tabbed)

    def update_snapshot(self, snapshot: dict):
        symbol = snapshot.get("symbol") or "--"
        name = snapshot.get("name") or "Awaiting selection"
        price = snapshot.get("price")
        change = snapshot.get("change")
        change_pct = snapshot.get("change_pct")
        volume = snapshot.get("volume")
        status = snapshot.get("status") or "Live"
        currency = (snapshot.get("currency") or "USD").upper()

        self.currency = currency
        self.symbol_label.setText(symbol)
        self.company_label.setText(name)
        exchange = snapshot.get("exchange") or "Global"
        self.exchange_badge.setText(exchange.upper())
        self.session_badge.setText(self._format_status(status))
        self.timestamp_label.setText(snapshot.get("time") or "--")

        if price is not None:
            self.price_label.setText(self._format_currency(price))
        else:
            self.price_label.setText("--")

        if change is not None and change_pct is not None:
            sign = "+" if change >= 0 else "-"
            self.change_label.setText(f"{sign}{self._format_number(abs(change), 2)}")
            self.change_pct_label.setText(f"{sign}{abs(change_pct):.2f}%")
            trend = "positive" if change >= 0 else "negative"
            self._set_trend([self.change_label, self.change_pct_label], trend)
        else:
            self.change_label.setText("--")
            self.change_pct_label.setText("--")
            self._set_trend([self.change_label, self.change_pct_label], "")

        pre_price = snapshot.get("pre_price")
        pre_change = snapshot.get("pre_change")
        pre_change_pct = snapshot.get("pre_change_pct")
        pre_label = snapshot.get("pre_status") or "Pre"
        if pre_price is not None and pre_change is not None and pre_change_pct is not None:
            sign = "+" if pre_change >= 0 else "-"
            label = (
                f"{pre_label}: {self._format_currency(pre_price)} "
                f"{sign}{self._format_number(abs(pre_change), 2)} "
                f"({sign}{abs(pre_change_pct):.2f}%)"
            )
            if snapshot.get("pre_time"):
                label += f" • {snapshot['pre_time']}"
            self.premarket_label.setText(label)
            self._set_trend([self.premarket_label], "positive" if pre_change >= 0 else "negative")
        else:
            self.premarket_label.setText("Pre: --")
            self._set_trend([self.premarket_label], "")

        self._set_metric("open", snapshot.get("open"), lambda v: self._format_currency(v))
        self._set_metric("day_high", snapshot.get("day_high"), lambda v: self._format_currency(v))
        self._set_metric("day_low", snapshot.get("day_low"), lambda v: self._format_currency(v))
        self._set_metric("prev_close", snapshot.get("prev_close"), lambda v: self._format_currency(v))
        self._set_metric("volume", volume, self._format_compact, snapshot.get("volume_label", "Volume"))
        self._set_metric("avg_volume", snapshot.get("avg_volume"), self._format_compact, "Avg 10D")
        self._set_metric("market_cap", snapshot.get("market_cap"), self._format_compact)
        self._set_metric("pe_ratio", snapshot.get("pe_ratio"), lambda v: self._format_number(v, 2))
        self._set_metric(
            "fifty_two_week_high",
            snapshot.get("fifty_two_week_high"),
            lambda v: self._format_currency(v),
        )
        self._set_metric(
            "fifty_two_week_low",
            snapshot.get("fifty_two_week_low"),
            lambda v: self._format_currency(v),
        )
        self._set_metric(
            "dividend_yield",
            snapshot.get("dividend_yield"),
            lambda v: f"{float(v) * 100:.2f}%",
        )
        self._set_metric("shares_outstanding", snapshot.get("shares_outstanding"), self._format_compact)

        self._update_context_cards(symbol)

    def _format_status(self, raw_status: str) -> str:
        status = (raw_status or "").strip().lower().replace("_", " ")
        if status.startswith("pre"):
            return "PRE"
        if status.startswith("post") or status.startswith("after"):
            return "POST"
        if status.startswith("live") or status.startswith("regular"):
            return "OPEN"
        if status.startswith("close"):
            return "CLOSED"
        return (raw_status or "--").upper()

    def _update_context_cards(self, ticker: str):
        now = datetime.now()
        filing_title = f"{ticker} 10-Q draft" if ticker not in ("--", "") else "Awaiting selection"
        filing_meta = f"Mock summary • {now.strftime('%b %d, %I:%M %p')}"
        event_title = "CPI (USD)" if ticker not in ("--", "") else "Macro outlook"
        event_meta = "Est. release in 02h 10m"
        self.set_latest_filing(filing_title, filing_meta)
        self.set_next_event(event_title, event_meta)

    def set_latest_filing(self, title: str | None, meta: str | None):
        self.filing_panel.set_primary(title or "No filings queued")
        self.filing_panel.set_meta(meta or "EDGAR feed pending")

    def set_next_event(self, title: str | None, meta: str | None):
        self.event_panel.set_primary(title or "No macro events")
        self.event_panel.set_meta(meta or "All clear")


class MarketPulseWidget(QFrame):
    """Combined market clock + session pulse chip for the header."""

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
        self.setObjectName("MarketPulse")
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 12, 18, 12)
        layout.setSpacing(16)

        left_col = QVBoxLayout()
        left_col.setSpacing(4)
        status_row = QHBoxLayout()
        status_row.setSpacing(6)
        self.status_chip = QLabel("PRE")
        self.status_chip.setObjectName("PulseStatus")
        self.market_label = QLabel("NYSE · America/New_York")
        self.market_label.setObjectName("PulseMeta")
        status_row.addWidget(self.status_chip)
        status_row.addWidget(self.market_label)
        status_row.addStretch()
        left_col.addLayout(status_row)

        self.transition_label = QLabel("Opens in --:--:--")
        self.transition_label.setObjectName("PulseMeta")
        left_col.addWidget(self.transition_label)

        layout.addLayout(left_col)

        clock_col = QVBoxLayout()
        clock_col.setSpacing(2)
        self.clock_label = QLabel("--:--:--")
        self.clock_label.setObjectName("PulseClock")
        self.date_label = QLabel("-- ---")
        self.date_label.setObjectName("PulseMeta")
        clock_col.addWidget(self.clock_label)
        clock_col.addWidget(self.date_label)
        layout.addLayout(clock_col)

        self.selector = QComboBox()
        self.selector.setObjectName("PulseSelector")
        for name in self.MARKETS:
            self.selector.addItem(name)
        self.selector.currentIndexChanged.connect(self.update_pulse)
        layout.addWidget(self.selector)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_pulse)
        self.timer.start(1_000)
        self.update_pulse()

    def update_pulse(self):
        market_name = self.selector.currentText()
        market = self.MARKETS[market_name]
        tz = ZoneInfo(market["tz"])
        now = datetime.now(tz)
        status, meta = self._determine_status(now, market)
        self.status_chip.setText(status.upper())
        self.market_label.setText(f"{market_name.split('(')[0].strip()} · {market['tz']}")
        self.transition_label.setText(meta)
        self.clock_label.setText(now.strftime("%H:%M:%S"))
        self.date_label.setText(now.strftime("%b %d"))

    def _determine_status(self, now: datetime, market: dict) -> tuple[str, str]:
        open_dt = now.replace(hour=market["open"].hour, minute=market["open"].minute,
                              second=0, microsecond=0)
        close_dt = now.replace(hour=market["close"].hour, minute=market["close"].minute,
                               second=0, microsecond=0)
        pre_start = open_dt - market["pre"]
        after_end = close_dt + market["after"]

        if pre_start <= now < open_dt:
            return "pre", f"Opens in {self._format_delta(open_dt - now)}"
        if open_dt <= now <= close_dt:
            return "open", f"Closes in {self._format_delta(close_dt - now)}"
        if close_dt < now <= after_end:
            return "post", f"After-hours ends in {self._format_delta(after_end - now)}"

        if now < pre_start:
            return "closed", f"Next session in {self._format_delta(pre_start - now)}"
        # rolled into next day
        return "closed", f"Next session in {self._format_delta((pre_start + timedelta(days=1)) - now)}"

    def _format_delta(self, delta: timedelta) -> str:
        total_seconds = max(int(delta.total_seconds()), 0)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

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

    def __init__(self):
        super().__init__()
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
        self._show_placeholder("Pick a ticker to load fundamentals.")

    def load_ticker(self, ticker: str, payload: dict | None = None):
        if not payload or not payload.get("info"):
            self._show_placeholder("Loading fundamentals...")
            return
        info = payload.get("info") or {}
        dividend_yield = info.get("dividendYield")
        metrics = [
            ("Market Cap", self._format_number(info.get("marketCap"), dollar=True)),
            ("P/E Ratio", self._format_number(info.get("trailingPE"))),
            ("Forward P/E", self._format_number(info.get("forwardPE"))),
            ("EPS", self._format_number(info.get("trailingEps"), dollar=True)),
            ("Dividend Yield", f"{dividend_yield * 100:.2f}%" if dividend_yield else "N/A"),
            ("52 Week High", self._format_number(info.get("fiftyTwoWeekHigh"), dollar=True)),
            ("52 Week Low", self._format_number(info.get("fiftyTwoWeekLow"), dollar=True)),
            ("Volume (Avg)", self._format_number(info.get("averageVolume"))),
            ("Beta", self._format_number(info.get("beta"))),
        ]
        self.table.setRowCount(len(metrics))
        for row, (metric, value) in enumerate(metrics):
            self.table.setItem(row, 0, QTableWidgetItem(str(metric)))
            self.table.setItem(row, 1, QTableWidgetItem(str(value)))

    def _show_placeholder(self, message: str):
        self.table.setRowCount(1)
        self.table.setItem(0, 0, QTableWidgetItem("Status"))
        self.table.setItem(0, 1, QTableWidgetItem(message))

    def _format_number(self, value: Any, dollar: bool = False) -> str:
        if value in (None, "N/A"):
            return "N/A"
        try:
            num = float(value)
        except (TypeError, ValueError):
            return str(value)
        suffixes = [(1_000_000_000_000, "T"), (1_000_000_000, "B"), (1_000_000, "M")]
        for threshold, suffix in suffixes:
            if abs(num) >= threshold:
                formatted = f"{num / threshold:.2f}{suffix}"
                return f"${formatted}" if dollar else formatted
        if dollar:
            return f"${num:,.2f}"
        return f"{num:,.2f}"

    def set_tab_mode(self, tabbed: bool):
        if hasattr(self, "header_frame"):
            self.header_frame.setVisible(not tabbed)


class NewsWidget(QWidget):
    """Standalone news list widget."""

    def __init__(self):
        super().__init__()
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
        self.news_list.addItem("Pick a ticker to load news.")

    def load_ticker(self, ticker: str, payload: dict | None = None):
        self.news_list.clear()
        if not payload:
            self.news_list.addItem("Loading headlines...")
            return
        news_items = list(payload.get("news") or [])[:12]
        if not news_items:
            self.news_list.addItem("No recent news.")
            return
        for item in news_items:
            title = item.get("title", "No title")
            timestamp = item.get("providerPublishTime")
            badge = self._format_timestamp(timestamp)
            source = item.get("source") or item.get("provider", {}).get("name", "")
            meta = f"{badge} · {source}".strip(" ·")
            self.news_list.addItem(f"[{meta}] {title}")

    def _format_timestamp(self, timestamp: Any) -> str:
        try:
            ts = float(timestamp)
        except (TypeError, ValueError):
            return "--"
        return datetime.fromtimestamp(ts).strftime("%b %d")

    def set_tab_mode(self, tabbed: bool):
        if hasattr(self, "header_frame"):
            self.header_frame.setVisible(not tabbed)


class SecFilingsWidget(QWidget):
    """Placeholder SEC filings console with mock data."""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(BASE_SPACING, BASE_SPACING, BASE_SPACING, BASE_SPACING)
        layout.setSpacing(BASE_SPACING)

        self.header_frame = QFrame()
        header_layout = QVBoxLayout(self.header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(2)
        title = QLabel("SEC Filings")
        title.setObjectName("SectionTitle")
        subtitle = QLabel("8-K, 10-Q, 10-K feeds inspired by Perplexity.")
        subtitle.setObjectName("SectionHint")
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        layout.addWidget(self.header_frame)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Type", "Summary", "Filed"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        self.latest_summary = ("Awaiting SEC feed", "—")
        self.setLayout(layout)

    def load_ticker(self, ticker: str):
        filings = self._mock_filings(ticker)
        self.table.setRowCount(len(filings))
        for row, entry in enumerate(filings):
            self.table.setItem(row, 0, QTableWidgetItem(entry["type"]))
            self.table.setItem(row, 1, QTableWidgetItem(entry["title"]))
            self.table.setItem(row, 2, QTableWidgetItem(entry["time"]))
        if filings:
            self.latest_summary = (f"{filings[0]['type']} · {filings[0]['title']}", filings[0]["time"])
        else:
            self.latest_summary = ("No filings surfaced", "Check EDGAR feed")

    def get_latest_summary(self) -> tuple[str, str]:
        return self.latest_summary

    def _mock_filings(self, ticker: str) -> list[dict]:
        base = datetime.utcnow()
        templates = [
            ("8-K", f"{ticker} announces product update", "Operations"),
            ("10-Q", f"{ticker} quarterly report highlights margin shift", "Financial"),
            ("SC 13G", f"Passive stake filed in {ticker}", "Ownership"),
        ]
        filings = []
        for idx, (ftype, title, _) in enumerate(templates):
            stamp = (base - timedelta(hours=idx * 3)).strftime("%b %d • %H:%M UTC")
            filings.append({"type": ftype, "title": title, "time": stamp})
        return filings

    def set_tab_mode(self, tabbed: bool):
        if hasattr(self, "header_frame"):
            self.header_frame.setVisible(not tabbed)


class MacroCalendarWidget(QWidget):
    """ForexFactory-style macro events placeholder."""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(BASE_SPACING, BASE_SPACING, BASE_SPACING, BASE_SPACING)
        layout.setSpacing(BASE_SPACING)

        self.header_frame = QFrame()
        header_layout = QVBoxLayout(self.header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(2)
        title = QLabel("Macro Calendar")
        title.setObjectName("SectionTitle")
        subtitle = QLabel("ForexFactory-inspired economic pulse.")
        subtitle.setObjectName("SectionHint")
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        layout.addWidget(self.header_frame)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Time", "Event", "Impact", "Ccy"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)

        self.events: list[dict] = []
        self.focus_symbol: str | None = None
        self.refresh_events()
        self.setLayout(layout)

    def refresh_events(self):
        base = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        sample = [
            {"title": "CPI (YoY)", "currency": "USD", "impact": "High", "offset": 2},
            {"title": "ECB Press Conference", "currency": "EUR", "impact": "High", "offset": 5},
            {"title": "PMI Manufacturing", "currency": "CNY", "impact": "Medium", "offset": 8},
        ]
        self.events = []
        self.table.setRowCount(len(sample))
        for row, event in enumerate(sample):
            ts = base + timedelta(hours=event["offset"])
            self.events.append({**event, "datetime": ts})
            self.table.setItem(row, 0, QTableWidgetItem(ts.strftime("%H:%M UTC")))
            self.table.setItem(row, 1, QTableWidgetItem(event["title"]))
            self.table.setItem(row, 2, QTableWidgetItem(event["impact"]))
            self.table.setItem(row, 3, QTableWidgetItem(event["currency"]))

    def get_next_event_summary(self) -> tuple[str, str]:
        now = datetime.utcnow()
        future = sorted(self.events, key=lambda e: e["datetime"])
        for event in future:
            if event["datetime"] >= now:
                delta = event["datetime"] - now
                return (f"{event['title']} ({event['currency']})",
                        f"in {self._format_delta(delta)} · {event['impact']} impact")
        return ("No macro events", "All clear for next 12h")

    def set_focus(self, ticker: str):
        self.focus_symbol = ticker

    def _format_delta(self, delta: timedelta) -> str:
        total_seconds = max(int(delta.total_seconds()), 0)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{hours}h {minutes}m"

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
                try:
                    df = strategy.fetch_hourly_data(ticker, period="30d")
                    if not df.empty:
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
        self.widget_button = None
        self.market_pulse = None
        self.quote_widget = None
        self.chart_widget = None
        self.chatbot = None
        self.screener = None
        self.fundamentals_widget = None
        self.news_widget = None
        self.sec_filings_widget = None
        self.macro_widget = None
        self.stowed_actions: dict[str, QAction] = {}
        self.widget_link_groups: dict[str, int | None] = {}
        self.link_groups: defaultdict[int, set[str]] = defaultdict(set)
        self.link_group_tickers: dict[int, str] = {}
        self.latest_payload: dict[str, Any] | None = None
        self.ticker_cache = TickerDataCache(ttl_seconds=180)
        self.active_workers: set[SnapshotWorker] = set()
        self.widget_factories: Dict[str, Callable[[], QWidget]] = {}
        self.dock_widgets: Dict[str, WorkspaceDock] = {}
        self.init_ui()
        self.apply_theme()
    
    def init_ui(self):
        self.setWindowTitle("Mira - Trading Terminal")
        self.resize(1600, 940)
        
        self.setDockNestingEnabled(True)
        self.setDockOptions(
            QMainWindow.DockOption.AllowTabbedDocks |
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
            "Screener": lambda: ScreenerWidget(self.on_ticker_selected),
            "Fundamentals": lambda: FundamentalsWidget(),
            "News": lambda: NewsWidget(),
            "Copilot": lambda: ChatbotWidget(self.get_context),
            "SEC Filings": lambda: SecFilingsWidget(),
            "Macro Calendar": lambda: MacroCalendarWidget(),
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
            action.triggered.connect(lambda checked, n=key: self.ensure_widget(n))
        if self.widget_button:
            self.widget_button.setMenu(self.widget_menu)
            self.widget_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
    
    def create_default_layout(self):
        quotes = self.ensure_widget("Quotes", Qt.DockWidgetArea.TopDockWidgetArea)
        chart = self.ensure_widget("Chart", Qt.DockWidgetArea.RightDockWidgetArea)
        screener = self.ensure_widget("Screener", Qt.DockWidgetArea.LeftDockWidgetArea)
        fundamentals = self.ensure_widget("Fundamentals", Qt.DockWidgetArea.BottomDockWidgetArea)
        news = self.ensure_widget("News", Qt.DockWidgetArea.BottomDockWidgetArea)
        copilot = self.ensure_widget("Copilot", Qt.DockWidgetArea.RightDockWidgetArea)
        sec = self.ensure_widget("SEC Filings", Qt.DockWidgetArea.RightDockWidgetArea)
        macro = self.ensure_widget("Macro Calendar", Qt.DockWidgetArea.BottomDockWidgetArea)

        if quotes and chart:
            self.splitDockWidget(quotes, chart, Qt.Orientation.Vertical)
        if chart and fundamentals:
            self.splitDockWidget(chart, fundamentals, Qt.Orientation.Vertical)
        if fundamentals and news:
            self.tabifyDockWidget(fundamentals, news)
        if news and macro:
            self.tabifyDockWidget(news, macro)
        if screener and chart:
            self.splitDockWidget(screener, chart, Qt.Orientation.Horizontal)
        if chart and copilot:
            self.splitDockWidget(chart, copilot, Qt.Orientation.Horizontal)
        if copilot and sec:
            self.splitDockWidget(copilot, sec, Qt.Orientation.Vertical)
    
    def ensure_widget(self, key: str, area: Qt.DockWidgetArea | None = None):
        """Make sure a widget dock exists and is visible."""
        if key in self.dock_widgets:
            dock = self.dock_widgets[key]
            dock.show()
            dock.raise_()
            return dock
        factory = self.widget_factories.get(key)
        if not factory:
            return None
        widget = factory()

        dock_shell = QFrame()
        dock_shell.setObjectName("DockBody")
        dock_shell.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        inner_layout = QVBoxLayout(dock_shell)
        inner_layout.setContentsMargins(BASE_SPACING, BASE_SPACING, BASE_SPACING, BASE_SPACING)
        inner_layout.setSpacing(BASE_SPACING)
        inner_layout.addWidget(widget)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setObjectName("DockSplitter")
        splitter.addWidget(dock_shell)
        splitter.setSizes([1])

        dock = WorkspaceDock(key, splitter, widget, self, link_callback=self.set_widget_link)
        dock.closed.connect(self.on_dock_closed)
        dock.collapsed_changed.connect(self.on_dock_collapsed)
        dock.setMinimumSize(QSize(150, 120))
        dock.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        if hasattr(widget, "setSizePolicy"):
            widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.addDockWidget(area or Qt.DockWidgetArea.LeftDockWidgetArea, dock)
        self.dock_widgets[key] = dock
        self.register_widget_instance(key, widget)
        dock.set_link_group_display(self.widget_link_groups.get(key))
        if hasattr(widget, "load_ticker") and self.current_ticker:
            widget.load_ticker(self.current_ticker)
        return dock
    
    def on_dock_closed(self, key: str):
        self.dock_widgets.pop(key, None)
        self.remove_stowed_tab(key)
        group = self.widget_link_groups.pop(key, None)
        if group and key in self.link_groups[group]:
            self.link_groups[group].remove(key)
    
    def register_widget_instance(self, key: str, widget: QWidget):
        child = widget
        if isinstance(widget, QSplitter):
            frame = widget.widget(0)
            if frame and isinstance(frame, QWidget):
                layout = frame.layout()
                if layout and layout.count():
                    inner = layout.itemAt(0).widget()
                    if inner:
                        child = inner

        if key == "Chart":
            self.chart_widget = child
        elif key == "Quotes":
            self.quote_widget = child
        elif key == "Fundamentals":
            self.fundamentals_widget = child
        elif key == "News":
            self.news_widget = child
        elif key == "Copilot":
            self.chatbot = child
        elif key == "Screener":
            self.screener = child
        elif key == "SEC Filings":
            self.sec_filings_widget = child
        elif key == "Macro Calendar":
            self.macro_widget = child
        self.widget_link_groups.setdefault(key, None)

    def set_widget_link(self, key: str, group: int | None):
        prev = self.widget_link_groups.get(key)
        if prev == group:
            return
        if prev and key in self.link_groups[prev]:
            self.link_groups[prev].remove(key)
        self.widget_link_groups[key] = group
        dock = self.dock_widgets.get(key)
        if dock:
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

    def on_dock_collapsed(self, key: str, collapsed: bool):
        dock = self.dock_widgets.get(key)
        if not dock:
            return
        if collapsed:
            self.add_stowed_tab(dock)
        else:
            self.remove_stowed_tab(key)

    def add_stowed_tab(self, dock: WorkspaceDock):
        key = dock.key
        if key in self.stowed_actions:
            return
        action = self.stow_bar.addAction(dock.windowTitle())
        action.triggered.connect(lambda checked=False, k=key: self.restore_stowed(k))
        self.stowed_actions[key] = action
        self.stow_bar.show()

    def remove_stowed_tab(self, key: str):
        action = self.stowed_actions.pop(key, None)
        if action:
            self.stow_bar.removeAction(action)
        if not self.stowed_actions and hasattr(self, "stow_bar"):
            self.stow_bar.hide()

    def restore_stowed(self, key: str):
        dock = self.dock_widgets.get(key)
        if not dock:
            return
        if dock.collapsed:
            dock.toggle_collapsed()
        self.remove_stowed_tab(key)

    def load_widget_ticker(self, key: str, ticker: str, propagate: bool = False,
                           payload: dict | None = None):
        if key in ("Quotes", "Fundamentals", "News") and payload is None:
            payload = self.ticker_cache.peek(ticker)
        loaded = False
        if key == "Chart" and self.chart_widget:
            self.chart_widget.load_ticker(ticker)
            loaded = True
        elif key == "Fundamentals" and self.fundamentals_widget:
            self.fundamentals_widget.load_ticker(ticker, payload)
            loaded = True
        elif key == "News" and self.news_widget:
            self.news_widget.load_ticker(ticker, payload)
            loaded = True
        elif key == "Quotes" and self.quote_widget:
            snapshot = payload.get("snapshot") if payload else None
            if snapshot:
                self.quote_widget.update_snapshot(snapshot)
            else:
                self.quote_widget.show_loading(ticker)
            self.update_brand_accent(ticker)
            loaded = True
        elif key == "SEC Filings" and self.sec_filings_widget:
            self.sec_filings_widget.load_ticker(ticker)
            loaded = True
        elif key == "Macro Calendar" and self.macro_widget:
            self.macro_widget.set_focus(ticker)
            loaded = True
        if propagate:
            self.broadcast_link_update(key, ticker)
        self._sync_hero_context_cards()

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
        """Spawn/refresh background worker for ticker payload (quotes + meta)."""
        ticker = ticker or self.current_ticker
        if not ticker:
            return
        worker = SnapshotWorker(lambda: self.ticker_cache.refresh(ticker))
        self.active_workers.add(worker)
        worker.result_ready.connect(lambda payload, w=worker: self.on_payload_ready(payload, w))
        worker.finished.connect(lambda w=worker: self.cleanup_worker(w))
        worker.start()

    def on_payload_ready(self, payload: dict, worker: SnapshotWorker | None = None):
        ticker = (payload or {}).get("ticker", "")
        if ticker.upper() != (self.current_ticker or "").upper():
            return
        self.latest_payload = payload
        self.load_widget_ticker("Quotes", ticker, propagate=False, payload=payload)
        self.load_widget_ticker("Fundamentals", ticker, payload=payload)
        self.load_widget_ticker("News", ticker, payload=payload)
        if worker:
            self.active_workers.discard(worker)

    def cleanup_worker(self, worker: SnapshotWorker):
        self.active_workers.discard(worker)
        worker.deleteLater()

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

    def _sync_hero_context_cards(self):
        if not self.quote_widget:
            return
        if self.sec_filings_widget:
            filing_title, filing_meta = self.sec_filings_widget.get_latest_summary()
            self.quote_widget.set_latest_filing(filing_title, filing_meta)
        if self.macro_widget:
            event_title, event_meta = self.macro_widget.get_next_event_summary()
            self.quote_widget.set_next_event(event_title, event_meta)
    
    def _build_header_button(self, glyph: str, tooltip: str) -> QToolButton:
        btn = QToolButton()
        btn.setObjectName("HeaderGlyph")
        btn.setText(glyph)
        btn.setToolTip(tooltip)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setAutoRaise(False)
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn.setCheckable(False)
        btn.setIcon(QIcon())
        btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        btn.setFixedSize(QSize(40, 40))
        return btn
    
    def create_header(self):
        header = QFrame()
        header.setObjectName("Header")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(24, 12, 24, 12)
        layout.setSpacing(24)
        
        title_block = QVBoxLayout()
        title_block.setSpacing(4)
        wordmark_row = QHBoxLayout()
        wordmark_row.setSpacing(8)
        title = QLabel("Mira")
        title.setObjectName("HeaderTitle")
        badge = QLabel("features · experimental")
        badge.setObjectName("HeaderBadge")
        wordmark_row.addWidget(title)
        wordmark_row.addWidget(badge)
        wordmark_row.addStretch()
        subtitle = QLabel("Perplexity-grade intelligence for traders")
        subtitle.setObjectName("HeaderSubtitle")
        title_block.addLayout(wordmark_row)
        title_block.addWidget(subtitle)
        layout.addLayout(title_block, stretch=1)

        self.market_pulse = MarketPulseWidget()
        layout.addWidget(self.market_pulse, stretch=0)

        layout.addStretch()
        
        controls_container = QFrame()
        controls_container.setObjectName("HeaderButtons")
        controls_layout = QHBoxLayout(controls_container)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(8)

        self.refresh_button = self._build_header_button("↻", "Refresh market data")
        self.refresh_button.clicked.connect(self.refresh_snapshot)
        controls_layout.addWidget(self.refresh_button)

        self.widget_button = self._build_header_button("+", "Add widget")
        self.widget_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
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
        hero_top = theme.get("hero_top", theme["surface"])
        hero_bottom = theme.get("hero_bottom", hero_top)
        quote_gradient = (
            f"qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:1,"
            f" stop:0 {hero_top}, stop:1 {hero_bottom})"
        )
        card_radius = 12
        chip_bg = theme.get("chip_bg", theme["surface"])
        chip_text = theme.get("chip_text", theme["text"])
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
            background-color: {theme['surface_alt']};
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
        QLabel#HeaderBadge {{
            color: {theme['muted']};
            font-size: 12px;
            letter-spacing: 0.08em;
        }}
        QLabel#QuoteSymbol {{
            color: {theme['text']};
            font-size: 32px;
            font-weight: 700;
        }}
        QLabel#QuoteCompany {{
            color: {theme['muted']};
            font-size: 14px;
        }}
        QLabel#QuoteExchange, QLabel#QuoteSession {{
            color: {theme['muted']};
            font-size: 11px;
            letter-spacing: 0.14em;
            border: 1px solid {theme['divider']};
            border-radius: {radius}px;
            padding: 4px 10px;
        }}
        QLabel#QuoteTimestamp {{
            color: {theme['muted']};
            font-size: 12px;
        }}
        QLabel#QuotePrice {{
            color: {theme['text']};
            font-size: 42px;
            font-weight: 700;
        }}
        QLabel#QuoteChange, QLabel#QuoteChangePct {{
            color: {theme['muted']};
            font-size: 18px;
            font-weight: 600;
        }}
        QLabel#QuotePremarket {{
            color: {theme['muted']};
            font-size: 13px;
        }}
        QLabel#QuoteChange[trend="positive"], QLabel#QuoteChangePct[trend="positive"], QLabel#QuotePremarket[trend="positive"] {{
            color: {theme['positive']};
        }}
        QLabel#QuoteChange[trend="negative"], QLabel#QuoteChangePct[trend="negative"], QLabel#QuotePremarket[trend="negative"] {{
            color: {theme['negative']};
        }}
        QFrame#QuoteCard {{
            background: {quote_gradient};
            border: 1px solid {theme['divider']};
            border-radius: {card_radius}px;
        }}
        QFrame#QuoteMetricGrid {{
            background-color: transparent;
            border-top: 1px solid {theme['divider']};
            margin-top: {spacing}px;
        }}
        QFrame#QuoteMetric {{
            background-color: transparent;
        }}
        QLabel#QuoteMetricLabel {{
            color: {theme['muted']};
            font-size: 11px;
            letter-spacing: 0.14em;
        }}
        QLabel#QuoteMetricValue {{
            color: {theme['text']};
            font-size: 16px;
            font-weight: 600;
        }}
        QLabel#QuoteMetricHint {{
            color: {theme['muted']};
            font-size: 12px;
        }}
        QFrame#MarketPulse {{
            border: 1px solid {theme['divider']};
            border-radius: {radius}px;
            background-color: {theme['surface']};
        }}
        QLabel#PulseStatus {{
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 0.1em;
            color: {chip_text};
            background-color: {chip_bg};
            border: 1px solid {theme['divider']};
            border-radius: {radius}px;
            padding: 2px 10px;
        }}
        QLabel#PulseClock {{
            font-size: 20px;
            font-weight: 700;
        }}
        QLabel#PulseMeta {{
            color: {theme['muted']};
            font-size: 12px;
        }}
        QComboBox#PulseSelector {{
            background-color: transparent;
            color: {theme['text']};
            border: 1px solid {theme['divider']};
            padding: 4px 8px;
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
        QComboBox {{
            background-color: {theme['panel_bg']};
            border: 1px solid {theme['divider']};
            color: {theme['text']};
            padding: 4px 8px;
        }}
        QComboBox::drop-down {{
            border: none;
        }}
        QFrame#HeroMicroPanel {{
            background-color: {theme['surface']};
            border: 1px solid {theme['divider']};
            border-radius: {card_radius}px;
        }}
        QLabel#MicroTitle {{
            color: {theme['muted']};
            font-size: 11px;
            letter-spacing: 0.12em;
        }}
        QLabel#MicroPrimary {{
            color: {theme['text']};
            font-size: 18px;
            font-weight: 700;
        }}
        QLabel#MicroMeta {{
            color: {theme['muted']};
            font-size: 12px;
        }}
        QListWidget {{
            background-color: {theme['surface']};
            border: 1px solid {theme['divider']};
            padding: {spacing - 4}px;
            border-radius: {card_radius}px;
        }}
        QListWidget::item {{
            padding: 8px;
            margin-bottom: 4px;
            border-radius: 4px;
            border: 1px solid transparent;
            color: {theme['text']};
        }}
        QListWidget::item:selected {{
            background-color: {theme['surface_alt']};
            color: {theme['text']};
            border-color: {theme['accent']};
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
        QLabel#DockTitle {{
            color: {theme['tab_text']};
        }}
        QWidget#DockTabStrip {{
            background: transparent;
        }}
        QToolButton#DockTabButton {{
            background-color: transparent;
            border: 1px solid {theme['divider']};
            border-radius: 0px;
            padding: 6px 12px;
            color: {theme['tab_text']};
        }}
        QToolButton#DockTabButton:checked {{
            background-color: {theme['accent']};
            color: {theme['button_text']};
            border-color: {theme['accent']};
        }}
        QToolButton#DockTabButton[solo="true"] {{
            border-color: {theme['divider']};
            color: {theme['tab_text']};
        }}
        QToolButton#DockTabButton:disabled {{
            color: {theme['tab_text']};
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
        QTabBar::tab {{
            background: {theme['tab_bg']};
            color: {theme['tab_text']};
            padding: 6px 12px;
            margin-right: 2px;
        }}
        QTabBar::tab:selected {{
            border-bottom: 2px solid {theme['tab_text']};
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
        QFrame#HeaderButtons {{
            background-color: {theme['surface']};
            border: 1px solid {theme['divider']};
            border-radius: {card_radius}px;
            padding: 4px;
        }}
        QToolButton#HeaderGlyph {{
            background-color: transparent;
            border: 1px solid {theme['divider']};
            border-radius: 8px;
            color: {theme['text']};
            font-size: 18px;
        }}
        QToolButton#HeaderGlyph:hover {{
            background-color: {theme['accent_hover']};
            color: {theme['button_hover_text']};
            border-color: {theme['accent_hover']};
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
        """Handle ticker selection."""
        self.current_ticker = ticker
        payload = self.ticker_cache.peek(ticker)
        self.update_brand_accent(ticker)
        self.load_widget_ticker("Quotes", ticker, propagate=True, payload=payload)
        if "Chart" not in self.dock_widgets:
            self.ensure_widget("Chart", Qt.DockWidgetArea.RightDockWidgetArea)
        if "Quotes" not in self.dock_widgets:
            self.ensure_widget("Quotes", Qt.DockWidgetArea.TopDockWidgetArea)
        if "Fundamentals" not in self.dock_widgets:
            self.ensure_widget("Fundamentals", Qt.DockWidgetArea.BottomDockWidgetArea)
        if "News" not in self.dock_widgets:
            self.ensure_widget("News", Qt.DockWidgetArea.BottomDockWidgetArea)
        if "SEC Filings" not in self.dock_widgets:
            self.ensure_widget("SEC Filings", Qt.DockWidgetArea.RightDockWidgetArea)
        if "Macro Calendar" not in self.dock_widgets:
            self.ensure_widget("Macro Calendar", Qt.DockWidgetArea.BottomDockWidgetArea)
        if self.chart_widget:
            self.chart_widget.load_ticker(ticker)
        self.load_widget_ticker("Fundamentals", ticker, payload=payload)
        self.load_widget_ticker("News", ticker, payload=payload)
        if self.sec_filings_widget:
            self.sec_filings_widget.load_ticker(ticker)
        if self.macro_widget:
            self.macro_widget.set_focus(ticker)
        self.request_snapshot()
        if self.quote_widget and self.chart_widget:
            self.quote_widget.set_active_interval(self.chart_widget.current_interval)
        self.broadcast_link_update("Screener", ticker)
        if self.refresh_button:
            self.refresh_button.setEnabled(True)
        if self.chatbot:
            self.chatbot.add_bot_message(f"Loaded {ticker}. Ask me about its signals or strategy!")
        self._sync_hero_context_cards()
    
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
    tab_filter = DockTabBarFilter(app)
    app.installEventFilter(tab_filter)
    
    window = TradingTerminal()
    window._dock_tab_filter = tab_filter
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

