"""
Chatbot widget for the Trading Terminal.
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTextEdit, QLineEdit,
                             QPushButton, QHBoxLayout, QLabel, QFrame)
from PyQt6.QtGui import QFont

from services.chatbot_service import generate_response

BASE_SPACING = 12
TOUCH_TARGET = 44

class ChatbotWidget(QWidget):
    """Context-aware chatbot panel."""
    
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
        subtitle = QLabel("Context-aware assistant that knows your current view.")
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
        self.input_field.setPlaceholderText("Ask about the chart, strategy, or ticker...")
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
        self.add_bot_message("Hi! I'm your trading assistant. Ask me about charts, signals, or strategies!")
    
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
        response = generate_response(user_msg, context)
        self.add_bot_message(response)
    
    def add_user_message(self, msg: str):
        """Add user message to chat."""
        self.chat_display.append(f"<b>You:</b> {msg}")
    
    def add_bot_message(self, msg: str):
        """Add bot message to chat."""
        self.chat_display.append(f"<b>Assistant:</b> {msg}")
