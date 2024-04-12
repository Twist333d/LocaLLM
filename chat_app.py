import sys
import os
from datetime import datetime

from PyQt5.QtCore import QThread, pyqtSignal, Qt, QEvent, QTimer
from PyQt5.QtGui import QFont, QTextCursor, QColor, QTextBlockFormat, QIcon
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QTextEdit, QWidget, \
    QMessageBox, QAction

import requests
import urllib3

# Suppress OpenSSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
urllib3.disable_warnings(urllib3.exceptions.NotOpenSSLWarning)

class Worker(QThread):
    finished = pyqtSignal(str, bool)  # Emit message content and a boolean for success
    error = pyqtSignal(str)

    def __init__(self, prompt):
        super(Worker, self).__init__()
        self.prompt = prompt

    def run(self):
        response, success = self.call_openai_api(self.prompt)
        if success:
            self.finished.emit(response, True)
        else:
            self.finished.emit(response, False)

    def call_openai_api(self, prompt):
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"
        }
        data = {
            "model": "gpt-4-turbo",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 1,
            "max_tokens": 4095,
            "top_p": 1,
        }
        try:
            response = requests.post(url, json=data, headers=headers)
            if response.status_code == 200:
                response_data = response.json()
                message_content = response_data['choices'][0]['message']['content']
                return message_content, True
            return "Failed to fetch response from the server.", False
        except Exception as e:
            return f"An error occurred: {str(e)}", False

class ChatApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.title = 'OpenAI GPT Chat'
        self.initUI()
        self.setStyleSheet("QMainWindow {background-color: #f0f0f0;}")
        self.setWindowIcon(QIcon('app_icon.png'))  # Ensure 'app_icon.png' is in the correct directory
        self.show_timestamps = True

    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(100, 100, 480, 640)
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setSpacing(10)
        self.layout.setContentsMargins(10, 10, 10, 10)

        self.menu = self.menuBar().addMenu("Settings")
        self.action_toggle_timestamps = QAction("Toggle Timestamps", self)
        self.action_toggle_timestamps.setCheckable(True)
        self.action_toggle_timestamps.setChecked(True)
        self.action_toggle_timestamps.triggered.connect(self.toggle_timestamps)
        self.menu.addAction(self.action_toggle_timestamps)

        self.create_chat_history()
        self.create_input_area()
        self.create_send_button()

    def toggle_timestamps(self, checked):
        self.show_timestamps = checked

    def create_chat_history(self):
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setFont(QFont('Roboto', 16))
        self.chat_history.setStyleSheet("background-color: #ffffff; color: #444; padding: 10px;")
        self.chat_history.setAcceptRichText(True)
        self.layout.addWidget(self.chat_history, 5)

    def create_input_area(self):
        self.input_line = QTextEdit()
        self.input_line.setFont(QFont('Roboto', 16))
        self.input_line.setPlaceholderText("Type your message here... Use HTML tags for formatting.")
        self.input_line.setStyleSheet("background-color: #ffffff; color: #444; padding: 10px;")
        self.input_line.setMaximumHeight(100)
        self.input_line.setAcceptRichText(True)
        self.layout.addWidget(self.input_line, 1)

    def eventFilter(self, source, event):
        if event.type() == QEvent.KeyPress and source is self.input_line:
            if event.key() == Qt.Key_Return and event.modifiers() & Qt.ShiftModifier:
                self.input_line.append('')  # Insert newline in the input field
            elif event.key() == Qt.Key_Return:
                self.send_message()  # Send message when Enter is pressed
                return True
        return super(ChatApp, self).eventFilter(source, event)

    def create_send_button(self):
        self.send_button = QPushButton("Send")
        self.send_button.setToolTip('Click to send your message (Enter)')
        self.send_button.clicked.connect(self.send_message)
        self.send_button.setStyleSheet("QPushButton { background-color: #0078d7; color: white; font-weight: bold; padding: 10px; border: none; }")
        self.layout.addWidget(self.send_button, 1)

    def send_message(self):
        user_input = self.input_line.toHtml()  # Use toHtml to preserve rich text formatting
        if user_input.strip():
            self.update_chat_history(user_input, "User")
            self.worker = Worker(user_input)
            self.worker.finished.connect(self.handle_finished_response)
            self.worker.error.connect(lambda: self.show_error("Failed to send message. Check your connection."))
            self.worker.start()
            self.send_button.setText("Sending...")
            self.send_button.setEnabled(False)
            self.input_line.setReadOnly(True)

    def handle_finished_response(self, msg, success):
        if success:
            self.update_chat_history(msg, "AI")
            self.input_line.clear()
            self.input_line.setReadOnly(False)
            self.send_button.setText("Send")
        else:
            self.send_button.setText("Try Again")
            self.show_error_in_chat("Click 'Try Again' to resend the message.")
        self.send_button.setEnabled(True)

    def reset_send_button(self):
        self.send_button.setText("Send")
        self.send_button.setEnabled(True)

    def update_chat_history(self, message, sender):
        cursor = self.chat_history.textCursor()
        cursor.movePosition(QTextCursor.End)
        text_color = "#0078D7" if sender == "User" else "#4A4A4A"
        cursor.insertHtml(f'<div style="color: {text_color};">{message}</div><br>')
        self.chat_history.setTextCursor(cursor)
        self.chat_history.ensureCursorVisible()

    def show_error_in_chat(self, error_message):
        self.chat_history.append(f'<div style="color: red;">{error_message}</div>')
        self.input_line.setReadOnly(False)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    chat_app = ChatApp()
    chat_app.show()
    sys.exit(app.exec_())
