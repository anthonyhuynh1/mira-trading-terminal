"""
Fundamentals widget for the Trading Terminal.
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QTableWidget,
                             QTableWidgetItem, QFrame)
from data.ticker_data_provider import TickerDataProvider
from ..threads import SnapshotWorker
from typing import Callable

BASE_SPACING = 12

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
