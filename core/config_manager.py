from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


class ConfigError(Exception):
    pass


@dataclass
class AppConfig:
    usuario: str = ""
    password: str = ""
    ollama_url: str = "http://localhost:11434"
    llm_model: str = "gemma3:4b"
    llm_temperatura: float = 0.7
    llm_prompt_sistema: str = ""
    cerrar_ollama_al_salir: bool = False


def load_config(path: str | Path = "config.json") -> AppConfig:
    path = Path(path)
    if not path.exists():
        raise ConfigError(f"No se encontró el archivo de configuración: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ConfigError(f"El archivo de configuración no es JSON válido: {e}")

    config = AppConfig(
        usuario=data.get("usuario", ""),
        password=data.get("password", ""),
        ollama_url=data.get("ollama_url", "http://localhost:11434"),
        llm_model=data.get("llm_model", "gemma3:4b"),
        llm_temperatura=float(data.get("llm_temperatura", 0.7)),
        llm_prompt_sistema=data.get("llm_prompt_sistema", ""),
        cerrar_ollama_al_salir=bool(data.get("cerrar_ollama_al_salir", False)),
    )

    errors = validate_config(config)
    if errors:
        raise ConfigError(f"Campos obligatorios vacíos: {', '.join(errors)}")

    return config


def save_config(config: AppConfig, path: str | Path = "config.json") -> None:
    path = Path(path)
    data = {
        "usuario": config.usuario,
        "password": config.password,
        "ollama_url": config.ollama_url,
        "llm_model": config.llm_model,
        "llm_temperatura": config.llm_temperatura,
        "llm_prompt_sistema": config.llm_prompt_sistema,
        "cerrar_ollama_al_salir": config.cerrar_ollama_al_salir,
    }
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def validate_config(config: AppConfig) -> list[str]:
    required = ["usuario", "password"]
    return [f for f in required if not getattr(config, f, "").strip()]
