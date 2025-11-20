"""
WorkspaceDock component for the Trading Terminal.
"""

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QTabBar, QStackedWidget, QStyle, QToolButton, QMenu, QFrame, QDockWidget, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QEvent, QTimer
from typing import Callable


BASE_SPACING = 12


class WorkspaceDock(QDockWidget):
    """Dock widget with Mira header, inline tabs, and stacked content."""

    closed = pyqtSignal(object)
    collapsed_changed = pyqtSignal(object, bool)
    tab_removed = pyqtSignal(str)
    tab_added = pyqtSignal(str)
    active_tab_changed = pyqtSignal(str)

    def __init__(self, dock_id: str, initial_key: str, widget: QWidget, parent: QMainWindow,
                 link_callback: Callable[[str, int | None], None] | None = None,
                 widget_menu_callback: Callable[[object, QWidget | None], None] | None = None):
        super().__init__(initial_key, parent)
        self.dock_id = dock_id
        self.setObjectName(dock_id)
        self.setContentsMargins(0, 0, 0, 0)
        self.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetClosable |
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.collapsed = False
        self._collapsed_height = 48
        self.link_callback = link_callback
        self.widget_menu_callback = widget_menu_callback
        self._link_group: int | None = None
        self._options_menu: QMenu | None = None
        self.tab_widgets: dict[str, QWidget] = {}
        self.tab_order: list[str] = []

        self._init_title_bar()
        self._init_body()
        self.add_tab(initial_key, widget, initial_key)

    def _init_title_bar(self):
        title_bar = QWidget()
        title_bar.setObjectName("DockTitleBar")
        layout = QHBoxLayout(title_bar)
        layout.setContentsMargins(12, 6, 8, 6)
        layout.setSpacing(6)

        self.title_label = QLabel("")
        self.title_label.setObjectName("DockTitleLabel")
        self.title_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        layout.addWidget(self.title_label)

        self.tab_bar = QTabBar()
        self.tab_bar.setObjectName("DockTabBar")
        self.tab_bar.setExpanding(False)
        self.tab_bar.setMovable(True)
        self.tab_bar.setDrawBase(False)
        self.tab_bar.setUsesScrollButtons(True)
        self.tab_bar.currentChanged.connect(self._on_tab_changed)
        self.tab_bar.tabMoved.connect(self._on_tab_moved)
        layout.addWidget(self.tab_bar, stretch=1)

        self.menu_btn = self._create_options_button()
        layout.addWidget(self.menu_btn)

        self.min_btn = self._create_icon_button("icons/minimize.svg", self.toggle_collapsed, "Minimize")
        self.expand_btn = self._create_icon_button("icons/expand.svg", self.expand_to_fill, "Expand to fit space")
        self.float_btn = self._create_icon_button("icons/float.svg", self._toggle_floating, "Float / Dock")
        self.close_btn = self._create_icon_button("icons/close.svg", self._handle_close_clicked, "Close")

        for btn in (self.min_btn, self.expand_btn, self.float_btn, self.close_btn):
            layout.addWidget(btn)

        self.setTitleBarWidget(title_bar)
        title_bar.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        title_bar.customContextMenuRequested.connect(lambda pos: self.menu_btn.showMenu())
        title_bar.installEventFilter(self)
        self._rebuild_options_menu()

    def _init_body(self):
        body = QFrame()
        body.setObjectName("DockBody")
        layout = QVBoxLayout(body)
        layout.setContentsMargins(BASE_SPACING, BASE_SPACING, BASE_SPACING, BASE_SPACING)
        layout.setSpacing(BASE_SPACING)
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)
        self.setWidget(body)

    def _create_button(self, text: str, handler: Callable, tooltip: str) -> QToolButton:
        btn = QToolButton()
        btn.setText(text)
        btn.setToolTip(tooltip)
        btn.clicked.connect(handler)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedSize(QSize(26, 22))
        btn.setObjectName("DockButton")
        return btn

    def _create_icon_button(self, icon_name: str, handler: Callable, tooltip: str) -> QToolButton:
        btn = QToolButton()
        btn.setToolTip(tooltip)
        btn.clicked.connect(handler)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedSize(QSize(24, 24))
        btn.setObjectName("DockIconButton")
        btn.setIconSize(QSize(12, 12))
        btn.setProperty("icon_name", icon_name)
        icon_map = {
            "icons/minimize.svg": QStyle.StandardPixmap.SP_TitleBarMinButton,
            "icons/expand.svg": QStyle.StandardPixmap.SP_TitleBarMaxButton,
            "icons/float.svg": QStyle.StandardPixmap.SP_TitleBarNormalButton,
            "icons/close.svg": QStyle.StandardPixmap.SP_TitleBarCloseButton,
        }
        btn.setIcon(self.style().standardIcon(icon_map.get(icon_name, QStyle.StandardPixmap.SP_TitleBarMenuButton)))
        btn.setText("")
        return btn

    def _create_options_button(self) -> QToolButton:
        btn = QToolButton()
        btn.setObjectName("DockIconButton")
        btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarMenuButton))
        btn.setToolTip("Widget options")
        btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedSize(QSize(24, 24))
        return btn

    def _rebuild_options_menu(self):
        if self._options_menu:
            self._options_menu.deleteLater()
        menu = QMenu(self)
        add_action = menu.addAction("Add Widget…")
        add_action.triggered.connect(self._handle_add_widget)
        menu.addSeparator()
        link_menu = menu.addMenu("Link Group")
        none_action = link_menu.addAction("No Link")
        none_action.setCheckable(True)
        none_action.setChecked(self._link_group is None)
        none_action.triggered.connect(lambda: self._set_link_group(None))
        for group in range(1, 7):
            action = link_menu.addAction(f"Group {group}")
            action.setCheckable(True)
            action.setChecked(self._link_group == group)
            action.triggered.connect(lambda checked=False, g=group: self._set_link_group(g))
        menu.addSeparator()
        float_action = menu.addAction("Float / Dock")
        float_action.triggered.connect(self._toggle_floating)
        self.menu_btn.setMenu(menu)
        self._options_menu = menu

    def _handle_add_widget(self):
        if self.widget_menu_callback:
            anchor = self.titleBarWidget() or self
            self.widget_menu_callback(self, anchor)

    def _set_link_group(self, group: int | None):
        current_key = self.current_tab_key()
        if current_key and self.link_callback:
            self.link_callback(current_key, group)
        self._link_group = group
        self._rebuild_options_menu()

    def add_tab(self, key: str, widget: QWidget, title: str):
        if key in self.tab_widgets:
            self.focus_tab(key)
            return
        widget.setParent(self.stack)
        self.stack.addWidget(widget)
        tab_index = self.tab_bar.addTab(title)
        self.tab_bar.setTabData(tab_index, key)
        self.tab_widgets[key] = widget
        self.tab_order.insert(tab_index, key)
        self.tab_bar.setCurrentIndex(tab_index)
        self.tab_added.emit(key)
        self._update_title_label()

    def take_tab(self, key: str) -> QWidget | None:
        idx = self._index_for_key(key)
        if idx is None:
            return None
        return self._remove_tab_at(idx, delete=False, emit_signal=False)

    def focus_tab(self, key: str):
        idx = self._index_for_key(key)
        if idx is None:
            return
        self.tab_bar.setCurrentIndex(idx)

    def current_tab_key(self) -> str | None:
        idx = self.tab_bar.currentIndex()
        if idx < 0 or idx >= len(self.tab_order):
            return None
        return self.tab_order[idx]

    def list_tab_keys(self) -> list[str]:
        return list(self.tab_order)

    def is_empty(self) -> bool:
        return not self.tab_order

    def _index_for_key(self, key: str) -> int | None:
        try:
            return self.tab_order.index(key)
        except ValueError:
            return None

    def _on_tab_changed(self, index: int):
        if index < 0:
            return
        self.stack.setCurrentIndex(index)
        self._update_title_label()
        key = self.current_tab_key()
        if key:
            self.active_tab_changed.emit(key)

    def _on_tab_moved(self, from_index: int, to_index: int):
        if from_index == to_index:
            return
        key = self.tab_order.pop(from_index)
        self.tab_order.insert(to_index, key)
        widget = self.stack.widget(from_index)
        self.stack.removeWidget(widget)
        self.stack.insertWidget(to_index, widget)

    def _remove_tab_at(self, index: int, delete: bool = True, emit_signal: bool = True) -> QWidget | None:
        if index < 0 or index >= len(self.tab_order):
            return None
        key = self.tab_order.pop(index)
        widget = self.stack.widget(index)
        self.stack.removeWidget(widget)
        self.tab_bar.blockSignals(True)
        self.tab_bar.removeTab(index)
        self.tab_bar.blockSignals(False)
        self.tab_widgets.pop(key, None)
        if emit_signal:
            self.tab_removed.emit(key)
        if delete:
            widget.deleteLater()
        else:
            widget.setParent(None)
        if self.tab_bar.count():
            next_index = min(index, self.tab_bar.count() - 1)
            self.tab_bar.setCurrentIndex(next_index)
        else:
            QTimer.singleShot(0, self.close)
        self._update_title_label()
        return widget

    def _handle_close_clicked(self):
        idx = self.tab_bar.currentIndex()
        self._remove_tab_at(idx, delete=True, emit_signal=True)

    def toggle_collapsed(self):
        self.set_collapsed(not self.collapsed)

    def set_collapsed(self, collapsed: bool):
        if self.collapsed == collapsed:
            return
        self.collapsed = collapsed
        if self.widget():
            self.widget().setVisible(not self.collapsed)
        self.setVisible(not self.collapsed)
        if not self.collapsed:
            self.setMaximumHeight(16777215)
            self.setMinimumHeight(0)
        self.collapsed_changed.emit(self, self.collapsed)

    def _toggle_floating(self):
        self.setFloating(not self.isFloating())

    def expand_to_fill(self):
        mw = self.parent()
        while mw and not isinstance(mw, QMainWindow):
            mw = mw.parent()
        if not mw:
            return
        mw.resizeDocks([self], [mw.width()], Qt.Orientation.Horizontal)
        mw.resizeDocks([self], [mw.height()], Qt.Orientation.Vertical)

    def closeEvent(self, event):
        # Always allow close - emit signal so parent can clean up
        self.closed.emit(self)
        super().closeEvent(event)

    def eventFilter(self, obj, event):
        if obj is self.titleBarWidget():
            if event.type() == QEvent.Type.MouseButtonDblClick and event.button() == Qt.MouseButton.LeftButton:
                self._toggle_floating()
                return True
            if event.type() in (QEvent.Type.MouseButtonPress,
                                QEvent.Type.MouseButtonRelease,
                                QEvent.Type.MouseMove):
                QApplication.sendEvent(self, event)
                return False
        return super().eventFilter(obj, event)

    def set_link_group_display(self, group: int | None):
        self._link_group = group
        self._update_title_label()
        self._rebuild_options_menu()

    def _update_title_label(self):
        if not hasattr(self, "title_label"):
            return
        text = self.current_tab_key() or ""
        if self._link_group:
            text = f"{text} · #{self._link_group}"
        display = text.upper()
        # Hide title label when tabs exist (tabs show the names)
        self.title_label.setVisible(self.tab_bar.count() == 0)
        self.title_label.setText(display)
        super().setWindowTitle(display)
