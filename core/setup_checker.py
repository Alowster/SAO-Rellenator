from __future__ import annotations

import os
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path

OLLAMA_API = "http://localhost:11434"
OLLAMA_INSTALLER_URL = "https://ollama.com/download/OllamaSetup.exe"
OLLAMA_EXE_CANDIDATES = [
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe",
    Path(os.environ.get("PROGRAMFILES", ""))  / "Ollama" / "ollama.exe",
]


def is_ollama_running() -> bool:
    try:
        urllib.request.urlopen(OLLAMA_API, timeout=3)
        return True
    except Exception:
        return False


def find_ollama_exe() -> Path | None:
    for path in OLLAMA_EXE_CANDIDATES:
        if path.exists():
            return path
    exe = shutil.which("ollama")
    return Path(exe) if exe else None


def start_ollama(exe: Path) -> bool:
    try:
        subprocess.Popen(
            [str(exe), "serve"],
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        for _ in range(15):
            time.sleep(1)
            if is_ollama_running():
                return True
        return False
    except Exception:
        return False


def download_ollama(progress_cb=None) -> Path:
    dest = Path(os.environ.get("TEMP", ".")) / "OllamaSetup.exe"

    def _report(block, block_size, total):
        if progress_cb and total > 0:
            pct = min(100, int(block * block_size * 100 / total))
            progress_cb(pct)

    urllib.request.urlretrieve(OLLAMA_INSTALLER_URL, dest, _report)
    return dest


def install_ollama(installer: Path) -> bool:
    try:
        subprocess.Popen([str(installer)])
        # Esperar hasta que Ollama esté corriendo (el instalador lo lanza solo)
        for _ in range(60):
            time.sleep(2)
            if is_ollama_running():
                return True
        return False
    except Exception:
        return False


def kill_ollama() -> None:
    subprocess.run(
        ["taskkill", "/F", "/IM", "ollama.exe"],
        creationflags=subprocess.CREATE_NO_WINDOW,
        capture_output=True,
    )


def is_model_available(model: str, ollama_url: str = OLLAMA_API) -> bool:
    try:
        import ollama
        client = ollama.Client(host=ollama_url)
        models = client.list()
        return any(m.model.startswith(model.split(":")[0]) for m in models.models)
    except Exception:
        return False


def pull_model(model: str, ollama_url: str = OLLAMA_API, progress_cb=None) -> None:
    import ollama
    client = ollama.Client(host=ollama_url)
    for update in client.pull(model, stream=True):
        if progress_cb and update.total and update.total > 0:
            pct = int((update.completed or 0) * 100 / update.total)
            progress_cb(update.status, pct)
        elif progress_cb:
            progress_cb(update.status, -1)
