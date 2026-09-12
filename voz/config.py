"""Configuración del asistente, leída de variables de entorno y de un .env opcional."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def cargar_dotenv(ruta: Path | None = None) -> None:
    """Carga un .env sencillo sin dependencias externas.

    No sobrescribe variables que ya existan en el entorno.
    """
    ruta = ruta or RAIZ / ".env"
    if not ruta.is_file():
        return
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, _, valor = linea.partition("=")
        clave = clave.strip()
        valor = valor.strip().strip('"').strip("'")
        os.environ.setdefault(clave, valor)


def _lista(nombre: str, por_defecto: list[str]) -> list[str]:
    bruto = os.environ.get(nombre, "")
    valores = [x.strip().lower() for x in bruto.split(",") if x.strip()]
    return valores or por_defecto


def _float(nombre: str, por_defecto: float) -> float:
    try:
        return float(os.environ[nombre])
    except (KeyError, ValueError):
        return por_defecto


def _ruta(nombre: str, por_defecto: str) -> Path:
    valor = os.environ.get(nombre, por_defecto)
    p = Path(valor).expanduser()
    return p if p.is_absolute() else RAIZ / p


@dataclass
class Config:
    # Palabra clave
    palabras_clave: list[str] = field(
        default_factory=lambda: _lista(
            "VOZ_PALABRAS_CLAVE",
            ["oye claude", "oye clod", "oye cloud", "oye claudio", "oye clau"],
        )
    )
    vosk_modelo: Path = field(default_factory=lambda: _ruta("VOZ_VOSK_MODELO", "modelos/vosk-es"))

    # Audio
    frecuencia: int = 16_000
    bloque: int = 512
    dispositivo_entrada: str | int | None = field(
        default_factory=lambda: os.environ.get("VOZ_DISPOSITIVO") or None
    )
    silencio_fin: float = field(default_factory=lambda: _float("VOZ_SILENCIO", 1.0))
    max_grabacion: float = field(default_factory=lambda: _float("VOZ_MAX_GRABACION", 30.0))
    espera_inicial: float = field(default_factory=lambda: _float("VOZ_ESPERA_INICIAL", 6.0))
    seguimiento: float = field(default_factory=lambda: _float("VOZ_SEGUIMIENTO", 8.0))

    # Transcripción
    stt: str = field(default_factory=lambda: os.environ.get("VOZ_STT", "whisper").lower())
    whisper_modelo: str = field(
        default_factory=lambda: os.environ.get("VOZ_WHISPER_MODELO", "small")
    )
    idioma: str = field(default_factory=lambda: os.environ.get("VOZ_IDIOMA", "es"))

    # Voz sintetizada
    tts: str = field(default_factory=lambda: os.environ.get("VOZ_TTS", "auto").lower())
    tts_voz: str | None = field(default_factory=lambda: os.environ.get("VOZ_TTS_VOZ") or None)
    piper_modelo: Path = field(
        default_factory=lambda: _ruta("VOZ_PIPER_MODELO", "modelos/es_ES-sharvard-medium.onnx")
    )

    # Claude
    modelo: str = field(default_factory=lambda: os.environ.get("VOZ_MODELO", "claude-opus-5"))
    esfuerzo: str = field(default_factory=lambda: os.environ.get("VOZ_ESFUERZO", "low").lower())
    max_tokens: int = 4_000
    max_turnos: int = 24

    @property
    def instrucciones(self) -> str:
        return (
            "Eres un asistente de voz en español. Tus respuestas se leen en voz alta, "
            "así que habla como una persona: frases cortas, tono natural y cercano.\n"
            "Reglas:\n"
            "- Responde en 1 o 2 frases salvo que te pidan más detalle.\n"
            "- Nunca uses markdown, listas con guiones, asteriscos, emojis ni URLs largas.\n"
            "- Escribe números, siglas y símbolos como se pronuncian.\n"
            "- Si la transcripción parece incompleta o ambigua, pide que te lo repitan "
            "en una sola frase corta.\n"
            "- No describas lo que vas a hacer: hazlo y contesta."
        )
