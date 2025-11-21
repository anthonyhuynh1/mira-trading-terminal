"""
Chatbot widget providing context-aware trading assistance.
AI copilot placeholder - ready for LLM integration (OpenAI, Claude, etc.)
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTextEdit, QLineEdit, QPushButton, QSizePolicy
)
from PyQt6.QtGui import QFont

from core.themes import BASE_SPACING, TOUCH_TARGET


class ChatbotWidget(QWidget):
    """Context-aware chatbot panel - ready for LLM integration."""

    def __init__(self, context_callback):
        super().__init__()
        self.context_callback = context_callback  # Function to get current context
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(BASE_SPACING)
        layout.setContentsMargins(BASE_SPACING, BASE_SPACING, BASE_SPACING, BASE_SPACING)

        self.header_frame = QFrame()
        header_layout = QVBoxLayout(self.header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(2)
        title = QLabel("AI Copilot")
        title.setObjectName("SectionTitle")
        subtitle = QLabel("Context-aware assistant (LLM integration coming soon)")
        subtitle.setObjectName("SectionHint")
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        layout.addWidget(self.header_frame)

        # Chat display
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont("Courier", 10))
        self.chat_display.setObjectName("ChatDisplay")
        self.chat_display.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.chat_display)

        # Input
        input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Ask about the terminal, widgets, or market data...")
        self.input_field.returnPressed.connect(self.send_message)
        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self.send_message)
        self.input_field.setMinimumHeight(TOUCH_TARGET)
        self.send_btn.setMinimumHeight(TOUCH_TARGET)
        self.input_field.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.send_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_btn)
        layout.addLayout(input_layout)

        self.setLayout(layout)
        self.add_bot_message("Hi! I'm your trading terminal assistant. I can help you understand how to use the terminal and its widgets.")

    def set_tab_mode(self, tabbed: bool):
        if hasattr(self, "header_frame"):
            self.header_frame.setVisible(not tabbed)

    def send_message(self):
        """Handle user message and generate response."""
        user_msg = self.input_field.text().strip()
        if not user_msg:
            return

        self.add_user_message(user_msg)
        self.input_field.clear()

        # Get context
        context = self.context_callback()

        # Generate response
        response = self.generate_response(user_msg, context)
        self.add_bot_message(response)

    def add_user_message(self, msg: str):
        """Add user message to chat."""
        self.chat_display.append(f"<b>You:</b> {msg}")

    def add_bot_message(self, msg: str):
        """Add bot message to chat."""
        self.chat_display.append(f"<b>Assistant:</b> {msg}")

    def generate_response(self, user_msg: str, context: dict) -> str:
        """
        Generate chatbot response based on user message and context.

        TODO: Integrate with LLM API (OpenAI, Claude, etc.)
        For now, provides basic help responses.
        """
        msg_lower = user_msg.lower()
        ticker = context.get("ticker", "N/A")

        # Terminal help responses
        if "help" in msg_lower or "how" in msg_lower:
            return """**Trading Terminal Help**

This terminal provides real-time market data visualization:

**Widgets Available:**
- **Quotes**: Current price, change, volume, and 52-week range
- **Chart**: Interactive TradingView charts
- **Screener**: Watchlist and stock search
- **Fundamentals**: Key metrics (P/E, market cap, etc.)
- **News**: Latest market headlines
- **Market Clock**: Market hours across timezones

**Features:**
- Drag tabs to rearrange widgets
- Create custom workspace layouts
- Save/load workspace presets
- Switch between dark/light themes

Try asking: "What widgets are available?" or "How do I add a widget?"
"""

        if "widget" in msg_lower:
            return """**Available Widgets:**

1. **Quotes** - Real-time price data and statistics
2. **Chart** - TradingView interactive charts
3. **Screener** - Stock watchlist and search
4. **Fundamentals** - Company metrics and ratios
5. **News** - Latest market headlines
6. **Market Clock** - Global market hours

**To add a widget:** Click the "+" button in the toolbar and select from the menu.
**To rearrange:** Drag tab headers to different positions or create new dock areas.
"""

        if "chart" in msg_lower:
            return """**Chart Widget:**

Displays interactive TradingView charts with:
- Multiple timeframes (1m, 5m, 15m, 1h, 4h, 1d, etc.)
- Technical indicators
- Drawing tools
- Real-time updates

The chart automatically updates when you select a new ticker from the screener.
"""

        if "data" in msg_lower or "source" in msg_lower:
            return """**Data Sources:**

This terminal uses **Alpaca Markets API** for:
- Real-time quotes
- Historical price data
- Market news
- High-quality, reliable data

Fundamentals are supplemented with yfinance data.

All data is cached intelligently to minimize API calls and improve performance.
"""

        if "theme" in msg_lower:
            return """**Themes:**

Switch between dark and light themes using the theme button in the toolbar.

The terminal features a minimal, elegant design inspired by professional trading platforms.
"""

        # Context-aware responses
        if ticker != "N/A":
            return f"""**Current Context:**

You're viewing: **{ticker}**

I can help you understand:
- How to read the quote widget for {ticker}
- How to change chart timeframes
- How to find fundamentals and news
- How to add {ticker} to your watchlist

**Coming Soon:** AI-powered market analysis and insights using LLM integration!
"""

        # Default response
        return f"""I'm a basic assistant helping you use the trading terminal.

**I can help with:**
- Terminal features and widgets
- How to navigate and customize
- Understanding the data displayed

**Coming Soon:**
- AI-powered market analysis
- Natural language queries about stocks
- Trading ideas and insights

Try asking: "What widgets are available?" or "How do I use the chart?"

**Note:** Advanced AI features will be available once LLM integration (OpenAI/Claude) is configured.
"""
