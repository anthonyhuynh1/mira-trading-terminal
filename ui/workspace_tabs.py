"""
Flexible workspace tab system for Mira.
Allows traders to organize their workspaces however they want.
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QLabel, QMenu, QInputDialog, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QFont, QAction

from core.workspace.workspace_manager_v2 import (
    WorkspaceManagerV2, WorkspaceConfig, WorkspaceType
)
from core.themes import THEMES


class WorkspaceTab(QWidget):
    """Individual workspace tab."""
    clicked = pyqtSignal(str)  # Emits workspace_id
    close_requested = pyqtSignal(str)
    rename_requested = pyqtSignal(str)
    duplicate_requested = pyqtSignal(str)

    def __init__(self, workspace: WorkspaceConfig, parent=None):
        super().__init__(parent)
        self.workspace = workspace
        self.is_active = False

        self.setObjectName("WorkspaceTab")
        self.setFixedHeight(40)
        self.setMinimumWidth(100)
        self.setMaximumWidth(250)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 8, 0)
        layout.setSpacing(8)

        # Icon for workspace type
        self.icon_label = QLabel(self._get_workspace_icon())
        self.icon_label.setObjectName("TabIcon")
        layout.addWidget(self.icon_label)

        # Name
        self.name_label = QLabel(workspace.name)
        self.name_label.setObjectName("TabName")
        font = QFont()
        font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 102)
        self.name_label.setFont(font)
        layout.addWidget(self.name_label, 1)

        # Symbol indicator (if workspace has primary symbol)
        if workspace.primary_symbol:
            self.symbol_label = QLabel(workspace.primary_symbol)
            self.symbol_label.setObjectName("TabSymbol")
            layout.addWidget(self.symbol_label)

        # Close button
        self.close_btn = QPushButton("×")
        self.close_btn.setObjectName("TabClose")
        self.close_btn.setFixedSize(16, 16)
        self.close_btn.clicked.connect(
            lambda: self.close_requested.emit(self.workspace.id)
        )
        self.close_btn.hide()  # Show on hover
        layout.addWidget(self.close_btn)

    def _get_workspace_icon(self) -> str:
        """Get icon for workspace type."""
        icons = {
            WorkspaceType.RESEARCH: "🔍",
            WorkspaceType.DAY_TRADE: "⚡",
            WorkspaceType.PORTFOLIO: "💼",
            WorkspaceType.EARNINGS: "📊",
            WorkspaceType.NEWS: "📰",
            WorkspaceType.CUSTOM: "⚙"
        }
        return icons.get(self.workspace.type, "📈")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.workspace.id)
        elif event.button() == Qt.MouseButton.RightButton:
            self.show_context_menu(event.pos())

    def show_context_menu(self, pos: QPoint):
        """Show context menu for workspace operations."""
        menu = QMenu(self)

        rename_action = QAction("Rename Workspace", self)
        rename_action.triggered.connect(
            lambda: self.rename_requested.emit(self.workspace.id)
        )
        menu.addAction(rename_action)

        duplicate_action = QAction("Duplicate Workspace", self)
        duplicate_action.triggered.connect(
            lambda: self.duplicate_requested.emit(self.workspace.id)
        )
        menu.addAction(duplicate_action)

        menu.addSeparator()

        close_action = QAction("Close Workspace", self)
        close_action.triggered.connect(
            lambda: self.close_requested.emit(self.workspace.id)
        )
        menu.addAction(close_action)

        menu.exec(self.mapToGlobal(pos))

    def enterEvent(self, event):
        self.close_btn.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self.is_active:
            self.close_btn.hide()
        super().leaveEvent(event)

    def set_active(self, active: bool):
        """Update active state."""
        self.is_active = active
        self.setProperty("active", active)
        if active:
            self.close_btn.show()
        else:
            self.close_btn.hide()
        self.style().unpolish(self)
        self.style().polish(self)

    def update_workspace(self, workspace: WorkspaceConfig):
        """Update with new workspace data."""
        self.workspace = workspace
        self.name_label.setText(workspace.name)


class WorkspaceTabs(QWidget):
    """Main workspace tab bar that integrates with header."""
    workspace_changed = pyqtSignal(str)  # Emits workspace_id
    new_workspace_requested = pyqtSignal()

    def __init__(self, workspace_manager: WorkspaceManagerV2, parent=None):
        super().__init__(parent)
        self.workspace_manager = workspace_manager
        self.tabs = {}

        self.setObjectName("WorkspaceTabs")
        self.setFixedHeight(40)

        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(0)

        # Tab container
        self.tab_container = QWidget()
        self.tab_container.setObjectName("TabContainer")
        self.tab_layout = QHBoxLayout(self.tab_container)
        self.tab_layout.setContentsMargins(0, 0, 0, 0)
        self.tab_layout.setSpacing(1)

        layout.addWidget(self.tab_container)
        layout.addStretch()

        # Quick add menu button
        self.add_button = QPushButton("+")
        self.add_button.setObjectName("AddWorkspace")
        self.add_button.setFixedSize(32, 40)
        self.add_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_button.clicked.connect(self.show_add_menu)
        layout.addWidget(self.add_button)

        # Load existing workspaces
        self.refresh_tabs()

    def refresh_tabs(self):
        """Rebuild tabs from workspace manager."""
        # Clear existing
        while self.tab_layout.count():
            child = self.tab_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.tabs.clear()

        # Add workspace tabs
        for workspace in self.workspace_manager.list_workspaces():
            self.add_tab(workspace)

        # Set active tab
        if self.workspace_manager.active_workspace_id:
            self.set_active_tab(self.workspace_manager.active_workspace_id)

    def add_tab(self, workspace: WorkspaceConfig):
        """Add a tab for workspace."""
        tab = WorkspaceTab(workspace, self)
        tab.clicked.connect(self.on_tab_clicked)
        tab.close_requested.connect(self.on_close_requested)
        tab.rename_requested.connect(self.on_rename_requested)
        tab.duplicate_requested.connect(self.on_duplicate_requested)

        self.tab_layout.addWidget(tab)
        self.tabs[workspace.id] = tab

    def set_active_tab(self, workspace_id: str):
        """Set the active tab."""
        for wid, tab in self.tabs.items():
            tab.set_active(wid == workspace_id)

    def on_tab_clicked(self, workspace_id: str):
        """Handle tab click."""
        self.workspace_manager.activate_workspace(workspace_id)
        self.set_active_tab(workspace_id)
        self.workspace_changed.emit(workspace_id)

    def on_close_requested(self, workspace_id: str):
        """Handle close request."""
        if len(self.tabs) <= 1:
            QMessageBox.warning(
                self,
                "Cannot Close",
                "You must have at least one workspace open."
            )
            return

        reply = QMessageBox.question(
            self,
            "Close Workspace",
            f"Close this workspace?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.workspace_manager.delete_workspace(workspace_id)
            self.refresh_tabs()
            # Emit change for new active workspace
            if self.workspace_manager.active_workspace_id:
                self.workspace_changed.emit(
                    self.workspace_manager.active_workspace_id
                )

    def on_rename_requested(self, workspace_id: str):
        """Handle rename request."""
        workspace = self.workspace_manager.get_workspace(workspace_id)
        if not workspace:
            return

        new_name, ok = QInputDialog.getText(
            self,
            "Rename Workspace",
            "New name:",
            text=workspace.name
        )

        if ok and new_name:
            workspace.name = new_name
            self.workspace_manager._save_workspace(workspace)
            self.tabs[workspace_id].update_workspace(workspace)

    def on_duplicate_requested(self, workspace_id: str):
        """Handle duplicate request."""
        workspace = self.workspace_manager.get_workspace(workspace_id)
        if not workspace:
            return

        new_workspace = self.workspace_manager.create_workspace(
            f"{workspace.name} (Copy)",
            workspace.type
        )

        # Copy widgets
        new_workspace.widgets = workspace.widgets.copy()
        self.workspace_manager._save_workspace(new_workspace)

        self.refresh_tabs()

    def show_add_menu(self):
        """Show menu for adding workspaces."""
        menu = QMenu(self)

        # Quick templates
        research_action = QAction("📚 Research Workspace", self)
        research_action.triggered.connect(self.create_research_workspace)
        menu.addAction(research_action)

        trading_action = QAction("⚡ Trading Workspace", self)
        trading_action.triggered.connect(self.create_trading_workspace)
        menu.addAction(trading_action)

        portfolio_action = QAction("💼 Portfolio Workspace", self)
        portfolio_action.triggered.connect(self.create_portfolio_workspace)
        menu.addAction(portfolio_action)

        menu.addSeparator()

        custom_action = QAction("✨ Custom Workspace", self)
        custom_action.triggered.connect(self.create_custom_workspace)
        menu.addAction(custom_action)

        menu.exec(self.add_button.mapToGlobal(QPoint(0, self.add_button.height())))

    def create_research_workspace(self):
        """Create research workspace."""
        symbol, ok = QInputDialog.getText(
            self,
            "Research Workspace",
            "Symbol to research:"
        )

        if ok and symbol:
            workspace = self.workspace_manager.create_workspace(
                f"Research: {symbol}",
                WorkspaceType.RESEARCH,
                template="research",
                symbol=symbol.upper()
            )
            self.refresh_tabs()
            self.on_tab_clicked(workspace.id)

    def create_trading_workspace(self):
        """Create trading workspace."""
        symbols_str, ok = QInputDialog.getText(
            self,
            "Trading Workspace",
            "Symbols (comma-separated):"
        )

        if ok and symbols_str:
            symbols = [s.strip().upper() for s in symbols_str.split(",")]
            workspace = self.workspace_manager.create_workspace(
                f"Trade: {', '.join(symbols[:3])}",
                WorkspaceType.DAY_TRADE,
                template="day_trade",
                symbols=symbols
            )
            self.refresh_tabs()
            self.on_tab_clicked(workspace.id)

    def create_portfolio_workspace(self):
        """Create portfolio workspace."""
        workspace = self.workspace_manager.create_workspace(
            "Portfolio",
            WorkspaceType.PORTFOLIO,
            template="portfolio"
        )
        self.refresh_tabs()
        self.on_tab_clicked(workspace.id)

    def create_custom_workspace(self):
        """Create custom workspace."""
        name, ok = QInputDialog.getText(
            self,
            "Custom Workspace",
            "Workspace name:"
        )

        if ok and name:
            workspace = self.workspace_manager.create_workspace(
                name,
                WorkspaceType.CUSTOM
            )
            self.refresh_tabs()
            self.on_tab_clicked(workspace.id)

    def apply_theme(self, theme_name: str):
        """Apply theme to tabs."""
        theme = THEMES[theme_name]

        self.setStyleSheet(f"""
            QWidget#WorkspaceTabs {{
                background-color: transparent;
                border: none;
            }}

            QWidget#WorkspaceTab {{
                background-color: transparent;
                border-right: 1px solid {theme['divider']};
            }}
            QWidget#WorkspaceTab[active=true] {{
                background-color: {theme['surface_alt']};
                border-bottom: 2px solid {theme['text']};
            }}
            QWidget#WorkspaceTab:hover {{
                background-color: {theme['surface_alt']};
            }}

            QLabel#TabName {{
                color: {theme['muted']};
                font-size: 12px;
                font-weight: 500;
            }}
            QWidget#WorkspaceTab[active=true] QLabel#TabName {{
                color: {theme['text']};
                font-weight: 600;
            }}

            QLabel#TabIcon {{
                font-size: 14px;
                padding-right: 2px;
            }}

            QLabel#TabSymbol {{
                color: {theme['accent']};
                font-size: 10px;
                font-weight: 600;
                padding: 2px 4px;
                background: {theme['surface_alt']};
                border-radius: 3px;
            }}

            QPushButton#TabClose {{
                background: transparent;
                border: none;
                color: {theme['muted']};
                font-size: 16px;
            }}
            QPushButton#TabClose:hover {{
                color: #ff4444;
            }}

            QPushButton#AddWorkspace {{
                background: transparent;
                border-left: 1px solid {theme['divider']};
                color: {theme['muted']};
                font-size: 18px;
            }}
            QPushButton#AddWorkspace:hover {{
                background: {theme['surface_alt']};
                color: {theme['text']};
            }}
        """)