"""
Ticker Synchronization Manager with PyQt signal architecture.

Manages link groups for ticker synchronization across widgets.
Uses signals/slots pattern for loose coupling and testability.
"""
from collections import defaultdict
from typing import Optional, Dict, Set
from PyQt6.QtCore import QObject, pyqtSignal


class TickerSyncManager(QObject):
    """
    Manages ticker synchronization across widgets using link groups.

    Widgets can be assigned to link groups (1-6). When one widget in a group
    changes its ticker, all other widgets in the same group are notified.

    Signals:
        ticker_changed: Emitted when a ticker changes for a link group
                       Parameters: (group_id: int, ticker: str, source_widget_key: str)

        group_changed: Emitted when a widget's link group assignment changes
                      Parameters: (widget_key: str, old_group: int | None, new_group: int | None)
    """

    # Signal emitted when a ticker changes for a group
    ticker_changed = pyqtSignal(int, str, str)  # group_id, ticker, source_widget_key

    # Signal emitted when a widget's group assignment changes
    group_changed = pyqtSignal(str, object, object)  # widget_key, old_group, new_group

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)

        # Track widget → group assignment
        self._widget_link_groups: Dict[str, Optional[int]] = {}

        # Track group → widgets (reverse mapping for efficiency)
        self._link_groups: defaultdict[int, Set[str]] = defaultdict(set)

        # Track current ticker for each group
        self._link_group_tickers: Dict[int, str] = {}

    def set_widget_group(self, widget_key: str, group: Optional[int]) -> None:
        """
        Assign a widget to a link group.

        Args:
            widget_key: Unique key for the widget (e.g., "Chart", "Fundamentals")
            group: Link group number (1-6) or None to unlink
        """
        # Validate group number
        if group is not None and (group < 1 or group > 6):
            raise ValueError(f"Link group must be between 1 and 6, got {group}")

        old_group = self._widget_link_groups.get(widget_key)

        # No change, skip
        if old_group == group:
            return

        # Remove from old group if exists
        if old_group is not None:
            self._link_groups[old_group].discard(widget_key)
            # Clean up empty groups
            if not self._link_groups[old_group]:
                del self._link_groups[old_group]
                del self._link_group_tickers[old_group]

        # Add to new group if specified
        if group is not None:
            self._link_groups[group].add(widget_key)
            self._widget_link_groups[widget_key] = group
        else:
            self._widget_link_groups.pop(widget_key, None)

        # Emit group change signal
        self.group_changed.emit(widget_key, old_group, group)

    def get_widget_group(self, widget_key: str) -> Optional[int]:
        """
        Get the link group for a widget.

        Args:
            widget_key: Unique key for the widget

        Returns:
            Link group number (1-6) or None if not linked
        """
        return self._widget_link_groups.get(widget_key)

    def broadcast_ticker(self, widget_key: str, ticker: str) -> None:
        """
        Broadcast a ticker change from a widget to its link group.

        Args:
            widget_key: Widget that initiated the ticker change
            ticker: New ticker symbol
        """
        group = self._widget_link_groups.get(widget_key)

        if group is None:
            # Widget not in a group, no broadcast needed
            return

        # Update group's ticker
        self._link_group_tickers[group] = ticker

        # Emit signal - all widgets in this group will receive it
        self.ticker_changed.emit(group, ticker, widget_key)

    def get_group_ticker(self, group: int) -> Optional[str]:
        """
        Get the current ticker for a link group.

        Args:
            group: Link group number (1-6)

        Returns:
            Current ticker symbol for the group, or None if not set
        """
        return self._link_group_tickers.get(group)

    def get_widgets_in_group(self, group: int) -> Set[str]:
        """
        Get all widgets in a link group.

        Args:
            group: Link group number (1-6)

        Returns:
            Set of widget keys in the group
        """
        return self._link_groups[group].copy()

    def get_all_groups(self) -> Set[int]:
        """
        Get all active link groups.

        Returns:
            Set of group numbers that have widgets assigned
        """
        return set(self._link_groups.keys())

    def remove_widget(self, widget_key: str) -> None:
        """
        Remove a widget from all tracking (called when widget is closed).

        Args:
            widget_key: Unique key for the widget
        """
        group = self._widget_link_groups.get(widget_key)
        if group is not None:
            self._link_groups[group].discard(widget_key)
            # Clean up empty groups
            if not self._link_groups[group]:
                del self._link_groups[group]
                del self._link_group_tickers[group]

        self._widget_link_groups.pop(widget_key, None)

    def clear_all(self) -> None:
        """Clear all link groups and widget assignments."""
        self._widget_link_groups.clear()
        self._link_groups.clear()
        self._link_group_tickers.clear()

    def debug_print(self) -> None:
        """Print current state for debugging."""
        print("\n=== TickerSyncManager State ===")
        print(f"Active groups: {sorted(self.get_all_groups())}")
        for group in sorted(self.get_all_groups()):
            ticker = self._link_group_tickers.get(group, "N/A")
            widgets = sorted(self._link_groups[group])
            print(f"  Group {group} (ticker: {ticker}): {widgets}")

        unlinked_widgets = [k for k, g in self._widget_link_groups.items() if g is None]
        if unlinked_widgets:
            print(f"Unlinked widgets: {sorted(unlinked_widgets)}")
        print("=" * 31 + "\n")
