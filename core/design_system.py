"""
Mira Design System - Professional design standards.
Based on: 8-point grid, golden ratio, and gestalt principles.
"""

from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass
class DesignSystem:
    """Complete design system for Mira."""

    # ============= GRID SYSTEM (8-point) =============
    GRID_UNIT = 8  # Base unit for all spacing

    # Spacing scale (multiples of 8)
    SPACING = {
        'xxs': 4,    # 0.5x - Tight spacing
        'xs': 8,     # 1x   - Compact
        'sm': 12,    # 1.5x - Small
        'md': 16,    # 2x   - Medium (default)
        'lg': 24,    # 3x   - Large
        'xl': 32,    # 4x   - Extra large
        'xxl': 48,   # 6x   - Section spacing
        'xxxl': 64,  # 8x   - Major sections
    }

    # ============= TYPOGRAPHY SCALE =============
    # Using Major Third scale (1.25x) for harmony
    TYPE_SCALE = {
        'xs': 10,     # Smallest readable
        'sm': 11,     # Captions, labels
        'base': 13,   # Body text
        'md': 16,     # Subheadings
        'lg': 20,     # Headings
        'xl': 25,     # Major headings
        'xxl': 31,    # Display
        'xxxl': 39,   # Hero
    }

    # Font weights (following system fonts)
    FONT_WEIGHTS = {
        'light': 300,
        'regular': 400,
        'medium': 500,
        'semibold': 600,
        'bold': 700,
    }

    # Line heights for readability
    LINE_HEIGHTS = {
        'tight': 1.2,   # Headers
        'base': 1.5,    # Body text
        'relaxed': 1.75, # Long form
    }

    # Letter spacing for different contexts
    LETTER_SPACING = {
        'tight': -0.02,  # Large headers
        'normal': 0,      # Body
        'wide': 0.02,    # Small caps
        'wider': 0.08,   # Labels
        'widest': 0.12,  # All caps
    }

    # ============= COLOR SYSTEM =============
    # Monochromatic with calculated ratios
    COLORS = {
        'dark': {
            # Background layers (increasing lightness)
            'bg': '#0a0a0a',        # L: 4%  - Primary background
            'bg-elevated': '#0f0f0f', # L: 6%  - Raised surfaces
            'surface': '#141414',    # L: 8%  - Cards, panels
            'surface-alt': '#1a1a1a', # L: 10% - Hover states
            'surface-high': '#1f1f1f', # L: 12% - Active states

            # Borders (subtle to prominent)
            'border-subtle': '#1f1f1f',  # L: 12% - Barely visible
            'border': '#2a2a2a',         # L: 16% - Default
            'border-medium': '#333333',   # L: 20% - Emphasis
            'border-strong': '#404040',   # L: 25% - Strong emphasis

            # Text (WCAG AAA compliant ratios)
            'text-disabled': '#4d4d4d',  # L: 30% - 2.5:1 ratio
            'text-muted': '#737373',     # L: 45% - 5:1 ratio
            'text-subtle': '#999999',    # L: 60% - 8:1 ratio
            'text': '#e6e6e6',           # L: 90% - 16:1 ratio
            'text-emphasis': '#ffffff',   # L: 100% - 21:1 ratio

            # Semantic colors (adjusted for dark theme)
            'success': '#10b981',  # Green - Positive
            'warning': '#f59e0b',  # Amber - Caution
            'error': '#ef4444',    # Red - Negative
            'info': '#0078d4',     # Blue - Microsoft blue

            # Trading specific
            'bid': '#10b981',      # Green
            'ask': '#ef4444',      # Red
            'neutral': '#737373',  # Gray
        },
        'light': {
            # Inverse of dark theme with same ratios
            'bg': '#ffffff',
            'bg-elevated': '#fafafa',
            'surface': '#f5f5f5',
            'surface-alt': '#ebebeb',
            'surface-high': '#e0e0e0',

            'border-subtle': '#e0e0e0',
            'border': '#d4d4d4',
            'border-medium': '#bfbfbf',
            'border-strong': '#999999',

            'text-disabled': '#bfbfbf',
            'text-muted': '#8c8c8c',
            'text-subtle': '#666666',
            'text': '#1a1a1a',
            'text-emphasis': '#000000',

            'success': '#059669',
            'warning': '#d97706',
            'error': '#dc2626',
            'info': '#0066cc',

            'bid': '#059669',
            'ask': '#dc2626',
            'neutral': '#8c8c8c',
        }
    }

    # ============= LAYOUT PRINCIPLES =============
    LAYOUT = {
        # Breakpoints for responsive design
        'breakpoints': {
            'sm': 640,   # Small screens
            'md': 1024,  # Medium screens
            'lg': 1440,  # Large screens
            'xl': 1920,  # Extra large
        },

        # Container widths
        'container': {
            'min': 320,
            'max': 1920,
            'padding': 24,  # 3x grid unit
        },

        # Component sizes
        'components': {
            'header-height': 64,      # 8x grid
            'tab-height': 40,         # 5x grid
            'toolbar-height': 48,     # 6x grid
            'sidebar-width': 280,     # 35x grid
            'sidebar-min': 200,       # 25x grid
            'sidebar-max': 400,       # 50x grid
        },

        # Golden ratio for proportions
        'golden-ratio': 1.618,

        # Z-index layers
        'z-index': {
            'base': 0,
            'elevated': 10,
            'sticky': 100,
            'overlay': 1000,
            'modal': 2000,
            'popover': 3000,
            'tooltip': 4000,
            'notification': 5000,
        }
    }

    # ============= ANIMATION =============
    ANIMATION = {
        'duration': {
            'instant': 0,
            'fast': 150,
            'base': 250,
            'slow': 350,
            'slower': 500,
        },

        'easing': {
            'linear': 'linear',
            'ease-in': 'cubic-bezier(0.4, 0, 1, 1)',
            'ease-out': 'cubic-bezier(0, 0, 0.2, 1)',
            'ease-in-out': 'cubic-bezier(0.4, 0, 0.2, 1)',
            'spring': 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
        }
    }

    # ============= EFFECTS =============
    EFFECTS = {
        'shadows': {
            'none': 'none',
            'sm': '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
            'base': '0 1px 3px 0 rgba(0, 0, 0, 0.1)',
            'md': '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
            'lg': '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
            'xl': '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
        },

        'blur': {
            'none': '0',
            'sm': '4px',
            'base': '8px',
            'md': '12px',
            'lg': '16px',
            'xl': '24px',
        },

        'border-radius': {
            'none': 0,
            'sm': 2,
            'base': 4,
            'md': 6,
            'lg': 8,
            'xl': 12,
            'full': 9999,
        }
    }

    @classmethod
    def get_spacing(cls, size: str = 'md') -> int:
        """Get spacing value."""
        return cls.SPACING.get(size, cls.SPACING['md'])

    @classmethod
    def get_font_size(cls, size: str = 'base') -> int:
        """Get font size."""
        return cls.TYPE_SCALE.get(size, cls.TYPE_SCALE['base'])

    @classmethod
    def get_color(cls, color: str, theme: str = 'dark') -> str:
        """Get color for theme."""
        return cls.COLORS[theme].get(color, '#000000')

    @classmethod
    def get_responsive_value(cls, base: int, screen_width: int) -> int:
        """Calculate responsive value based on screen size."""
        if screen_width < cls.LAYOUT['breakpoints']['sm']:
            return int(base * 0.85)  # Scale down for small screens
        elif screen_width > cls.LAYOUT['breakpoints']['xl']:
            return int(base * 1.15)  # Scale up for large screens
        return base

    @classmethod
    def generate_stylesheet(cls, theme: str = 'dark', screen_width: int = 1440) -> str:
        """Generate complete stylesheet based on design system."""
        colors = cls.COLORS[theme]

        # Responsive adjustments
        base_font = cls.get_responsive_value(cls.TYPE_SCALE['base'], screen_width)
        header_height = cls.get_responsive_value(cls.LAYOUT['components']['header-height'], screen_width)

        return f"""
        /* Mira Design System Stylesheet */

        * {{
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display",
                         "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            font-size: {base_font}px;
            line-height: {cls.LINE_HEIGHTS['base']};
        }}

        /* Background Layers */
        QMainWindow {{
            background-color: {colors['bg']};
            color: {colors['text']};
        }}

        QWidget {{
            background-color: {colors['bg']};
            color: {colors['text']};
        }}

        /* Typography Scale */
        QLabel {{
            color: {colors['text']};
            font-size: {base_font}px;
            font-weight: {cls.FONT_WEIGHTS['regular']};
        }}

        QLabel[class="heading"] {{
            font-size: {cls.TYPE_SCALE['lg']}px;
            font-weight: {cls.FONT_WEIGHTS['semibold']};
            letter-spacing: {cls.LETTER_SPACING['tight']}em;
            color: {colors['text-emphasis']};
        }}

        QLabel[class="caption"] {{
            font-size: {cls.TYPE_SCALE['sm']}px;
            font-weight: {cls.FONT_WEIGHTS['medium']};
            letter-spacing: {cls.LETTER_SPACING['wider']}em;
            color: {colors['text-muted']};
        }}

        /* Surfaces */
        QFrame {{
            background-color: {colors['surface']};
            border: 1px solid {colors['border-subtle']};
            border-radius: {cls.EFFECTS['border-radius']['base']}px;
            padding: {cls.SPACING['md']}px;
        }}

        QFrame:hover {{
            background-color: {colors['surface-alt']};
            border-color: {colors['border']};
        }}

        /* Responsive Container */
        QWidget#Container {{
            min-width: {cls.LAYOUT['container']['min']}px;
            max-width: {cls.LAYOUT['container']['max']}px;
            padding: {cls.LAYOUT['container']['padding']}px;
        }}

        /* Header */
        QWidget#Header {{
            height: {header_height}px;
            background-color: {colors['bg-elevated']};
            border-bottom: 1px solid {colors['border']};
        }}

        /* Tabs with Golden Ratio proportions */
        QWidget#Tab {{
            height: {cls.LAYOUT['components']['tab-height']}px;
            min-width: {int(cls.LAYOUT['components']['tab-height'] * cls.LAYOUT['golden-ratio'])}px;
            background-color: transparent;
            border-right: 1px solid {colors['border-subtle']};
            padding: 0 {cls.SPACING['md']}px;
        }}

        QWidget#Tab[active="true"] {{
            background-color: {colors['surface']};
            border-bottom: 2px solid {colors['info']};
        }}

        /* Animations - Qt doesn't support CSS transitions, removed */

        /* Focus States (Accessibility) */
        *:focus {{
            outline: 2px solid {colors['info']};
            outline-offset: 2px;
        }}

        /* Scrollbars */
        QScrollBar:vertical {{
            width: {cls.SPACING['xs']}px;
            background: {colors['bg']};
            border: none;
        }}

        QScrollBar::handle:vertical {{
            background: {colors['border-medium']};
            border-radius: {cls.EFFECTS['border-radius']['sm']}px;
            min-height: {cls.SPACING['xl']}px;
        }}

        QScrollBar::handle:vertical:hover {{
            background: {colors['border-strong']};
        }}
        """


# Export singleton instance
design = DesignSystem()