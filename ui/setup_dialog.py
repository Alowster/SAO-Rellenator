from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton, QHBoxLayout,
)
from PySide6.QtCore import Qt, QThread, Signal, QObject
from PySide6.QtGui import QFont

from core import setup_checker

STEP_PENDING  = "⏳"
STEP_OK       = "✅"
STEP_ERROR    = "❌"
STEP_RUNNING  = "🔄"


class _SetupWorker(QObject):
    step_update = Signal(int, str, str)   # índice, icono, detalle
    progress    = Signal(int)             # 0-100, -1 = indeterminado
    finished    = Signal(bool, str)       # ok, mensaje

    def __init__(self, model: str, ollama_url: str):
        super().__init__()
        self._model = model
        self._ollama_url = ollama_url

    def run(self):
        # 1 — Ollama corriendo?
        self.step_update.emit(0, STEP_RUNNING, "Comprobando servicio Ollama...")
        if setup_checker.is_ollama_running():
            self.step_update.emit(0, STEP_OK, "Ollama está en ejecución.")
        else:
            # Intentar arrancar si está instalado
            exe = setup_checker.find_ollama_exe()
            if exe:
                self.step_update.emit(0, STEP_RUNNING, "Iniciando Ollama...")
                if setup_checker.start_ollama(exe):
                    self.step_update.emit(0, STEP_OK, "Ollama iniciado.")
                else:
                    self.step_update.emit(0, STEP_ERROR, "No se pudo iniciar Ollama.")
                    self.finished.emit(False, "No se pudo iniciar Ollama.")
                    return
            else:
                # Descargar e instalar
                self.step_update.emit(0, STEP_RUNNING, "Descargando instalador de Ollama...")
                try:
                    installer = setup_checker.download_ollama(
                        lambda pct: self.progress.emit(pct)
                    )
                    self.progress.emit(100)
                    self.step_update.emit(0, STEP_RUNNING, "Instalando Ollama...")
                    if not setup_checker.install_ollama(installer):
                        raise RuntimeError("El instalador finalizó con error.")
                    installer.unlink(missing_ok=True)  # eliminar instalador
                    self.step_update.emit(0, STEP_RUNNING, "Iniciando Ollama...")
                    exe = setup_checker.find_ollama_exe()
                    if not exe or not setup_checker.start_ollama(exe):
                        raise RuntimeError("No se pudo iniciar Ollama tras la instalación.")
                    self.step_update.emit(0, STEP_OK, "Ollama instalado e iniciado.")
                except Exception as e:
                    self.step_update.emit(0, STEP_ERROR, str(e))
                    self.finished.emit(False, str(e))
                    return

        # 2 — Modelo disponible?
        self.step_update.emit(1, STEP_RUNNING, f"Comprobando modelo {self._model}...")
        self.progress.emit(-1)
        if setup_checker.is_model_available(self._model, self._ollama_url):
            self.step_update.emit(1, STEP_OK, f"Modelo {self._model} disponible.")
        else:
            self.step_update.emit(1, STEP_RUNNING, f"Descargando {self._model}...")
            try:
                def _on_progress(status, pct):
                    label = status or ""
                    if pct >= 0:
                        label += f" {pct}%"
                        self.progress.emit(pct)
                    else:
                        self.progress.emit(-1)
                    self.step_update.emit(1, STEP_RUNNING, label)

                setup_checker.pull_model(self._model, self._ollama_url, _on_progress)
                self.step_update.emit(1, STEP_OK, f"Modelo {self._model} descargado.")
            except Exception as e:
                self.step_update.emit(1, STEP_ERROR, str(e))
                self.finished.emit(False, str(e))
                return

        self.progress.emit(100)
        self.finished.emit(True, "Todo listo.")


class SetupDialog(QDialog):
    def __init__(self, model: str = "gemma3:4b", ollama_url: str = "http://localhost:11434", parent=None):
        super().__init__(parent)
        self._model = model
        self._ollama_url = ollama_url
        self.setWindowTitle("Configuración inicial")
        self.setMinimumWidth(440)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint)
        self._ready = False
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("Comprobando requisitos...")
        font = QFont()
        font.setBold(True)
        font.setPointSize(11)
        title.setFont(font)
        layout.addWidget(title)

        self._step_labels = []
        self._detail_labels = []
        steps = ["Ollama", f"Modelo {self._model}"]
        for name in steps:
            row = QHBoxLayout()
            icon = QLabel(STEP_PENDING)
            icon.setFixedWidth(24)
            step_lbl = QLabel(f"<b>{name}</b>")
            detail_lbl = QLabel("Pendiente")
            detail_lbl.setStyleSheet("color: gray;")
            row.addWidget(icon)
            row.addWidget(step_lbl)
            row.addStretch()
            row.addWidget(detail_lbl)
            layout.addLayout(row)
            self._step_labels.append(icon)
            self._detail_labels.append(detail_lbl)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        layout.addWidget(self._progress)

        self._status = QLabel("")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._close_btn = QPushButton("Continuar")
        self._close_btn.setEnabled(False)
        self._close_btn.clicked.connect(self.accept)
        btn_row.addWidget(self._close_btn)
        layout.addLayout(btn_row)

    def run_setup(self):
        self._worker = _SetupWorker(self._model, self._ollama_url)
        self._thread = QThread()
        self._worker.moveToThread(self._thread)

        self._worker.step_update.connect(self._on_step_update)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._thread.quit)

        self._thread.start()

    def _on_step_update(self, idx: int, icon: str, detail: str):
        self._step_labels[idx].setText(icon)
        self._detail_labels[idx].setText(detail)
        color = "green" if icon == STEP_OK else ("red" if icon == STEP_ERROR else "black")
        self._detail_labels[idx].setStyleSheet(f"color: {color};")

    def _on_progress(self, pct: int):
        if pct < 0:
            self._progress.setRange(0, 0)  # indeterminado
        else:
            self._progress.setRange(0, 100)
            self._progress.setValue(pct)

    def _on_finished(self, ok: bool, msg: str):
        self._progress.setRange(0, 100)
        self._progress.setValue(100 if ok else 0)
        if ok:
            self._status.setText("✅ Todo listo. Puedes continuar.")
            self._status.setStyleSheet("color: green;")
            self._ready = True
        else:
            self._status.setText(f"❌ Error: {msg}")
            self._status.setStyleSheet("color: red;")
        self._close_btn.setEnabled(True)

    def is_ready(self) -> bool:
        return self._ready
