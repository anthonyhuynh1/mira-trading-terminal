"""
Market clock widget displaying time and market status.
Shows current time in different market timezones with open/closed status.
"""

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QComboBox, QSizePolicy


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
