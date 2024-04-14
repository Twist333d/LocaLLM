import os

import markdown
import requests
from PyQt5.QtCore import QThread, pyqtSignal


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
