"""Síntesis de voz: convierte la respuesta de Claude en audio hablado."""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .config import Config


def _existe(programa: str) -> bool:
    return shutil.which(programa) is not None


def elegir_motor(cfg: Config) -> str:
    """Escoge el mejor motor disponible en este equipo."""
    if cfg.tts != "auto":
        return cfg.tts

    sistema = platform.system()
    if sistema == "Darwin" and _existe("say"):
        return "say"
    if sistema == "Windows":
        return "powershell"
    if _existe("piper") and cfg.piper_modelo.is_file():
        return "piper"
    if _existe("espeak-ng") or _existe("espeak"):
        return "espeak"
    return "pyttsx3"


class Voz:
    """Reproduce texto en voz alta y permite cortar la reproducción."""

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.motor = elegir_motor(cfg)
        self._proc: subprocess.Popen | None = None
        self._pyttsx = None
        print(f"[tts] Motor de voz: {self.motor}", file=sys.stderr)

    # -- motores -----------------------------------------------------------

    def _comando_say(self, texto: str) -> list[str]:
        cmd = ["say"]
        if self.cfg.tts_voz:
            cmd += ["-v", self.cfg.tts_voz]
        return [*cmd, texto]

    def _comando_espeak(self, texto: str) -> list[str]:
        binario = "espeak-ng" if _existe("espeak-ng") else "espeak"
        return [binario, "-v", self.cfg.tts_voz or "es", "-s", "165", texto]

    def _comando_powershell(self, texto: str) -> list[str]:
        seguro = texto.replace("'", "''")
        voz = f"$s.SelectVoice('{self.cfg.tts_voz}');" if self.cfg.tts_voz else ""
        script = (
            "Add-Type -AssemblyName System.Speech;"
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
            f"{voz}$s.Speak('{seguro}')"
        )
        return ["powershell", "-NoProfile", "-Command", script]

    def _reproductor(self) -> list[str] | None:
        for prog, args in (
            ("afplay", []),
            ("paplay", []),
            ("aplay", ["-q"]),
            ("ffplay", ["-nodisp", "-autoexit", "-loglevel", "quiet"]),
        ):
            if _existe(prog):
                return [prog, *args]
        return None

    def _hablar_piper(self, texto: str) -> None:
        reproductor = self._reproductor()
        if reproductor is None:
            print("[tts] No hay reproductor de audio (aplay/paplay/afplay).", file=sys.stderr)
            return
        with tempfile.TemporaryDirectory() as tmp:
            wav = Path(tmp) / "voz.wav"
            subprocess.run(
                ["piper", "--model", str(self.cfg.piper_modelo), "--output_file", str(wav)],
                input=texto.encode("utf-8"),
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self._proc = subprocess.Popen([*reproductor, str(wav)])
            self._proc.wait()
            self._proc = None

    def _hablar_pyttsx3(self, texto: str) -> None:
        try:
            import pyttsx3
        except ImportError:
            print(f"[tts] Sin motor de voz disponible. Respuesta: {texto}", file=sys.stderr)
            return
        if self._pyttsx is None:
            self._pyttsx = pyttsx3.init()
            if self.cfg.tts_voz:
                self._pyttsx.setProperty("voice", self.cfg.tts_voz)
        self._pyttsx.say(texto)
        self._pyttsx.runAndWait()

    # -- API pública -------------------------------------------------------

    def hablar(self, texto: str) -> None:
        texto = texto.strip()
        if not texto:
            return
        try:
            if self.motor == "piper":
                self._hablar_piper(texto)
                return
            if self.motor == "pyttsx3":
                self._hablar_pyttsx3(texto)
                return

            comando = {
                "say": self._comando_say,
                "espeak": self._comando_espeak,
                "powershell": self._comando_powershell,
            }[self.motor](texto)
            self._proc = subprocess.Popen(comando)
            self._proc.wait()
            self._proc = None
        except FileNotFoundError:
            print(f"[tts] Motor «{self.motor}» no instalado. Respuesta: {texto}", file=sys.stderr)
        except subprocess.CalledProcessError as exc:
            print(f"[tts] Error al sintetizar: {exc}", file=sys.stderr)

    def callar(self) -> None:
        """Corta la reproducción en curso."""
        if self._proc is not None and self._proc.poll() is None:
            self._proc.terminate()
        self._proc = None
        if self._pyttsx is not None:
            try:
                self._pyttsx.stop()
            except RuntimeError:
                pass
