"""
StatPill widget for the Trading Terminal.
"""
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel

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
