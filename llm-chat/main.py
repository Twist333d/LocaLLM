from PyQt5.QtWidgets import QApplication
from chatwindow import ChatApp

def main():
    app = QApplication([])
    chat_app = ChatApp()
    chat_app.show()
    app.exec_()

if __name__ == "__main__":
    main()
