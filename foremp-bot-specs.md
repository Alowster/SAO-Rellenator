# foremp-bot — Plan de Proyecto y Especificaciones Técnicas

## 1. Descripción General

Aplicación de escritorio desarrollada en **Python + PySide6** para Windows que:

1. Gestiona una configuración persistente en JSON (credenciales + parámetros de IA)
2. Genera una descripción de diario de prácticas usando la **API de Google Gemini**
3. Automatiza el relleno de esa descripción en la plataforma **foremp.edu.gva.es** mediante **Selenium + Chrome**

---

## 2. Stack Tecnológico

| Capa | Tecnología |
|---|---|
| Interfaz gráfica | PySide6 (Qt for Python) |
| Automatización web | Selenium 4 + ChromeDriver |
| IA generativa | Google Gemini API (`google-generativeai`) |
| Configuración | JSON (fichero local `config.json`) |
| Concurrencia UI | `QThread` + señales Qt |
| Sistema operativo | Windows 10/11 |
| Python | 3.10+ |

---

## 3. Estructura de Archivos

```
foremp-bot/
│
├── main.py                  # Punto de entrada
├── config.json              # Generado por la app (gitignore)
├── requirements.txt         # Dependencias
│
├── core/
│   ├── __init__.py
│   ├── config_manager.py    # Leer/escribir/validar config.json
│   ├── gemini_client.py     # Llamada a Gemini API
│   └── selenium_bot.py      # Automatización de foremp
│
└── ui/
    ├── __init__.py
    ├── main_window.py       # Ventana principal, ensambla widgets
    ├── config_widget.py     # Formulario de configuración
    ├── ia_widget.py         # Input usuario + generación Gemini
    ├── automation_widget.py # Fecha + headless + ejecutar
    └── log_widget.py        # Panel de log en tiempo real
```

---

## 4. Estructura del `config.json`

```json
{
  "usuario": "string",
  "password": "string",
  "gemini_api_key": "string",
  "gemini_model": "gemini-1.5-flash",
  "gemini_temperatura": 0.7,
  "gemini_prompt_sistema": "string (instrucciones base para Gemini)"
}
```

---

## 5. Especificaciones por Módulo

### 5.1 `core/config_manager.py`

**Responsabilidad:** Abstracción total del fichero `config.json`.

**Funciones:**
- `load_config(path) -> AppConfig` — Lee el JSON y devuelve un objeto tipado. Lanza `ConfigError` si faltan campos obligatorios.
- `save_config(config: AppConfig, path)` — Serializa y guarda. Crea el fichero si no existe.
- `validate_config(config: AppConfig) -> list[str]` — Devuelve lista de campos vacíos o inválidos.

**Campos obligatorios validados:** `usuario`, `password`, `gemini_api_key`

---

### 5.2 `core/gemini_client.py`

**Responsabilidad:** Comunicación con la API de Google Gemini.

**Función principal:**
```
generate_description(
    context: str,        # Texto del usuario (tema/contexto del día)
    config: AppConfig    # Parámetros de IA del JSON
) -> str
```

**Comportamiento:**
- Construye el prompt combinando `gemini_prompt_sistema` + contexto del usuario
- El prompt incluye explícitamente: *"La respuesta no debe superar 240 caracteres"*
- Usa el modelo y temperatura definidos en config
- Lanza `GeminiError` con mensaje legible si la llamada falla

---

### 5.3 `core/selenium_bot.py`

**Responsabilidad:** Automatización completa de foremp. Corre en un `QThread` para no bloquear la UI.

**Clase:** `ForempBot(QObject)`

**Señales Qt:**
- `log_signal = Signal(str, str)` — mensaje + nivel (`info` / `success` / `error`)
- `finished = Signal(bool, str)` — éxito (bool) + mensaje final

**Métodos encadenados:**

