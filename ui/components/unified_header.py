"""
Unified header with integrated workspace tabs.
Follows Mira Design System for professional aesthetics.
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QPalette, QColor

from core.design_system import design
from ui.workspace_tabs import WorkspaceTabs
from widgets.market_clock import MarketClockWidget


class UnifiedHeader(QFrame):
    """
    Professional header with integrated workspace tabs.
    Responsive and follows design system principles.
    """

    def __init__(self, workspace_manager, parent=None):
        super().__init__(parent)
        self.workspace_manager = workspace_manager
        self.current_theme = 'dark'
        self.screen_width = 1440  # Default, will update

        self.setObjectName("UnifiedHeader")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # Main vertical layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header content
        self.header_content = HeaderContent(self)
        main_layout.addWidget(self.header_content)

        # Workspace tabs
        self.workspace_tabs = WorkspaceTabs(workspace_manager, self)
        main_layout.addWidget(self.workspace_tabs)

        self.apply_theme(self.current_theme)

    def resizeEvent(self, event):
        """Handle responsive sizing."""
        self.screen_width = self.width()
        self.apply_theme(self.current_theme)
        super().resizeEvent(event)

    def apply_theme(self, theme: str):
        """Apply design system theme."""
        self.current_theme = theme
        colors = design.COLORS[theme]

        # Calculate responsive values
        header_height = design.get_responsive_value(
            design.LAYOUT['components']['header-height'],
            self.screen_width
        )
        tab_height = design.LAYOUT['components']['tab-height']
        total_height = header_height + tab_height

        self.setFixedHeight(total_height)

        # Professional styling with subtle depth
        self.setStyleSheet(f"""
            QFrame#UnifiedHeader {{
                background-color: {colors['bg-elevated']};
                border: none;
                border-bottom: 1px solid {colors['border']};
            }}
        """)

        # Apply to children
        self.header_content.apply_theme(theme, self.screen_width)
        self.workspace_tabs.apply_theme(theme)


class HeaderContent(QWidget):
    """Header content area with title and controls."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("HeaderContent")

        # Responsive layout
        layout = QHBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # Title section
        self.title_section = TitleSection(self)
        layout.addWidget(self.title_section)

        layout.addSpacing(design.SPACING['lg'])

        # Market clock
        self.market_clock = MarketClockWidget()
        self.market_clock.setFixedWidth(220)
        layout.addWidget(self.market_clock)

        # Flexible spacer
        layout.addStretch()

        # Control buttons
        self.controls = HeaderControls(self)
        layout.addWidget(self.controls)

    def apply_theme(self, theme: str, screen_width: int):
        """Apply responsive theme."""
        colors = design.COLORS[theme]

        # Responsive padding
        padding = design.get_responsive_value(design.SPACING['lg'], screen_width)
        self.layout().setContentsMargins(padding, 0, padding, 0)

        self.setStyleSheet(f"""
            QWidget#HeaderContent {{
                background-color: transparent;
            }}
        """)


class TitleSection(QWidget):
    """Title and subtitle with proper typography."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TitleSection")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(design.SPACING['xxs'])

        # Title with proper typography
        self.title = QLabel("MIRA")
        self.title.setObjectName("AppTitle")
        title_font = QFont()
        title_font.setWeight(design.FONT_WEIGHTS['bold'])
        title_font.setLetterSpacing(
            QFont.SpacingType.AbsoluteSpacing,
            design.LETTER_SPACING['widest']
        )
        self.title.setFont(title_font)

        # Subtitle
        self.subtitle = QLabel("Adaptive Trading Workspace")
        self.subtitle.setObjectName("AppSubtitle")
        subtitle_font = QFont()
        subtitle_font.setWeight(design.FONT_WEIGHTS['regular'])
        subtitle_font.setLetterSpacing(
            QFont.SpacingType.AbsoluteSpacing,
            design.LETTER_SPACING['wide']
        )
        self.subtitle.setFont(subtitle_font)

        layout.addWidget(self.title)
        layout.addWidget(self.subtitle)

    def apply_theme(self, theme: str):
        """Apply theme to title section."""
        colors = design.COLORS[theme]

        self.setStyleSheet(f"""
            QLabel#AppTitle {{
                color: {colors['text-emphasis']};
                font-size: {design.TYPE_SCALE['lg']}px;
            }}
            QLabel#AppSubtitle {{
                color: {colors['text-muted']};
                font-size: {design.TYPE_SCALE['sm']}px;
            }}
        """)


class HeaderControls(QWidget):
    """Header control buttons with consistent styling."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("HeaderControls")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(design.SPACING['xs'])

        # Icon buttons with tooltips
        self.buttons = []
        icons = [
            ("↻", "Refresh Data"),
            ("⚙", "Settings"),
            ("?", "Help"),
            ("⋮", "More")
        ]

        for icon, tooltip in icons:
            btn = IconButton(icon, tooltip, self)
            layout.addWidget(btn)
            self.buttons.append(btn)


class IconButton(QPushButton):
    """Consistent icon button with hover effects."""

    def __init__(self, icon: str, tooltip: str, parent=None):
        super().__init__(icon, parent)
        self.setObjectName("IconButton")
        self.setToolTip(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Fixed size based on design system
        size = design.LAYOUT['components']['toolbar-height'] - design.SPACING['md']
        self.setFixedSize(size, size)

        # Animation for hover
        self.animation = QPropertyAnimation(self, b"iconSize")
        self.animation.setDuration(design.ANIMATION['duration']['fast'])
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def enterEvent(self, event):
        """Smooth hover effect."""
        self.setProperty("hover", True)
        self.style().polish(self)
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Remove hover effect."""
        self.setProperty("hover", False)
        self.style().polish(self)
        super().leaveEvent(event)

    def apply_theme(self, theme: str):
        """Apply theme to button."""
        colors = design.COLORS[theme]

        self.setStyleSheet(f"""
            QPushButton#IconButton {{
                background-color: transparent;
                border: 1px solid {colors['border-subtle']};
                border-radius: {design.EFFECTS['border-radius']['md']}px;
                color: {colors['text-muted']};
                font-size: {design.TYPE_SCALE['md']}px;
                font-weight: {design.FONT_WEIGHTS['light']};
            }}

            QPushButton#IconButton:hover {{
                background-color: {colors['surface-alt']};
                border-color: {colors['border']};
                color: {colors['text']};
            }}

            QPushButton#IconButton:pressed {{
                background-color: {colors['surface-high']};
                border-color: {colors['border-medium']};
                color: {colors['text-emphasis']};
            }}

            QPushButton#IconButton[hover=true] {{
                /* Qt doesn't support CSS transform */
            }}
        """)