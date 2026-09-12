"""Una pregunta, una respuesta, por línea de comandos.

Pensado para que el iPhone lo invoque por SSH: el texto entra por stdin y la
respuesta sale por stdout, sin adornos, lista para leerse en voz alta.

    echo "¿qué tiempo hace?" | python -m voz.pregunta

Guarda el hilo de la conversación en disco durante unos minutos, así las
preguntas encadenadas mantienen el contexto sin que el teléfono tenga que
llevar el historial.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from .cerebro import Cerebro
from .config import Config, cargar_dotenv


def _ruta_sesion() -> Path:
    cache = os.environ.get("XDG_CACHE_HOME")
    base = Path(cache) if cache else Path.home() / ".cache"
    return base / "quim" / "sesion.json"


def _ttl() -> float:
    try:
        return float(os.environ["VOZ_SESION_TTL"])
    except (KeyError, ValueError):
        return 600.0  # 10 minutos


def cargar_historial() -> list[dict]:
    """Recupera la conversación si es reciente; si no, empieza de cero."""
    ruta = _ruta_sesion()
    if not ruta.is_file():
        return []
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        if time.time() - datos.get("t", 0) > _ttl():
            return []
        return datos.get("mensajes", [])
    except (OSError, ValueError):
        return []


def guardar_historial(mensajes: list[dict]) -> None:
    ruta = _ruta_sesion()
    try:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(
            json.dumps({"t": time.time(), "mensajes": mensajes}, ensure_ascii=False),
            encoding="utf-8",
        )
        ruta.chmod(0o600)
    except OSError as exc:
        print(f"[pregunta] No pude guardar la sesión: {exc}", file=sys.stderr)


def olvidar() -> None:
    try:
        _ruta_sesion().unlink()
    except OSError:
        pass


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    cargar_dotenv()

    nuevo = "--nuevo" in argv
    argv = [a for a in argv if a != "--nuevo"]

    # El texto llega como argumento o, si no, por stdin (que es como lo manda
    # la acción «Ejecutar script por SSH» de Atajos a través de su Entrada).
    texto = " ".join(argv).strip() or sys.stdin.read().strip()
    if not texto:
        print("No he entendido nada.")
        return 0

    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        print("Falta la clave de la API en el servidor.")
        print("[pregunta] Define ANTHROPIC_API_KEY o crea un .env", file=sys.stderr)
        return 1

    cerebro = Cerebro(Config())
    cerebro.historial = [] if nuevo else cargar_historial()

    respuesta = cerebro.responder(texto, lambda _frase: None)

    guardar_historial(cerebro.historial)
    print(respuesta or "No he podido responder a eso.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