| Método | Acción | Selector usado |
|---|---|---|
| `login()` | Rellena usuario y password, envía el formulario | `input[name="usuario"]`, `input[name="password"]` |
| `navigate_to_fct()` | Pulsa el enlace FCT | `a[title=""]` con texto `FCT` |
| `find_diary_entry(fecha: date)` | Itera los `<p class="diasDelDiario">` buscando la fecha. Extrae el índice `N` del bloque | `p.diasDelDiario` |
| `click_modify(n: int)` | Pulsa el botón modificar del bloque N | `#modificar{N}` |
| `fill_description(texto: str, n: int)` | Escribe el texto en el textarea | `#descripcion{N+1}` |
| `confirm(n: int)` | Pulsa el botón de confirmar | `#aceptar{N+1}` |
| `verify_success(n: int)` | Busca el mensaje de confirmación | `#diario{N+1} p` con texto `Modificación realizada.` |

**Gestión de errores:**
- Cada método emite `log_signal` antes y después de ejecutarse
- Si un paso falla, emite `log_signal` con nivel `error` y llama a `finished(False, motivo)`
- Usa `WebDriverWait` con timeout configurable (default: 10s)

**Opciones de inicio:**
- `headless: bool` — pasado como parámetro al constructor
- ChromeDriver gestionado con `webdriver-manager` (sin instalación manual)

---

### 5.4 `ui/config_widget.py`

**Responsabilidad:** Formulario para crear/editar y persistir la configuración.

**Campos UI:**
- Usuario (`QLineEdit`)
- Contraseña (`QLineEdit`, `echoMode=Password`)
- API Key Gemini (`QLineEdit`, `echoMode=Password`)
- Modelo Gemini (`QComboBox`: `gemini-1.5-flash`, `gemini-1.5-pro`, `gemini-2.0-flash`)
- Temperatura (`QDoubleSpinBox`, rango 0.0–1.0, step 0.1)
- Prompt de sistema (`QTextEdit`, multilinea)

**Botones:**
- `Cargar desde archivo` — abre `QFileDialog` para seleccionar un JSON distinto
- `Guardar configuración` — valida y guarda; muestra errores inline si faltan campos

**Comportamiento al arrancar:** intenta cargar `config.json` del directorio de trabajo automáticamente y rellena los campos si existe.

**Señal emitida:** `config_saved = Signal(AppConfig)`

---

### 5.5 `ui/ia_widget.py`

**Responsabilidad:** Input del usuario y generación de texto con Gemini.

**Elementos UI:**
- `QTextEdit` — área donde el usuario escribe el tema/contexto del día
- Botón `Generar descripción` — llama a `gemini_client.generate_description()`
- `QTextEdit` editable — muestra el resultado de Gemini (el usuario puede retocarlo)
- Contador de caracteres en tiempo real: `"NNN / 240"`, rojo si supera 240
- Indicador de estado: spinner o label `Generando...` mientras espera la API

**Validación:**
- Si el texto generado o editado supera 240 caracteres, el contador se pone en rojo y se bloquea el botón `Ejecutar` en `automation_widget`

**Señal emitida:** `text_ready = Signal(str, bool)` — texto + válido (≤240 chars)

---

### 5.6 `ui/automation_widget.py`

**Responsabilidad:** Selección de fecha, modo de ejecución y lanzamiento del bot.

**Elementos UI:**
- `QDateEdit` — selector de fecha (por defecto: fecha de hoy)
- `QCheckBox` — `Ejecutar en modo headless (sin ventana)`
- Botón `Ejecutar en foremp` — desactivado hasta que `ia_widget` emita `text_ready(texto, True)`

**Al pulsar Ejecutar:**
1. Crea instancia de `ForempBot` con config, texto, fecha y modo headless
2. La mueve a un `QThread`
3. Conecta `log_signal` → `log_widget.append_log()`
4. Conecta `finished` → `main_window.on_bot_finished()`
5. Arranca el hilo

---

### 5.7 `ui/log_widget.py`

**Responsabilidad:** Mostrar el progreso de Selenium en tiempo real.

**Elementos UI:**
- `QTextEdit` en modo solo lectura con fuente monoespaciada
- Botón `Limpiar log`

