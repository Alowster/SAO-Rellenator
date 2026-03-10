# SAÓ-Rellenator

Herramienta de escritorio que automatiza el relleno del SAÓ (Sistema de Anotación y Observación) utilizando un modelo de lenguaje local a través de Ollama.

## ¿Qué hace?

Genera y completa automáticamente los campos de texto del SAÓ usando IA local, evitando la necesidad de escribir manualmente cada entrada.

## Tecnologías

- **Python**
- **Ollama** — modelo de IA local para generación de texto
- **PyInstaller** — empaquetado como ejecutable `.exe`

## Requisitos

- Python 3.x
- [Ollama](https://ollama.com/) instalado y en ejecución con el modelo gemma3:4b descargado (`ollama pull gemma3:4b`)

## Instalación

```bash
git clone https://github.com/Alowster/SAO-Rellenator.git
cd SAO-Rellenator
pip install -r requirements.txt
```

## Uso

```bash
python main.py
```

O descarga el ejecutable desde la sección [Releases](https://github.com/Alowster/SAO-Rellenator/releases).

## Estructura

```
SAO-Rellenator/
├── core/       # Lógica principal e integración con Ollama
├── ui/         # Interfaz de usuario
├── assets/     # Recursos gráficos
└── main.py     # Punto de entrada
```

## Autor

[Alowster](https://github.com/Alowster)
