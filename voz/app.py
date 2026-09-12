"""Bucle principal: escuchar «oye claude» → transcribir → responder hablando."""

from __future__ import annotations

import contextlib
import os
import sys

from .audio import Microfono, duracion, grabar_frase
from .cerebro import Cerebro
from .config import Config, cargar_dotenv
from .stt import Transcriptor
from .tts import Voz
from .wake import Escucha, normalizar

DESPEDIDAS = {
    "adios", "adios claude", "hasta luego", "gracias adios", "ya esta",
    "para", "para ya", "callate", "termina", "cancela", "nada mas",
}


def _es_despedida(texto: str) -> bool:
    limpio = normalizar(texto)
    return limpio in DESPEDIDAS or (len(limpio) <= 25 and limpio.startswith(("adios", "hasta luego")))


class Asistente:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.escucha = Escucha(cfg.vosk_modelo, cfg.palabras_clave, cfg.frecuencia)
        self.transcriptor = Transcriptor(cfg, self.escucha)
        self.voz = Voz(cfg)
        self.cerebro = Cerebro(cfg)

    @contextlib.contextmanager
    def _sin_eco(self, microfono: Microfono):
        """Silencia el micrófono mientras hablamos, para no oírnos a nosotros mismos."""
        microfono.silenciar(True)
        try:
            yield
        finally:
            microfono.silenciar(False)

    def _decir(self, microfono: Microfono, texto: str) -> None:
        with self._sin_eco(microfono):
            self.voz.hablar(texto)

    def _turno(self, microfono: Microfono, *, primera_vez: bool) -> bool:
        """Escucha una solicitud y la responde. Devuelve False para cerrar la conversación."""
        pcm = grabar_frase(
            microfono,
            silencio_fin=self.cfg.silencio_fin,
            espera_inicial=self.cfg.espera_inicial if primera_vez else self.cfg.seguimiento,
            maximo=self.cfg.max_grabacion,
        )
        if duracion(pcm) < 0.35:
            if primera_vez:
                self._decir(microfono, "No te he oído.")
            return False

        print("[app] Transcribiendo…", file=sys.stderr)
        texto = self.transcriptor.transcribir(pcm)
        if not texto:
            self._decir(microfono, "No he entendido nada. ¿Me lo repites?")
            return True

        print(f"\n  Tú: {texto}")
        if _es_despedida(texto):
            self._decir(microfono, "Hasta luego.")
            return False

        print("  Claude: ", end="", flush=True)

        def hablar(frase: str) -> None:
            print(frase, end=" ", flush=True)
            self.voz.hablar(frase)

        # Un único silenciado para toda la respuesta: si lo abriéramos y
        # cerráramos por frase, el micro captaría la cola de nuestra propia voz.
        with self._sin_eco(microfono):
            respuesta = self.cerebro.responder(texto, hablar)
        print()
        if not respuesta:
            self._decir(microfono, "No he podido responder a eso.")
        return True

    def ejecutar(self) -> int:
        print("Asistente de voz listo.")
        print(f"Di «{self.cfg.palabras_clave[0]}» para empezar. Ctrl+C para salir.\n")

        with Microfono(self.cfg.frecuencia, self.cfg.bloque, self.cfg.dispositivo_entrada) as mic:
            while True:
                print("· Esperando la palabra clave…", file=sys.stderr)
                if not self.escucha.esperar(mic):
                    break

                print("· ¡Te escucho!", file=sys.stderr)
                self.cerebro.reiniciar()
                self._decir(mic, "Dime.")

                primera_vez = True
                # Tras responder seguimos escuchando un rato: así se puede
                # encadenar la conversación sin repetir la palabra clave.
                while self._turno(mic, primera_vez=primera_vez):
                    primera_vez = False
        return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    cargar_dotenv()

    if "--dispositivos" in argv:
        import sounddevice as sd

        print(sd.query_devices())
        return 0

    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        print(
            "Falta ANTHROPIC_API_KEY. Copia .env.example a .env y pon tu clave,\n"
            "o inicia sesión con `ant auth login`.",
            file=sys.stderr,
        )
        return 1

    cfg = Config()
    try:
        asistente = Asistente(cfg)
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        return 1

    try:
        return asistente.ejecutar()
    except KeyboardInterrupt:
        print("\nHasta luego.")
        return 0
