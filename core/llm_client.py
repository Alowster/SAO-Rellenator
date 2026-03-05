from __future__ import annotations

from datetime import date

import ollama

from core.config_manager import AppConfig


class LLMError(Exception):
    pass


def generate_description(config: AppConfig, fecha: date | None = None) -> str:
    try:
        client = ollama.Client(host=config.ollama_url)

        fecha_str = fecha.strftime("%d/%m/%Y") if fecha else date.today().strftime("%d/%m/%Y")
        prompt = (
            f"Genera la descripción del diario de prácticas para el día {fecha_str}. "
            "La respuesta no debe superar 240 caracteres."
        )

        response = client.generate(
            model=config.llm_model,
            prompt=prompt,
            system=config.llm_prompt_sistema or None,
            options={"temperature": config.llm_temperatura},
        )
        return response.response.strip()

    except Exception as e:
        raise LLMError(f"Error al llamar a Ollama: {e}") from e
