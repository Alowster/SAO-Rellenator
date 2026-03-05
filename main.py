import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from core.config_manager import AppConfig, load_config, ConfigError
from ui.setup_dialog import SetupDialog
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("SAÓ-Rellenator")

    icon_path = Path(__file__).parent / "assets" / "icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # Leer config para saber qué modelo y URL usar en el setup
    try:
        config = load_config()
    except ConfigError:
        config = AppConfig()  # valores por defecto si no existe aún

    setup = SetupDialog(model=config.llm_model, ollama_url=config.ollama_url)
    setup.run_setup()
    setup.exec()

    if not setup.is_ready():
        sys.exit(1)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
