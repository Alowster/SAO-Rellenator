from __future__ import annotations

from datetime import datetime

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton
from PySide6.QtGui import QTextCursor, QColor
from PySide6.QtCore import Qt

LEVEL_COLORS = {
    "info": "#cccccc",
    "success": "#44bb77",
    "ok": "#44bb77",
    "error": "#ee4444",
}


class LogWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setFont(self._monospace_font())
        self.log_edit.setStyleSheet("background-color: #1e1e1e;")
        layout.addWidget(self.log_edit)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        clear_btn = QPushButton("Limpiar log")
        clear_btn.clicked.connect(self.log_edit.clear)
        btn_row.addWidget(clear_btn)
        layout.addLayout(btn_row)

    @staticmethod
    def _monospace_font():
        from PySide6.QtGui import QFont
        font = QFont("Consolas")
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPointSize(9)
        return font

    def append_log(self, message: str, level: str = "info"):
        ts = datetime.now().strftime("%H:%M:%S")
        tag = level.upper().ljust(7)
        if level in ("success", "ok"):
            tag = "OK".ljust(7)
        line = f"[{ts}] [{tag}] {message}"

        color = LEVEL_COLORS.get(level.lower(), "#cccccc")

        cursor = self.log_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        fmt = cursor.charFormat()
        fmt.setForeground(QColor(color))
        cursor.setCharFormat(fmt)
        cursor.insertText(line + "\n")

        self.log_edit.setTextCursor(cursor)
        self.log_edit.ensureCursorVisible()
