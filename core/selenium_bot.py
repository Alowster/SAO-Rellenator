from __future__ import annotations

from datetime import date

from PySide6.QtCore import QObject, Signal

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

from core.config_manager import AppConfig

BASE_URL = "https://foremp.edu.gva.es"
TIMEOUT = 10


class ForempBot(QObject):
    log_signal = Signal(str, str)   # message, level: 'info'|'success'|'error'
    finished = Signal(bool, str)    # success, message

    def __init__(self, config: AppConfig, texto: str, fecha: date, horas: int = 8, headless: bool = True):
        super().__init__()
        self._config = config
        self._texto = texto
        self._fecha = fecha
        self._horas = horas
        self._headless = headless
        self._driver: webdriver.Chrome | None = None

    def run(self):
        try:
            self._init_driver()
            n = self._execute()
            self._quit()
            if n is not None:
                self.finished.emit(True, "Entrada del diario modificada correctamente.")
        except BotError as e:
            self._quit()
            self.finished.emit(False, str(e))
        except Exception as e:
            self._quit()
            self.finished.emit(False, f"Error inesperado: {e}")

    # ------------------------------------------------------------------
    def _execute(self) -> int:
        self.login()
        self.navigate_to_fct()
        n = self.find_diary_entry(self._fecha)
        self.click_modify(n)
        form_id = self._detect_form_id()
        self.fill_description(self._texto, form_id)
        self.fill_hours(self._horas, form_id)
        self.confirm(form_id)
        self.verify_success(form_id)
        return n

    def _detect_form_id(self) -> int:
        """Detecta el ID numérico del textarea que se hizo visible tras pulsar modificar."""
        textarea = self._wait().until(
            EC.visibility_of_element_located((By.XPATH, '//textarea[starts-with(@id,"descripcion")]'))
        )
        return int(textarea.get_attribute("id").replace("descripcion", ""))

    def _init_driver(self):
        self._log("Iniciando ChromeDriver...", "info")
        options = webdriver.ChromeOptions()
        if self._headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        service = Service(ChromeDriverManager().install())
        self._driver = webdriver.Chrome(service=service, options=options)
        self._driver.implicitly_wait(0)

    def _quit(self):
        if self._driver:
            try:
                self._driver.quit()
            except Exception:
                pass
            self._driver = None

    def _wait(self):
        return WebDriverWait(self._driver, TIMEOUT)

    def _log(self, msg: str, level: str = "info"):
        self.log_signal.emit(msg, level)

    # ------------------------------------------------------------------
    def login(self):
        self._log(f"Navegando a {BASE_URL}...", "info")
        self._driver.get(BASE_URL)

        try:
            self._wait().until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[name="usuario"]')))
            self._driver.find_element(By.CSS_SELECTOR, 'input[name="usuario"]').clear()
            self._driver.find_element(By.CSS_SELECTOR, 'input[name="usuario"]').send_keys(self._config.usuario)
            self._driver.find_element(By.CSS_SELECTOR, 'input[name="password"]').clear()
            self._driver.find_element(By.CSS_SELECTOR, 'input[name="password"]').send_keys(self._config.password)
            self._driver.find_element(By.CSS_SELECTOR, 'input[type="submit"][name="login"]').click()

            # Login confirmado solo cuando el enlace FCT es visible en la página
            try:
                self._wait().until(EC.presence_of_element_located((By.XPATH, '//a[contains(@href,"op=2")]')))
            except Exception:
                raise BotError("Login fallido: credenciales incorrectas o la sesión no se estableció.")

            self._log("Login completado.", "success")
        except BotError:
            raise
        except Exception as e:
            raise BotError(f"Error en login: {e}")

    def navigate_to_fct(self):
        self._log("Navegando a FCT...", "info")
        try:
            self._driver.get(f"{BASE_URL}/index.php?op=2)")
            self._wait().until(EC.presence_of_element_located((By.CSS_SELECTOR, "p.diasDelDiario")))
            self._log("Sección FCT abierta.", "success")
        except Exception as e:
            raise BotError(f"No se pudo cargar la sección FCT: {e}")

    def find_diary_entry(self, fecha: date) -> int:
        fecha_str = fecha.strftime("%d/%m/%Y")
        self._log(f"Buscando entrada del {fecha_str}...", "info")
        try:
            self._wait().until(EC.presence_of_element_located((By.CSS_SELECTOR, "p.diasDelDiario")))
            # Buscar el enlace modificar cuyo href contiene la fecha en formato DD/MM/YYYY
            link = self._driver.find_element(
                By.XPATH,
                f"//a[starts-with(@id,'modificar') and contains(@href,\"'{fecha_str}'\")]"
            )
            n = int(link.get_attribute("id").replace("modificar", ""))
            self._log(f"Entrada encontrada (índice {n}).", "success")
            return n
        except NoSuchElementException:
            raise BotError(f"No se encontró una entrada para la fecha {fecha_str}.")
        except BotError:
            raise
        except Exception as e:
            raise BotError(f"Error al buscar la entrada del diario: {e}")

    def click_modify(self, n: int):
        self._log(f"Pulsando modificar (bloque {n})...", "info")
        try:
            btn = self._wait().until(
                EC.presence_of_element_located((By.CSS_SELECTOR, f"#modificar{n}"))
            )
            self._driver.execute_script("arguments[0].click();", btn)
            self._log("Formulario de modificación abierto.", "success")
        except Exception as e:
            raise BotError(f"No se encontró el botón modificar{n}: {e}")

    def fill_description(self, texto: str, form_id: int):
        self._log("Rellenando descripción...", "info")
        try:
            textarea = self._driver.find_element(By.CSS_SELECTOR, f"#descripcion{form_id}")
            textarea.clear()
            textarea.send_keys(texto)
            self._log("Descripción rellenada.", "success")
        except Exception as e:
            raise BotError(f"No se encontró el campo descripcion{form_id}: {e}")

    def fill_hours(self, horas: int, form_id: int):
        self._log(f"Rellenando horas ({horas}h)...", "info")
        try:
            field = self._driver.find_element(By.CSS_SELECTOR, f"#tiempo{form_id}")
            field.clear()
            field.send_keys(str(horas))
            self._log("Horas rellenadas.", "success")
        except Exception as e:
            raise BotError(f"No se encontró el campo tiempo{form_id}: {e}")

    def confirm(self, form_id: int):
        self._log("Confirmando cambios...", "info")
        try:
            btn = self._wait().until(
                EC.presence_of_element_located((By.CSS_SELECTOR, f"#aceptar{form_id}"))
            )
            self._driver.execute_script("arguments[0].click();", btn)
            self._log("Botón confirmar pulsado.", "success")
        except Exception as e:
            raise BotError(f"No se encontró el botón aceptar{form_id}: {e}")

    def verify_success(self, form_id: int):
        self._log("Verificando confirmación...", "info")
        try:
            self._wait().until(
                EC.text_to_be_present_in_element(
                    (By.CSS_SELECTOR, f"#diario{form_id} p"),
                    "Modificación realizada.",
                )
            )
            self._log("Modificación realizada correctamente.", "success")
        except Exception as e:
            raise BotError(f"No se encontró el mensaje de confirmación: {e}")


class BotError(Exception):
    pass
