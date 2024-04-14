import sys
import os
from datetime import datetime

import markdown
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QEvent
from PyQt5.QtGui import QFont, QTextCursor, QIcon
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QPushButton, QTextEdit, QWidget, QAction, QMenu

import requests
import urllib3

# Suppressing less secure warnings for demonstration; handle appropriately in production
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Worker(QThread):
    finished = pyqtSignal(str, bool)  # Emit message content (as HTML) and a boolean for success

    def __init__(self, prompt):
        super().__init__()
        self.prompt = prompt

    def run(self):
        response, success = self.call_openai_api(self.prompt)
        if success:
            html_content = markdown.markdown(response, extensions=['fenced_code', 'tables'])
            self.finished.emit(html_content, True)
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
            response = requests.post(url, json=data, headers=headers, timeout=10)
            response.raise_for_status()  # Handle HTTP errors
            response_data = response.json()
            message_content = response_data['choices'][0]['message']['content']
            return message_content, True
        except requests.RequestException as e:
            return f"An error occurred: {str(e)}", False


class ChatApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.title = 'OpenAI GPT Chat'
        self.initUI()
        self.setStyleSheet("background-color: #f0f0f0;")
        self.setWindowIcon(QIcon('app_icon.png'))  # Make sure 'app_icon.png' is available

    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(100, 100, 480, 640)
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setSpacing(10)
        self.layout.setContentsMargins(10, 10, 10, 10)

        self.create_chat_history()
        self.create_input_area()
        self.create_send_button()
        self.create_formatting_actions()

    def create_chat_history(self):
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setFont(QFont('Arial', 14))
        self.chat_history.setStyleSheet("background-color: #ffffff; color: #444; padding: 10px;")
        self.layout.addWidget(self.chat_history, 5)

    def create_input_area(self):
        self.input_line = QTextEdit()
        self.input_line.setFont(QFont('Arial', 14))
        self.input_line.setPlaceholderText("Type your message here... Use HTML tags for formatting.")
        self.input_line.setStyleSheet("background-color: #ffffff; color: #444; padding: 10px;")
        self.input_line.setMaximumHeight(100)
        self.layout.addWidget(self.input_line, 1)
        self.input_line.installEventFilter(self)

    def create_send_button(self):
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_message)
        self.send_button.setStyleSheet(
            "background-color: #0078d7; color: white; font-weight: bold; padding: 10px; border: none;")
        self.layout.addWidget(self.send_button, 1)

    def create_formatting_actions(self):
        self.menu = self.menuBar().addMenu("Format")
        bold_action = QAction("Bold", self)
        code_action = QAction("Code", self)
        bullet_action = QAction("Bullet Point", self)

        bold_action.triggered.connect(lambda: self.format_text('bold'))
        code_action.triggered.connect(lambda: self.format_text('code'))
        bullet_action.triggered.connect(lambda: self.format_text('bullet'))

        self.menu.addAction(bold_action)
        self.menu.addAction(code_action)
        self.menu.addAction(bullet_action)

    def format_text(self, format_type):
        cursor = self.input_line.textCursor()
        if format_type == 'bold':
            cursor.mergeCharFormat(QtGui.QTextCharFormat.setFontWeight(QtGui.QFont.Bold))
        elif format_type == 'code':
            cursor.insertHtml('<code>{}</code>'.format(cursor.selectedText()))
        elif format_type == 'bullet':
            cursor.insertHtml('<ul><li>{}</li></ul>'.format(cursor.selectedText()))

    def eventFilter(self, source, event):
        if event.type() == QEvent.KeyPress and source is self.input_line:
            if event.key() in [Qt.Key_Return, Qt.Key_Enter]:
                if QApplication.keyboardModifiers() == Qt.ControlModifier:
                    self.send_message()
                    return True
                else:
                    self.input_line.append('')
                    return True
        return super().eventFilter(source, event)

    def send_message(self):
        user_input = self.input_line.toHtml()
        if user_input.strip():
            self.update_chat_history(user_input, "User")
            self.worker = Worker(user_input)
            self.worker.finished.connect(self.handle_finished_response)
            self.worker.start()
            self.send_button.setText("Sending...")
            self.send_button.setEnabled(False)
            self.input_line.setReadOnly(True)

    def handle_finished_response(self, msg, success):
        self.send_button.setText("Send")
        self.send_button.setEnabled(True)
        self.input_line.setReadOnly(False)
        if success:
            self.update_chat_history(msg, "AI")
        else:
            self.update_chat_history("Error: Could not fetch response.", "System")

    def update_chat_history(self, message, sender):
        cursor = self.chat_history.textCursor()
        cursor.movePosition(QTextCursor.End)
        text_color = "#0078D7" if sender == "User" else "#4A4A4A"
        cursor.insertHtml('<div style="color: {};">{}</div><br>'.format(text_color, message))
        self.chat_history.ensureCursorVisible()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    chat_app = ChatApp()
    chat_app.show()
    sys.exit(app.exec_())
