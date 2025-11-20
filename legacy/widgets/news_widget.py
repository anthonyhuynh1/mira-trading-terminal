"""
News widget for the Trading Terminal.
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QListWidget, QFrame,
                             QSizePolicy)
from data.ticker_data_provider import TickerDataProvider
from ..threads import SnapshotWorker
from typing import Callable

BASE_SPACING = 12

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