**Formato de cada línea:**
```
[HH:MM:SS] [INFO]    Navegando a foremp...
[HH:MM:SS] [OK]      Login completado
[HH:MM:SS] [ERROR]   Timeout esperando el botón FCT
```

**Colores:**
- `INFO` → blanco/gris
- `OK` / `success` → verde (`#4B7`)
- `ERROR` → rojo

**Slot público:** `append_log(message: str, level: str)`

---

### 5.8 `ui/main_window.py`

**Responsabilidad:** Ensamblar todos los widgets en una sola ventana y gestionar el estado global.

**Layout:**
```
┌─────────────────────────────────────────┐
│  [config_widget]   Configuración        │
├─────────────────────────────────────────┤
│  [ia_widget]       IA / Gemini          │
├─────────────────────────────────────────┤
│  [automation_widget]  Automatización    │
├─────────────────────────────────────────┤
│  [log_widget]      Log en tiempo real   │
└─────────────────────────────────────────┘
```

**Conexiones de señales:**
```
config_widget.config_saved  ──▶  guarda AppConfig en memoria
ia_widget.text_ready        ──▶  automation_widget.set_text_valid()
selenium_bot.log_signal     ──▶  log_widget.append_log()
selenium_bot.finished       ──▶  on_bot_finished() → reactiva UI
```

**Durante ejecución del bot:** deshabilita `config_widget`, `ia_widget` y `automation_widget` para evitar cambios concurrentes.

---

## 6. Flujo Completo de la Aplicación

```
Arranque
  └─▶ Intenta cargar config.json → rellena config_widget

Usuario rellena config → pulsa "Guardar"
  └─▶ config_manager.save_config() → AppConfig en memoria

Usuario escribe contexto → pulsa "Generar"
  └─▶ gemini_client.generate_description()
        └─▶ Muestra resultado en ia_widget
              └─▶ Si ≤240 chars → desbloquea botón Ejecutar

Usuario selecciona fecha + modo headless → pulsa "Ejecutar"
  └─▶ ForempBot corre en QThread
        ├─▶ login()
        ├─▶ navigate_to_fct()
        ├─▶ find_diary_entry(fecha)
        ├─▶ click_modify(n)
        ├─▶ fill_description(texto, n)
        ├─▶ confirm(n)
        └─▶ verify_success(n)
              └─▶ finished(True/False) → log_widget + reactiva UI
```

---

## 7. Manejo de Errores

| Situación | Comportamiento |
|---|---|
| `config.json` no existe al arrancar | Campos vacíos, aviso suave en UI |
| Campo obligatorio vacío al guardar | Resalta campos en rojo, no guarda |
| Fallo en API Gemini | Muestra error en `ia_widget`, no bloquea app |
| Texto generado > 240 chars | Contador rojo, botón Ejecutar bloqueado |
| Timeout en Selenium | `log_signal` con nivel `error`, `finished(False)` |
| Elemento no encontrado en foremp | Idem anterior + mensaje descriptivo |
| Mensaje de confirmación no aparece | `finished(False, "No se encontró confirmación")` |

---

## 8. Dependencias (`requirements.txt`)

```
PySide6>=6.6.0
selenium>=4.18.0
webdriver-manager>=4.0.0
google-generativeai>=0.5.0
```

---

## 9. Consideraciones de Seguridad

- El fichero `config.json` contiene credenciales sensibles → añadir al `.gitignore`
- La contraseña y API key se muestran enmascaradas en la UI (`echoMode=Password`)
- No se loguea nunca la contraseña ni la API key en el panel de log

---

## 10. Orden de Desarrollo Recomendado

1. `core/config_manager.py` + `ui/config_widget.py` — base de todo
2. `core/gemini_client.py` + `ui/ia_widget.py` — flujo de IA aislado y testeable
3. `core/selenium_bot.py` — automatización, testear paso a paso
4. `ui/log_widget.py` + `ui/automation_widget.py` — integración del bot con la UI
5. `ui/main_window.py` + `main.py` — ensamblado final y señales
