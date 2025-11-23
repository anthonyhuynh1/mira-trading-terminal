"""
Mira Trading Terminal v2 - Professional Architecture
Features context-based workspaces with unified design system.
"""

import sys
import warnings
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

warnings.filterwarnings("ignore")

import os
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--disable-gpu")

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QDockWidget, QSizePolicy, QFrame, QToolButton, QMenu,
    QToolBar, QStyle, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, QSize, pyqtSignal
from PyQt6.QtGui import QAction, QIcon

# Import our new architecture components
from core.design_system import design
from core.workspace.workspace_manager_v2 import (
    WorkspaceManagerV2, WorkspaceConfig, WorkspaceType, WidgetConfig
)
from ui.components.unified_header import UnifiedHeader
from core.data_pipeline.base import DataManager
from core.data_provider import TickerDataProvider  # Legacy compatibility

# Import widgets
from widgets.quotes import QuoteWidget
from widgets.chart import ChartWidget
from widgets.screener import ScreenerWidget
from widgets.fundamentals import FundamentalsWidget
from widgets.news import NewsWidget
from widgets.chatbot import ChatbotWidget

# Import docking system
from docking.workspace_dock import WorkspaceDock


class MiraTradingTerminal(QMainWindow):
    """Professional trading terminal with context-based workspaces."""

    # Signals
    workspace_changed = pyqtSignal(str)  # Emits workspace_id
    ticker_changed = pyqtSignal(str)     # Emits ticker symbol

    def __init__(self):
        super().__init__()

        # Initialize state
        self.current_theme = 'dark'
        self.current_ticker = None
        self.widgets: Dict[str, QWidget] = {}
        self.docks: Dict[str, WorkspaceDock] = {}

        # Initialize data layer
        self.data_manager = DataManager()
        self.legacy_data_provider = TickerDataProvider()  # For widget compatibility

        # Initialize workspace management
        app_data_dir = Path.home() / ".mira_terminal"
        app_data_dir.mkdir(exist_ok=True)
        self.workspace_manager = WorkspaceManagerV2(app_data_dir)

        # Widget factories for lazy loading
        self.widget_factories = {
            "quotes": lambda: QuoteWidget(self.handle_interval_change),
            "chart": lambda: ChartWidget(self.get_current_theme),
            "screener": lambda: ScreenerWidget(self.on_ticker_selected),
            "fundamentals": lambda: FundamentalsWidget(self.legacy_data_provider),
            "news": lambda: NewsWidget(self.legacy_data_provider),
            "copilot": lambda: ChatbotWidget(self.get_context),
        }

        # Auto-refresh timer
        self.auto_refresh_timer = QTimer(self)
        self.auto_refresh_timer.timeout.connect(self.refresh_data)
        self.auto_refresh_timer.start(15000)  # 15 seconds

        self.init_ui()
        self.apply_theme(self.current_theme)

        # Load default workspace
        self.load_default_workspace()

    def init_ui(self):
        """Initialize the UI with professional design system."""
        self.setWindowTitle("Mira - Adaptive Trading Workspace")

        # Use design system responsive sizing
        base_width = design.LAYOUT['container']['max']
        base_height = int(base_width / design.LAYOUT['golden-ratio'])
        self.resize(base_width, base_height)

        # Configure docking
        self.setDockNestingEnabled(True)
        self.setDockOptions(
            QMainWindow.DockOption.AllowNestedDocks |
            QMainWindow.DockOption.AnimatedDocks |
            QMainWindow.DockOption.GroupedDragging |
            QMainWindow.DockOption.AllowTabbedDocks
        )

        # Minimal central widget (docks fill the space)
        central = QWidget()
        central.setObjectName("CentralWorkspace")
        central.setMaximumSize(1, 1)
        central.setVisible(False)
        self.setCentralWidget(central)

        # Create unified header with workspace tabs
        self.header = UnifiedHeader(self.workspace_manager, self)
        self.setMenuWidget(self.header)

        # Connect workspace signals
        self.header.workspace_tabs.workspace_changed.connect(self.switch_workspace)
        self.header.workspace_tabs.new_workspace_requested.connect(self.create_new_workspace)

        # Status bar for subtle feedback
        self.create_status_bar()

    def create_status_bar(self):
        """Create minimal status bar."""
        self.status_bar = self.statusBar()
        self.status_bar.setObjectName("StatusBar")
        self.status_bar.showMessage("Ready")

    def apply_theme(self, theme: str):
        """Apply design system theme."""
        self.current_theme = theme

        # Generate and apply stylesheet
        stylesheet = design.generate_stylesheet(theme, self.width())

        # Add specific styles for our components
        colors = design.COLORS[theme]
        additional_styles = f"""
        QMainWindow {{
            background-color: {colors['bg']};
        }}

        QWidget#CentralWorkspace {{
            background-color: {colors['bg']};
        }}

        QStatusBar#StatusBar {{
            background-color: {colors['bg-elevated']};
            border-top: 1px solid {colors['border-subtle']};
            color: {colors['text-muted']};
            font-size: {design.TYPE_SCALE['sm']}px;
            padding: {design.SPACING['xs']}px {design.SPACING['md']}px;
        }}

        QDockWidget {{
            background-color: {colors['surface']};
            border: 1px solid {colors['border-subtle']};
            border-radius: {design.EFFECTS['border-radius']['base']}px;
        }}

        QDockWidget::title {{
            background-color: {colors['surface-alt']};
            border-bottom: 1px solid {colors['border']};
            padding: {design.SPACING['sm']}px;
            text-align: left;
        }}
        """

        self.setStyleSheet(stylesheet + additional_styles)

        # Apply theme to header
        self.header.apply_theme(theme)

        # Apply to all widgets
        for widget in self.widgets.values():
            if hasattr(widget, 'apply_theme'):
                widget.apply_theme(theme)

    def load_default_workspace(self):
        """Load the default workspace on startup."""
        workspaces = self.workspace_manager.list_workspaces()

        if workspaces:
            # Load most recent workspace
            workspace = workspaces[0]
        else:
            # Create default workspace
            workspace = self.workspace_manager.create_workspace(
                "Main Workspace",
                WorkspaceType.CUSTOM
            )

        self.switch_workspace(workspace.id)

    def switch_workspace(self, workspace_id: str):
        """Switch to a different workspace."""
        workspace = self.workspace_manager.get_workspace(workspace_id)
        if not workspace:
            return

        # Clear existing docks
        self.clear_all_docks()

        # Activate workspace
        self.workspace_manager.activate_workspace(workspace_id)

        # Load workspace widgets
        self.load_workspace_widgets(workspace)

        # Update UI
        if workspace.primary_symbol:
            self.on_ticker_selected(workspace.primary_symbol)

        # Emit signal
        self.workspace_changed.emit(workspace_id)

        # Status feedback
        self.status_bar.showMessage(f"Loaded workspace: {workspace.name}", 3000)

    def clear_all_docks(self):
        """Remove all dock widgets."""
        for dock in list(self.docks.values()):
            self.removeDockWidget(dock)
            dock.deleteLater()
        self.docks.clear()
        self.widgets.clear()

    def load_workspace_widgets(self, workspace: WorkspaceConfig):
        """Load widgets from workspace configuration."""
        # Create docks for each widget in the workspace
        for widget_config in workspace.widgets:
            self.create_widget_dock(widget_config)

        # Restore layout if saved
        if workspace.layout_state:
            try:
                self.restoreState(workspace.layout_state.encode())
            except:
                # Layout incompatible, use default arrangement
                self.arrange_default_layout()
        else:
            self.arrange_default_layout()

    def create_widget_dock(self, config: WidgetConfig) -> Optional[WorkspaceDock]:
        """Create a dock widget from configuration."""
        # Get or create widget
        widget = self.get_or_create_widget(config.widget_type)
        if not widget:
            return None

        # Create dock
        dock_id = f"dock_{config.widget_type}_{id(widget)}"
        dock = WorkspaceDock(
            dock_id,
            config.widget_type.title(),
            widget,
            self,
            link_callback=lambda key, group: None,  # Simplified for now
            widget_menu_callback=lambda dock, anchor: None
        )

        # Configure dock
        dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetClosable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )

        # Apply settings
        if config.symbols and hasattr(widget, 'load_ticker'):
            widget.load_ticker(config.symbols[0])

        if config.settings and hasattr(widget, 'apply_settings'):
            widget.apply_settings(config.settings)

        # Position dock
        area_map = {
            'left': Qt.DockWidgetArea.LeftDockWidgetArea,
            'right': Qt.DockWidgetArea.RightDockWidgetArea,
            'top': Qt.DockWidgetArea.TopDockWidgetArea,
            'bottom': Qt.DockWidgetArea.BottomDockWidgetArea,
            'center': Qt.DockWidgetArea.RightDockWidgetArea  # Default
        }
        area = area_map.get(config.position, Qt.DockWidgetArea.RightDockWidgetArea)

        self.addDockWidget(area, dock)
        self.docks[config.widget_type] = dock

        return dock

    def get_or_create_widget(self, widget_type: str) -> Optional[QWidget]:
        """Get existing widget or create new one."""
        if widget_type in self.widgets:
            return self.widgets[widget_type]

        factory = self.widget_factories.get(widget_type)
        if not factory:
            return None

        widget = factory()
        self.widgets[widget_type] = widget

        # Apply current theme
        if hasattr(widget, 'apply_theme'):
            widget.apply_theme(self.current_theme)

        return widget

    def arrange_default_layout(self):
        """Arrange docks in a sensible default layout."""
        # Find key docks
        chart_dock = self.docks.get('chart')
        screener_dock = self.docks.get('screener')
        quotes_dock = self.docks.get('quotes')
        fundamentals_dock = self.docks.get('fundamentals')
        news_dock = self.docks.get('news')

        # Arrange in typical trading layout
        if screener_dock and chart_dock:
            self.splitDockWidget(screener_dock, chart_dock, Qt.Orientation.Horizontal)
            self.resizeDocks([screener_dock, chart_dock], [350, 1250], Qt.Orientation.Horizontal)

        if chart_dock and quotes_dock:
            self.tabifyDockWidget(chart_dock, quotes_dock)

        if fundamentals_dock and news_dock:
            self.tabifyDockWidget(fundamentals_dock, news_dock)

        if chart_dock and fundamentals_dock:
            self.splitDockWidget(chart_dock, fundamentals_dock, Qt.Orientation.Vertical)

    def create_new_workspace(self):
        """Create a new workspace interactively."""
        # This would normally show a dialog
        # For now, create a simple workspace
        workspace = self.workspace_manager.create_workspace(
            f"Workspace {len(self.workspace_manager.workspaces) + 1}",
            WorkspaceType.CUSTOM
        )

        # Switch to it
        self.switch_workspace(workspace.id)

    def on_ticker_selected(self, ticker: str):
        """Handle ticker selection."""
        self.current_ticker = ticker

        # Update all ticker-aware widgets
        for widget in self.widgets.values():
            if hasattr(widget, 'load_ticker'):
                widget.load_ticker(ticker)

        # Update current workspace's primary symbol
        if self.workspace_manager.active_workspace_id:
            workspace = self.workspace_manager.get_workspace(
                self.workspace_manager.active_workspace_id
            )
            if workspace:
                workspace.primary_symbol = ticker
                self.workspace_manager._save_workspace(workspace)

        # Emit signal
        self.ticker_changed.emit(ticker)

        # Status feedback
        self.status_bar.showMessage(f"Loaded: {ticker}", 3000)

    def handle_interval_change(self, interval: str):
        """Handle timeframe changes."""
        chart = self.widgets.get('chart')
        if chart and hasattr(chart, 'update_chart'):
            chart.update_chart(self.current_ticker, interval)

    def get_current_theme(self):
        """Get current theme for widgets."""
        return {'name': self.current_theme}

    def get_context(self) -> Dict[str, Any]:
        """Get current context for AI assistant."""
        return {
            "ticker": self.current_ticker or "N/A",
            "workspace": self.workspace_manager.active_workspace_id or "N/A",
            "timestamp": datetime.now().isoformat(),
            "theme": self.current_theme
        }

    def refresh_data(self):
        """Refresh data for active widgets."""
        if not self.current_ticker:
            return

        # Refresh quote widget if visible
        quotes = self.widgets.get('quotes')
        if quotes and hasattr(quotes, 'refresh'):
            quotes.refresh()

    def closeEvent(self, event):
        """Save workspace state on close."""
        # Save current workspace layout
        if self.workspace_manager.active_workspace_id:
            state = self.saveState()
            self.workspace_manager.update_workspace_layout(
                self.workspace_manager.active_workspace_id,
                state.data().decode()
            )

        event.accept()

    def resizeEvent(self, event):
        """Handle window resize for responsive design."""
        super().resizeEvent(event)

        # Update header responsiveness
        self.header.resizeEvent(event)

        # Could trigger responsive adjustments here
        # For now, the design system handles most of it


def main():
    """Launch Mira Trading Terminal."""
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Modern, consistent look

    # Set application metadata
    app.setApplicationName("Mira")
    app.setOrganizationName("Mira Trading")
    app.setApplicationDisplayName("Mira Trading Terminal")

    # Launch terminal
    terminal = MiraTradingTerminal()
    terminal.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()