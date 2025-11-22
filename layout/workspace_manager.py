"""
Workspace management system for saving/loading dock layouts.
Provides preset layouts and custom workspace persistence.
"""

import base64
import json
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt


class WorkspaceManager:
    """
    Manages workspace layouts for the trading terminal.
    Handles saving, loading, and switching between different workspace configurations.
    Similar to "sheets" in Excel - users can have multiple layouts for different workflows.
    """

    def __init__(self, app_dir: Path):
        """
        Initialize workspace manager.

        Args:
            app_dir: Directory to store workspace configurations.
                     Will be user-specific once authentication is added.
        """
        self.app_dir = app_dir
        self.workspaces_dir = app_dir / "workspaces"
        self.workspaces_dir.mkdir(parents=True, exist_ok=True)
        self.current_workspace_name: str | None = None

    def save_workspace(self, name: str, main_window: "TradingTerminal") -> bool:
        """
        Save current dock layout and window state to a named workspace.

        Args:
            name: Name for this workspace (e.g., "Trading", "Research")
            main_window: The TradingTerminal instance to save state from

        Returns:
            True if save was successful, False otherwise
        """
        try:
            workspace_data = {
                "name": name,
                "version": "1.0",
                "created": datetime.now().isoformat(),
                # Save Qt's native window geometry and dock states
                "window_geometry": base64.b64encode(main_window.saveGeometry()).decode('utf-8'),
                "window_state": base64.b64encode(main_window.saveState()).decode('utf-8'),
                # Save custom dock tab information
                "docks": []
            }

            # Serialize each dock's tab configuration
            for dock_id, dock in main_window.dock_by_id.items():
                dock_info = {
                    "dock_id": dock_id,
                    "is_floating": dock.isFloating(),
                    "tabs": dock.tab_order.copy(),  # List of widget keys in order
                    "current_tab_index": dock.tab_bar.currentIndex(),
                }
                workspace_data["docks"].append(dock_info)

            # Save to JSON file
            filepath = self.workspaces_dir / f"{name}.json"
            with open(filepath, 'w') as f:
                json.dump(workspace_data, f, indent=2)

            self.current_workspace_name = name
            return True

        except Exception as e:
            print(f"Error saving workspace '{name}': {e}")
            return False

    def load_workspace(self, name: str, main_window: "TradingTerminal") -> bool:
        """
        Load a saved workspace and restore dock layout.

        Args:
            name: Name of the workspace to load
            main_window: The TradingTerminal instance to restore state to

        Returns:
            True if load was successful, False otherwise
        """
        try:
            filepath = self.workspaces_dir / f"{name}.json"
            if not filepath.exists():
                print(f"Workspace '{name}' not found")
                return False

            with open(filepath, 'r') as f:
                workspace_data = json.load(f)

            # Safely close all existing docks (deferred to avoid crashes)
            docks_to_close = list(main_window.dock_by_id.values())

            # Clear tracking dictionaries first
            main_window.dock_widgets.clear()
            main_window.dock_by_id.clear()

            # Close docks after clearing references (safer)
            for dock in docks_to_close:
                dock.blockSignals(True)
                dock.deleteLater()

            # Restore window geometry and Qt's native dock state
            main_window.restoreGeometry(base64.b64decode(workspace_data["window_geometry"]))
            main_window.restoreState(base64.b64decode(workspace_data["window_state"]))

            # Recreate docks with their tab configurations
            for dock_info in workspace_data["docks"]:
                if not dock_info["tabs"]:
                    continue

                # Create dock with first tab
                first_tab = dock_info["tabs"][0]
                dock = main_window.ensure_widget(first_tab)

                if not dock:
                    continue

                # Add remaining tabs
                for tab_key in dock_info["tabs"][1:]:
                    main_window.add_widget_tab(dock, tab_key)

                # Restore current tab selection
                if 0 <= dock_info["current_tab_index"] < len(dock_info["tabs"]):
                    dock.tab_bar.setCurrentIndex(dock_info["current_tab_index"])

                # Restore floating state
                if dock_info["is_floating"] != dock.isFloating():
                    dock.setFloating(dock_info["is_floating"])

            self.current_workspace_name = name
            return True

        except Exception as e:
            print(f"Error loading workspace '{name}': {e}")
            return False

    def list_workspaces(self) -> list[str]:
        """
        Get list of available workspace names.

        Returns:
            List of workspace names (without .json extension)
        """
        try:
            return [f.stem for f in self.workspaces_dir.glob("*.json")]
        except Exception as e:
            print(f"Error listing workspaces: {e}")
            return []

    def delete_workspace(self, name: str) -> bool:
        """
        Delete a saved workspace.

        Args:
            name: Name of the workspace to delete

        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            filepath = self.workspaces_dir / f"{name}.json"
            if filepath.exists():
                filepath.unlink()
                if self.current_workspace_name == name:
                    self.current_workspace_name = None
                return True
            return False
        except Exception as e:
            print(f"Error deleting workspace '{name}': {e}")
            return False

    @staticmethod
    def get_default_presets() -> dict[str, callable]:
        """
        Returns dictionary of preset layout builders.
        Each preset is a callable that takes a TradingTerminal and creates a layout.

        Returns:
            Dict mapping preset name to layout builder function
        """
        return {
            "Webull": WorkspaceManager._create_webull_layout,
            "Bloomberg": WorkspaceManager._create_bloomberg_layout,
            "Trading": WorkspaceManager._create_trading_layout,
            "Research": WorkspaceManager._create_research_layout,
        }

    @staticmethod
    def _create_bloomberg_layout(terminal: "TradingTerminal"):
        """
        Bloomberg-style layout: Chart dominates center, smaller panels around edges.
        Layout: Screener (left) | Chart (center-large) | Fundamentals (right-small)
                                  Quotes (top bar)
                                  News + Copilot (bottom tabs)
        """
        # Main chart - large center area
        chart = terminal.ensure_widget("Chart", Qt.DockWidgetArea.RightDockWidgetArea)

        # Screener on left
        screener = terminal.ensure_widget("Screener", Qt.DockWidgetArea.LeftDockWidgetArea)

        # Quotes at top
        quotes = terminal.ensure_widget("Quotes", Qt.DockWidgetArea.TopDockWidgetArea)

        # Fundamentals on right
        fundamentals = terminal.ensure_widget("Fundamentals", Qt.DockWidgetArea.RightDockWidgetArea)

        # Split screener and chart horizontally
        if screener and chart:
            terminal.splitDockWidget(screener, chart, Qt.Orientation.Horizontal)

        # Split chart and fundamentals vertically
        if chart and fundamentals:
            terminal.splitDockWidget(chart, fundamentals, Qt.Orientation.Vertical)

        # Add News and Copilot as tabs at bottom
        if fundamentals:
            terminal.add_widget_tab(fundamentals, "News")
            terminal.add_widget_tab(fundamentals, "Copilot")

    @staticmethod
    def _create_trading_layout(terminal: "TradingTerminal"):
        """
        Trading-focused layout: Quotes and Chart prominent, quick access to Screener.
        Layout: Quotes (top) + Chart (center-large)
                Screener (left-thin) | Fundamentals + News (bottom tabs)
        """
        # Quotes and Chart stacked - main focus
        quotes = terminal.ensure_widget("Quotes", Qt.DockWidgetArea.TopDockWidgetArea)
        chart = terminal.ensure_widget("Chart", Qt.DockWidgetArea.RightDockWidgetArea)

        # Screener on left (thin column for quick stock selection)
        screener = terminal.ensure_widget("Screener", Qt.DockWidgetArea.LeftDockWidgetArea)

        # Fundamentals at bottom
        fundamentals = terminal.ensure_widget("Fundamentals", Qt.DockWidgetArea.BottomDockWidgetArea)

        # Arrange layout
        if screener and chart:
            terminal.splitDockWidget(screener, chart, Qt.Orientation.Horizontal)

        # Add complementary widgets as tabs
        if fundamentals:
            terminal.add_widget_tab(fundamentals, "News")
            terminal.add_widget_tab(fundamentals, "Copilot")

    @staticmethod
    def _create_research_layout(terminal: "TradingTerminal"):
        """
        Research-focused layout: Screener, Fundamentals, and News prominent.
        Layout: Screener (left-wide) | Fundamentals + Chart (right, stacked)
                News + Copilot (bottom, full width)
        """
        # Screener wide on left for comparing stocks
        screener = terminal.ensure_widget("Screener", Qt.DockWidgetArea.LeftDockWidgetArea)

        # Fundamentals on right
        fundamentals = terminal.ensure_widget("Fundamentals", Qt.DockWidgetArea.RightDockWidgetArea)

        # News at bottom for reading
        news = terminal.ensure_widget("News", Qt.DockWidgetArea.BottomDockWidgetArea)

        # Arrange layout
        if screener and fundamentals:
            terminal.splitDockWidget(screener, fundamentals, Qt.Orientation.Horizontal)

        # Add Chart and Quotes as tabs in fundamentals dock
        if fundamentals:
            terminal.add_widget_tab(fundamentals, "Chart")
            terminal.add_widget_tab(fundamentals, "Quotes")

        # Add Copilot as tab in news dock
        if news:
            terminal.add_widget_tab(news, "Copilot")

    @staticmethod
    def _create_webull_layout(terminal: "TradingTerminal"):
        """
        Webull-style 3-column layout: Professional trading terminal look.

        Layout structure:
        ┌─────────────┬────────────────┬──────────────┐
        │  SCREENER   │     CHART      │     NEWS     │
        │   (Left)    │   (Middle)     │   (Right)    │
        │   ~20%      │     ~50%       │    ~30%      │
        └─────────────┴────────────────┴──────────────┘

        Key features:
        - Screener locked to left column (Webull-style)
        - Large chart in center for analysis
        - News/secondary info on right
        - Clean 3-column professional structure
        """
        from PyQt6.QtCore import Qt, QTimer

        # Step 1: Create the three main docks
        screener = terminal.ensure_widget("Screener", Qt.DockWidgetArea.LeftDockWidgetArea)
        chart = terminal.ensure_widget("Chart", Qt.DockWidgetArea.RightDockWidgetArea)
        news = terminal.ensure_widget("News", Qt.DockWidgetArea.RightDockWidgetArea)

        if not screener or not chart or not news:
            print("Warning: Could not create all widgets for Webull layout")
            return

        # Step 2: Arrange in 3-column structure
        # Split: Screener | Chart
        terminal.splitDockWidget(screener, chart, Qt.Orientation.Horizontal)

        # Split: Chart | News (creates the 3rd column)
        terminal.splitDockWidget(chart, news, Qt.Orientation.Horizontal)

        # Note: Dock registration happens automatically in ensure_widget()
        # Screener is already marked as immovable, no manual registration needed

        # Step 3: Set proportions after a brief delay (let Qt process the splits)
        def set_proportions():
            try:
                # Get total width
                total_width = terminal.width()

                # Calculate target widths: 20% | 50% | 30%
                screener_width = int(total_width * 0.20)
                chart_width = int(total_width * 0.50)
                news_width = int(total_width * 0.30)

                # Apply sizes
                terminal.resizeDocks(
                    [screener, chart, news],
                    [screener_width, chart_width, news_width],
                    Qt.Orientation.Horizontal
                )

                # Set minimum widths to prevent squishing
                screener.setMinimumWidth(200)  # Screener needs space for watchlist
                chart.setMinimumWidth(400)     # Chart needs space to be useful
                news.setMinimumWidth(250)      # News needs readable width

            except Exception as e:
                print(f"Could not set Webull layout proportions: {e}")

        # Execute after Qt finishes laying out docks
        QTimer.singleShot(100, set_proportions)

        # Step 4: Add optional secondary widgets as tabs
        # Copilot can go in the chart area (middle column)
        if chart:
            terminal.add_widget_tab(chart, "Copilot")

        # Fundamentals can go in news area (right column)
        if news:
            terminal.add_widget_tab(news, "Fundamentals")
