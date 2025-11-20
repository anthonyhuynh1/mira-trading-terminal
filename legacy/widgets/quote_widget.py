"""
Quote widget for the Trading Terminal.
"""
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel
from .stat_pill import StatPill
from ..utils import ideal_text_color

BASE_SPACING = 12

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
