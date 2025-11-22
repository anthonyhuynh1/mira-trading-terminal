from dataclasses import dataclass, field
from typing import Optional
import uuid

@dataclass
class StockPage:
    page_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    page_name: str = "Untitled"
    primary_ticker: str = "SPY"
    widget_states: dict = field(default_factory=dict)

    # Layout state - stores QMainWindow state for this page
    layout_state: Optional[bytes] = None  # QMainWindow.saveState()

    # Widget configuration - which widgets are visible/hidden
    visible_widgets: set = field(default_factory=set)  # {"Quotes", "Chart", ...}

    # Dock positions and sizes
    dock_geometry: dict = field(default_factory=dict)  # {dock_id: geometry_bytes}
