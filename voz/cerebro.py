"""Conversación con Claude, emitida frase a frase para que la voz empiece antes."""

from __future__ import annotations

import re
import sys
from collections.abc import Callable

import anthropic

from .config import Config

# Cortamos por final de frase, pero no tras abreviaturas ni números decimales.
_FIN_DE_FRASE = re.compile(r"(?<=[.!?…])\s+|(?<=[:;])\s+|\n+")
_MINIMO_POR_FRASE = 40


class Cerebro:
    """Mantiene el hilo de la conversación y produce las respuestas."""

    def __init__(self, cfg: Config):
        self.cfg = cfg
        # La clave se resuelve del entorno (ANTHROPIC_API_KEY o perfil de `ant auth login`).
        self.cliente = anthropic.Anthropic()
        self.historial: list[anthropic.types.MessageParam] = []

    def reiniciar(self) -> None:
        self.historial.clear()

    def _recortar(self) -> None:
        if len(self.historial) > self.cfg.max_turnos:
            del self.historial[: len(self.historial) - self.cfg.max_turnos]

    def responder(self, texto: str, al_completar_frase: Callable[[str], None]) -> str:
        """Envía `texto` a Claude y va entregando la respuesta por frases.

        `al_completar_frase` se llama con cada fragmento hablable en cuanto está
        listo, de modo que el usuario oye la respuesta mientras se genera.
        Devuelve la respuesta completa.
        """
        self.historial.append({"role": "user", "content": texto})
        self._recortar()

        completa: list[str] = []
        pendiente = ""
        buffer_voz = ""
        primera = True

        try:
            with self.cliente.messages.stream(
                model=self.cfg.modelo,
                max_tokens=self.cfg.max_tokens,
                system=self.cfg.instrucciones,
                output_config={"effort": self.cfg.esfuerzo},
                messages=self.historial,
            ) as flujo:
                for trozo in flujo.text_stream:
                    pendiente += trozo
                    partes = _FIN_DE_FRASE.split(pendiente)
                    # La última parte puede estar a medias: se queda pendiente.
                    pendiente = partes.pop() if partes else ""
                    for parte in partes:
                        parte = parte.strip()
                        if not parte:
                            continue
                        completa.append(parte)
                        buffer_voz = f"{buffer_voz} {parte}".strip()
                        # La primera frase sale enseguida (baja la latencia percibida);
                        # las siguientes se agrupan para que la prosodia no suene picada.
                        if primera or len(buffer_voz) >= _MINIMO_POR_FRASE:
                            al_completar_frase(buffer_voz)
                            buffer_voz = ""
                            primera = False
                mensaje = flujo.get_final_message()
        except anthropic.RateLimitError:
            return self._fallo("Estoy recibiendo demasiadas peticiones. Prueba en un momento.")
        except anthropic.APIStatusError as exc:
            print(f"[cerebro] Error {exc.status_code}: {exc}", file=sys.stderr)
            return self._fallo("Hubo un problema con el servicio. Inténtalo otra vez.")
        except anthropic.APIConnectionError:
            return self._fallo("No tengo conexión ahora mismo.")

        if pendiente.strip():
            completa.append(pendiente.strip())
            buffer_voz = f"{buffer_voz} {pendiente.strip()}".strip()
        if buffer_voz:
            al_completar_frase(buffer_voz)

        if getattr(mensaje, "stop_reason", None) == "refusal":
            return self._fallo("Prefiero no responder a eso.")

        respuesta = " ".join(completa).strip()
        self.historial.append({"role": "assistant", "content": respuesta or "…"})
        return respuesta

    def _fallo(self, aviso: str) -> str:
        # No dejamos un turno de usuario huérfano en el historial.
        if self.historial and self.historial[-1]["role"] == "user":
            self.historial.pop()
        return aviso
