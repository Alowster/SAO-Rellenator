from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton,
)
from PySide6.QtCore import Signal, Qt, QObject, QThread

from core.config_manager import AppConfig
from core.llm_client import generate_description, LLMError

MAX_CHARS = 240


class _GenerationWorker(QObject):
    chunk = Signal(str)
    finished = Signal()
    error = Signal(str)

    def __init__(self, config: AppConfig, fecha: date | None):
        super().__init__()
        self._config = config
        self._fecha = fecha

    def run(self):
        try:
            import ollama
            from datetime import date as _date
            from core.foremp_reader import read_week_entries

            client = ollama.Client(host=self._config.ollama_url)
            fecha = self._fecha or _date.today()
            fecha_str = fecha.strftime("%d/%m/%Y")

            # Leer entradas de la semana como contexto (falla silenciosamente)
            context_block = ""
            try:
                week_entries = read_week_entries(self._config, fecha)
                if week_entries:
                    lines = "\n".join(
                        f"- {d.strftime('%A %d/%m/%Y')}: \"{desc}\""
                        for d, desc in sorted(week_entries.items())
                    )
                    context_block = (
                        f"\nDescripciones ya escritas esta semana:\n{lines}\n"
                        "Genera algo diferente, variado y coherente con lo anterior.\n"
                    )
            except Exception:
                pass

            prompt = (
                f"Genera la descripción del diario de prácticas para el día {fecha_str}."
                f"{context_block}"
                "La respuesta no debe superar 240 caracteres."
            )

            for part in client.generate(
                model=self._config.llm_model,
                prompt=prompt,
                system=self._config.llm_prompt_sistema or None,
                options={"temperature": self._config.llm_temperatura},
                keep_alive=0,
                stream=True,
            ):
                self.chunk.emit(part.response)
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))


class IAWidget(QWidget):
    text_ready = Signal(str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._config: AppConfig | None = None
        self._fecha: date | None = None
        self._thread: QThread | None = None
        self._worker: _GenerationWorker | None = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self.generate_btn = QPushButton("Generar descripción")
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.generate_btn)
        btn_row.addWidget(self.status_label)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        layout.addWidget(QLabel("Descripción generada (editable):"))
        self.result_edit = QTextEdit()
        self.result_edit.setFixedHeight(70)
        self.result_edit.setPlaceholderText("Aquí aparecerá el texto generado...")
        layout.addWidget(self.result_edit)

        self.counter_label = QLabel(f"0 / {MAX_CHARS}")
        self.counter_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.counter_label)

        self.generate_btn.clicked.connect(self._on_generate)
        self.result_edit.textChanged.connect(self._on_text_changed)

    def set_config(self, config: AppConfig):
        self._config = config

    def set_fecha(self, fecha: date):
        self._fecha = fecha

    def _on_generate(self):
        if not self._config:
            self.status_label.setText("Sin configuración guardada.")
            return

        self.generate_btn.setEnabled(False)
        self.status_label.setText("Leyendo semana...")

        self._worker = _GenerationWorker(self._config, self._fecha)
        self._thread = QThread()
        self._worker.moveToThread(self._thread)

        self._worker.chunk.connect(self._on_chunk)
        self._worker.finished.connect(self._on_generation_done)
        self._worker.error.connect(self._on_generation_error)
        self._thread.started.connect(self._worker.run)
        self._worker.chunk.connect(lambda _: self.status_label.setText("Generando..."))
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.finished.connect(self._thread.deleteLater)

        self.result_edit.clear()
        self._thread.start()

    def _on_chunk(self, text: str):
        cursor = self.result_edit.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(text)
        self.result_edit.setTextCursor(cursor)

    def _on_generation_done(self):
        self.status_label.setText("")
        self.generate_btn.setEnabled(True)

    def _on_generation_error(self, msg: str):
        self.status_label.setText(f"Error: {msg}")
        self.generate_btn.setEnabled(True)

    def _on_text_changed(self):
        text = self.result_edit.toPlainText()
        count = len(text)
        valid = count <= MAX_CHARS
        self.counter_label.setText(f"{count} / {MAX_CHARS}")
        self.counter_label.setStyleSheet("" if valid else "color: red;")
        self.text_ready.emit(text, valid)

    def get_text(self) -> str:
        return self.result_edit.toPlainText()
