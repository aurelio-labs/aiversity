import sys
import os
import asyncio
import json
import aiohttp
from aiohttp import ClientSession
import qasync
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QListWidget, QLabel, QTextBrowser, QLineEdit, 
                             QPushButton, QSplitter, QListWidgetItem, 
                             QFileIconProvider, QAbstractItemView, QScrollArea)
from PyQt5.QtCore import Qt, QFileInfo, QSize, QDateTime, QTimer
from PyQt5.QtGui import QIcon, QPixmap, QColor, QPalette

class AutoScrollTextBrowser(QTextBrowser):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

    def append(self, text):
        super().append(text)
        self.scroll_to_bottom()

    def scroll_to_bottom(self):
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())

class CustomListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QListWidget {
                background-color: #2B2B2B;
                border: 1px solid #444444;
                border-radius: 5px;
                padding: 5px;
                font-size: 14px;
                color: #FFFFFF;
            }
            QListWidget::item {
                padding: 10px;
            }
            QListWidget::item:selected {
                background-color: #444444;
            }
        """)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            self.delete_selected_items()
        else:
            super().keyPressEvent(event)

    def delete_selected_items(self):
        for item in self.selectedItems():
            self.takeItem(self.row(item))

class SharedWorkspace(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Shared Workspace")
        self.setGeometry(100, 100, 800, 600)
        self.setup_palette()

        main_layout = QHBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.create_workspace_widget())
        splitter.addWidget(self.create_chat_widget())

        main_layout.addWidget(splitter)
        self.setLayout(main_layout)

        self.setup_animations()

    def setup_palette(self):
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ToolTipBase, Qt.black)
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, Qt.black)
        self.setPalette(palette)

    def create_workspace_widget(self):
        workspace_widget = QWidget()
        workspace_layout = QVBoxLayout()
        workspace_layout.setSpacing(10)

        workspace_label = QLabel("Shared Workspace")
        workspace_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFFFFF; margin-bottom: 10px;")
        workspace_layout.addWidget(workspace_label)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("border: none;")

        self.list_widget = CustomListWidget()
        self.setup_list_widget()

        scroll_area.setWidget(self.list_widget)
        workspace_layout.addWidget(scroll_area)

        delete_button = QPushButton("Delete Selected")
        delete_button.setIcon(QIcon("delete.png"))
        delete_button.setStyleSheet("""
            QPushButton {
                background-color: #FF4136;
                color: #FFFFFF;
                border: none;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #FF725C;
            }
        """)
        delete_button.clicked.connect(self.list_widget.delete_selected_items)
        workspace_layout.addWidget(delete_button)

        workspace_widget.setLayout(workspace_layout)
        workspace_widget.setStyleSheet("background-color: #333333; border-radius: 10px; padding: 10px;")
        return workspace_widget

    def setup_list_widget(self):
        self.list_widget.setAcceptDrops(True)
        self.list_widget.setDragEnabled(True)
        self.list_widget.setDefaultDropAction(Qt.CopyAction)
        self.list_widget.setViewMode(QListWidget.IconMode)
        self.list_widget.setIconSize(QSize(64, 64))
        self.list_widget.setResizeMode(QListWidget.Adjust)
        self.list_widget.setSelectionMode(QAbstractItemView.MultiSelection)

    def create_chat_widget(self):
        chat_widget = QWidget()
        chat_layout = QVBoxLayout()
        chat_layout.setSpacing(10)

        chat_label = QLabel("Chat with Triage Agent")
        chat_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #FFFFFF; margin-bottom: 10px;")
        chat_layout.addWidget(chat_label)

        self.chat_history = AutoScrollTextBrowser()
        self.chat_history.setStyleSheet("""
            QTextBrowser {
                background-color: #2B2B2B;
                color: #FFFFFF;
                border: 1px solid #444444;
                border-radius: 5px;
                padding: 10px;
                font-size: 14px;
            }
        """)
        chat_layout.addWidget(self.chat_history)

        input_layout = QHBoxLayout()
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Type your message...")
        self.chat_input.setStyleSheet("""
            QLineEdit {
                background-color: #444444;
                color: #FFFFFF;
                border: none;
                padding: 10px;
                font-size: 14px;
                border-radius: 5px;
            }
        """)
        self.chat_input.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.chat_input)

        send_button = QPushButton("Send")
        send_button.setIcon(QIcon("send.png"))
        send_button.setStyleSheet("""
            QPushButton {
                background-color: #2ECC40;
                color: #FFFFFF;
                border: none;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #01FF70;
            }
        """)
        send_button.clicked.connect(self.send_message)
        input_layout.addWidget(send_button)

        chat_layout.addLayout(input_layout)

        chat_widget.setLayout(chat_layout)
        chat_widget.setStyleSheet("background-color: #333333; border-radius: 10px; padding: 10px;")
        return chat_widget

    def setup_animations(self):
        self.processing_animation_timer = QTimer()
        self.processing_animation_timer.timeout.connect(self.update_processing_animation)
        self.processing_animation_frames = ['|', '/', '-', '\\']
        self.current_frame_index = 0

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        icon_provider = QFileIconProvider()
        for file in files:
            file_info = QFileInfo(file)
            file_name = self.truncate_filename(os.path.basename(file))

            if file_info.isDir():
                icon = icon_provider.icon(QFileIconProvider.Folder)
            elif file_info.suffix().lower() in ['png', 'jpg', 'jpeg', 'gif', 'bmp']:
                pixmap = QPixmap(file)
                icon = QIcon(pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                icon = icon_provider.icon(file_info)

            item = QListWidgetItem(icon, file_name)
            self.list_widget.addItem(item)

    def truncate_filename(self, filename, max_length=20, start_chars=10, end_chars=5):
        if len(filename) > max_length:
            return f"{filename[:start_chars]}...{filename[-end_chars:]}"
        return filename

    def update_processing_animation(self):
        self.current_frame_index = (self.current_frame_index + 1) % len(self.processing_animation_frames)
        current_frame = self.processing_animation_frames[self.current_frame_index]

        cursor = self.chat_history.textCursor()
        cursor.movePosition(cursor.End)
        
        # Find the processing animation span
        cursor.movePosition(cursor.StartOfBlock, cursor.KeepAnchor)
        selected_text = cursor.selectedText()
        
        animation_start = selected_text.find("Processing ")
        if animation_start != -1:
            # Remove only the existing animation frame
            new_text = f"{selected_text[:animation_start]}Processing {current_frame}"
            cursor.removeSelectedText()
            cursor.insertHtml(new_text)
        else:
            # If not found, insert a new processing message
            cursor.movePosition(cursor.End)
            cursor.insertHtml(f"<br><span style='color: #FFFFFF;'>Processing {current_frame}</span>")

        # Ensure the view scrolls to show the latest text
        self.chat_history.ensureCursorVisible()


    def triage_agent_response(self, response_message):
        # Stop the animation timer
        self.processing_animation_timer.stop()

        # Remove the processing message if it exists
        cursor = self.chat_history.textCursor()
        cursor.movePosition(cursor.End)
        cursor.movePosition(cursor.StartOfBlock, cursor.KeepAnchor)
        selected_text = cursor.selectedText()
        
        if "Processing" in selected_text:
            cursor.removeSelectedText()
        else:
            cursor.movePosition(cursor.End)

        try:
            # Parse the JSON response
            response_data = json.loads(response_message)
            sender = response_data.get("sender", "Triage Agent")
            content = response_data.get("content", "")
            timestamp = response_data.get("time_utc", "")

            # Convert UTC time to local time
            utc_time = QDateTime.fromString(timestamp, Qt.ISODate)
            local_time = utc_time.toLocalTime()
            formatted_time = local_time.toString("yyyy-MM-dd HH:mm:ss")

            # Insert the agent's response
            self.chat_history.append(f"<span style='color: #2ECC40;'>[{formatted_time}] {sender}:</span> {content}")
        except json.JSONDecodeError:
            # If JSON parsing fails, display the raw message
            timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss")
            self.chat_history.append(f"<span style='color: #2ECC40;'>[{timestamp}] Triage Agent:</span> {response_message}")

        # Ensure the view scrolls to show the latest text
        self.chat_history.ensureCursorVisible()

    def send_message(self):
        message = self.chat_input.text().strip()
        if message:
            timestamp = QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss")
            self.chat_history.append(f"<span style='color: #7FDBFF;'>[{timestamp}] User:</span> {message}")
            self.chat_history.append(f"<span style='color: #FFFFFF;'>Processing {self.processing_animation_frames[0]}</span>")
            asyncio.create_task(self.send_message_to_backend(message))
            self.chat_input.clear()
            self.processing_animation_timer.start(100)  # Update every 100ms


    async def send_message_to_backend(self, message):
        url = "http://localhost:5000/chat/"
        async with ClientSession() as session:
            async with session.post(url, json={"message": message}):
                pass

    async def receive_messages(self):
        url = "ws://localhost:5000/ws-chat/"
        async with ClientSession() as session:
            async with session.ws_connect(url) as websocket:
                while True:
                    message = await websocket.receive()
                    if message.type == aiohttp.WSMsgType.TEXT:
                        self.triage_agent_response(message.data)
                    elif message.type == aiohttp.WSMsgType.CLOSED:
                        break
                    elif message.type == aiohttp.WSMsgType.ERROR:
                        print("WebSocket connection closed with exception:", websocket.exception())
                        break


if __name__ == "__main__":
    app = QApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    workspace = SharedWorkspace()
    workspace.show()

    if sys.platform == "darwin":
        workspace.setAcceptDrops(True)
        workspace.installEventFilter(workspace)

    with loop:
        loop.create_task(workspace.receive_messages())
        loop.run_forever()