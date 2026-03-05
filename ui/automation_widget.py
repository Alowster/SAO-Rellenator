from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QDateEdit, QCheckBox, QPushButton, QSpinBox,
)
from PySide6.QtCore import Signal, QDate, QThread

from core.config_manager import AppConfig
from core.selenium_bot import ForempBot
from ui.log_widget import LogWidget


class AutomationWidget(QWidget):
    bot_started = Signal()
    bot_finished = Signal(bool, str)

    def __init__(self, log_widget: LogWidget, parent=None):
        super().__init__(parent)
        self._log_widget = log_widget
        self._config: AppConfig | None = None
        self._text: str = ""
        self._text_valid: bool = False
        self._thread: QThread | None = None
        self._bot: ForempBot | None = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        row = QHBoxLayout()
        row.addWidget(QLabel("Fecha:"))
        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd/MM/yyyy")
        row.addWidget(self.date_edit)
        row.addSpacing(20)
        row.addWidget(QLabel("Horas realizadas:"))
        self.horas_spin = QSpinBox()
        self.horas_spin.setRange(0, 24)
        self.horas_spin.setValue(8)
        self.horas_spin.setSuffix(" h")
        row.addWidget(self.horas_spin)
        row.addStretch()
        layout.addLayout(row)

        self.headless_check = QCheckBox("Ejecutar en modo headless (sin ventana)")
        self.headless_check.setChecked(True)
        layout.addWidget(self.headless_check)

        self.execute_btn = QPushButton("Ejecutar en foremp")
        self.execute_btn.setEnabled(False)
        layout.addWidget(self.execute_btn)

        self.execute_btn.clicked.connect(self._on_execute)

    def set_config(self, config: AppConfig):
        self._config = config

    def set_text_valid(self, text: str, valid: bool):
        self._text = text
        self._text_valid = valid
        self._update_btn()

    def _update_btn(self):
        self.execute_btn.setEnabled(
            self._text_valid and bool(self._text) and self._config is not None
        )

    def _on_execute(self):
        if not self._config or not self._text_valid:
            return

        qdate = self.date_edit.date()
        fecha = date(qdate.year(), qdate.month(), qdate.day())
        headless = self.headless_check.isChecked()

        horas = self.horas_spin.value()
        self._bot = ForempBot(self._config, self._text, fecha, horas, headless)
        self._thread = QThread()
        self._bot.moveToThread(self._thread)

        self._bot.log_signal.connect(self._log_widget.append_log)
        self._bot.finished.connect(self._on_bot_finished)
        self._thread.started.connect(self._bot.run)

        self.execute_btn.setEnabled(False)
        self.bot_started.emit()
        self._thread.start()

    def _on_bot_finished(self, success: bool, msg: str):
        self._thread.quit()
        self._thread.wait()
        self._thread = None
        self._bot = None
        self._update_btn()
        self.bot_finished.emit(success, msg)
