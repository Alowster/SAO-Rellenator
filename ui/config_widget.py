from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QFormLayout, QLineEdit, QDoubleSpinBox,
    QTextEdit, QPushButton, QHBoxLayout, QVBoxLayout, QFileDialog,
    QLabel, QCheckBox,
)
from PySide6.QtCore import Signal

from core.config_manager import AppConfig, load_config, save_config, validate_config, ConfigError

CONFIG_PATH = "config.json"


class ConfigWidget(QWidget):
    config_saved = Signal(object)  # AppConfig

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._try_autoload()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        form = QFormLayout()
        form.setSpacing(6)

        self.usuario_edit = QLineEdit()

        self.password_edit = QLineEdit()

        self.ollama_url_edit = QLineEdit()
        self.ollama_url_edit.setPlaceholderText("http://localhost:11434")

        self.model_edit = QLineEdit()
        self.model_edit.setPlaceholderText("gemma3:4b")

        self.temp_spin = QDoubleSpinBox()
        self.temp_spin.setRange(0.0, 1.0)
        self.temp_spin.setSingleStep(0.1)
        self.temp_spin.setDecimals(1)
        self.temp_spin.setValue(0.7)

        self.prompt_edit = QTextEdit()
        self.prompt_edit.setFixedHeight(80)
        self.prompt_edit.setPlaceholderText("Instrucciones base para el modelo (describe el trabajo de prácticas)...")

        form.addRow("Usuario foremp:", self.usuario_edit)
        form.addRow("Contraseña foremp:", self.password_edit)
        form.addRow("URL Ollama:", self.ollama_url_edit)
        form.addRow("Modelo:", self.model_edit)
        form.addRow("Temperatura:", self.temp_spin)
        form.addRow("Prompt de sistema:", self.prompt_edit)

        self.cerrar_ollama_check = QCheckBox("Cerrar Ollama al salir de la aplicación")
        form.addRow("", self.cerrar_ollama_check)

        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: red;")
        self.error_label.setWordWrap(True)
        self.error_label.hide()

        btn_layout = QHBoxLayout()
        self.load_btn = QPushButton("Cargar desde archivo")
        self.save_btn = QPushButton("Guardar configuración")
        btn_layout.addWidget(self.load_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.save_btn)

        layout.addLayout(form)
        layout.addWidget(self.error_label)
        layout.addLayout(btn_layout)

        self.load_btn.clicked.connect(self._on_load)
        self.save_btn.clicked.connect(self._on_save)

    def _try_autoload(self):
        if Path(CONFIG_PATH).exists():
            try:
                config = load_config(CONFIG_PATH)
                self._populate(config)
            except ConfigError:
                pass

    def _populate(self, config: AppConfig):
        self.usuario_edit.setText(config.usuario)
        self.password_edit.setText(config.password)
        self.ollama_url_edit.setText(config.ollama_url)
        self.model_edit.setText(config.llm_model)
        self.temp_spin.setValue(config.llm_temperatura)
        self.prompt_edit.setPlainText(config.llm_prompt_sistema)
        self.cerrar_ollama_check.setChecked(config.cerrar_ollama_al_salir)

    def _collect(self) -> AppConfig:
        return AppConfig(
            usuario=self.usuario_edit.text().strip(),
            password=self.password_edit.text(),
            ollama_url=self.ollama_url_edit.text().strip() or "http://localhost:11434",
            llm_model=self.model_edit.text().strip() or "gemma3:4b",
            llm_temperatura=self.temp_spin.value(),
            llm_prompt_sistema=self.prompt_edit.toPlainText().strip(),
            cerrar_ollama_al_salir=self.cerrar_ollama_check.isChecked(),
        )

    def _on_load(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar archivo de configuración", "", "JSON (*.json)"
        )
        if not path:
            return
        try:
            config = load_config(path)
            self._populate(config)
            self.error_label.hide()
        except ConfigError as e:
            self._show_error(str(e))

    def _on_save(self):
        config = self._collect()
        errors = validate_config(config)
        if errors:
            self._show_error(f"Campos obligatorios vacíos: {', '.join(errors)}")
            return
        try:
            save_config(config, CONFIG_PATH)
            self.error_label.hide()
            self.config_saved.emit(config)
        except Exception as e:
            self._show_error(f"Error al guardar: {e}")

    def _show_error(self, msg: str):
        self.error_label.setText(msg)
        self.error_label.show()

    def get_config(self) -> AppConfig | None:
        config = self._collect()
        if validate_config(config):
            return None
        return config
