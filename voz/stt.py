"""Transcripción de la solicitud del usuario (voz a texto)."""

from __future__ import annotations

import sys

from .audio import a_float32
from .config import Config


class Transcriptor:
    """Fachada sobre el motor elegido: faster-whisper (mejor) o Vosk (más ligero)."""

    def __init__(self, cfg: Config, escucha=None):
        self.cfg = cfg
        self._escucha = escucha
        self._whisper = None
        if cfg.stt == "whisper":
            self._whisper = self._cargar_whisper()
            if self._whisper is None:
                print("[stt] Sin Whisper: uso Vosk para transcribir.", file=sys.stderr)

    def _cargar_whisper(self):
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            return None
        print(f"[stt] Cargando Whisper «{self.cfg.whisper_modelo}»…", file=sys.stderr)
        return WhisperModel(self.cfg.whisper_modelo, device="auto", compute_type="int8")

    def transcribir(self, pcm: bytes) -> str:
        if not pcm:
            return ""
        if self._whisper is not None:
            segmentos, _ = self._whisper.transcribe(
                a_float32(pcm),
                language=self.cfg.idioma,
                vad_filter=True,
                beam_size=1,
                condition_on_previous_text=False,
            )
            return " ".join(s.text.strip() for s in segmentos).strip()
        if self._escucha is not None:
            return self._escucha.transcribir(pcm)
        return ""
