"""Detección de la palabra clave «oye claude» con Vosk, en local y sin conexión."""

from __future__ import annotations

import difflib
import json
import re
import sys
import unicodedata
from pathlib import Path

from .audio import Microfono

# Parecido mínimo para dar por buena una palabra clave mal reconocida.
# 0.76 acepta «olle claud» y sigue muy lejos del habla corriente (< 0.5).
_UMBRAL_PARECIDO = 0.76


def normalizar(texto: str) -> str:
    """Minúsculas, sin tildes y sin puntuación, para comparar de forma tolerante."""
    texto = unicodedata.normalize("NFD", texto.lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    texto = re.sub(r"[^a-z0-9 ]+", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


class Escucha:
    """Escucha continuamente y avisa cuando oye alguna de las palabras clave."""

    def __init__(self, modelo: Path, palabras_clave: list[str], frecuencia: int = 16_000):
        try:
            from vosk import KaldiRecognizer, Model, SetLogLevel
        except ImportError as exc:  # pragma: no cover
            raise SystemExit(
                "Falta el paquete vosk. Instálalo con: pip install vosk"
            ) from exc

        if not modelo.is_dir():
            raise SystemExit(
                f"No encuentro el modelo de Vosk en {modelo}.\n"
                "Descárgalo con: bash scripts/descargar_modelos.sh"
            )

        SetLogLevel(-1)
        self.palabras_clave = [normalizar(p) for p in palabras_clave]
        self._modelo = Model(str(modelo))

        # Una gramática cerrada mejora mucho la precisión: el reconocedor solo
        # puede elegir entre las palabras clave y «desconocido».
        gramatica = json.dumps(self.palabras_clave + ["[unk]"])
        self._rec = KaldiRecognizer(self._modelo, frecuencia, gramatica)
        self._rec.SetWords(False)

    def _coincide(self, texto: str) -> bool:
        texto = normalizar(texto)
        if not texto:
            return False
        for clave in self.palabras_clave:
            if clave in texto:
                return True
            # Tolerancia a errores de reconocimiento ("oye clos", "oye clod").
            palabras = texto.split()
            n = len(clave.split())
            ventanas = [" ".join(palabras[i : i + n]) for i in range(max(1, len(palabras) - n + 1))]
            if any(difflib.SequenceMatcher(None, clave, v).ratio() >= _UMBRAL_PARECIDO for v in ventanas):
                return True
        return False

    def esperar(self, microfono: Microfono) -> bool:
        """Bloquea hasta oír la palabra clave. Devuelve False si se interrumpe."""
        self._rec.Reset()
        try:
            for bloque in microfono.bloques():
                if self._rec.AcceptWaveform(bloque):
                    texto = json.loads(self._rec.Result()).get("text", "")
                else:
                    texto = json.loads(self._rec.PartialResult()).get("partial", "")
                if self._coincide(texto):
                    self._rec.Reset()
                    microfono.vaciar()
                    return True
        except KeyboardInterrupt:
            return False
        return False

    def transcribir(self, pcm: bytes) -> str:
        """Transcripción de respaldo con Vosk, si no se usa Whisper."""
        from vosk import KaldiRecognizer

        rec = KaldiRecognizer(self._modelo, 16_000)
        rec.AcceptWaveform(pcm)
        return json.loads(rec.FinalResult()).get("text", "").strip()


def comprobar_modelo(ruta: Path) -> None:
    if not ruta.is_dir():
        print(
            f"[wake] Falta el modelo de Vosk en {ruta}. "
            "Ejecuta: bash scripts/descargar_modelos.sh",
            file=sys.stderr,
        )
