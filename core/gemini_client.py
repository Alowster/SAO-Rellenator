from __future__ import annotations

from datetime import date

from google import genai
from google.genai import types

from core.config_manager import AppConfig


class GeminiError(Exception):
    pass


def generate_description(config: AppConfig, fecha: date | None = None) -> str:
    try:
        client = genai.Client(api_key=config.gemini_api_key)

        fecha_str = fecha.strftime("%d/%m/%Y") if fecha else date.today().strftime("%d/%m/%Y")
        prompt = (
            f"Genera la descripción del diario de prácticas para el día {fecha_str}. "
            "La respuesta no debe superar 240 caracteres."
        )

        response = client.models.generate_content(
            model=config.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=config.gemini_temperatura,
                system_instruction=config.gemini_prompt_sistema or None,
            ),
        )
        return response.text.strip()

    except Exception as e:
        raise GeminiError(f"Error al llamar a Gemini: {e}") from e
