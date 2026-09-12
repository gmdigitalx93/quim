"""Captura de micrófono y detección de fin de frase (endpointing)."""

from __future__ import annotations

import queue
import sys
import time
from collections.abc import Iterator

import numpy as np

try:
    import sounddevice as sd
except OSError as exc:  # PortAudio ausente
    print(f"[audio] No se pudo cargar PortAudio: {exc}", file=sys.stderr)
    raise

try:
    import webrtcvad
except ImportError:
    webrtcvad = None


class Microfono:
    """Flujo continuo de micrófono a 16 kHz, mono, PCM 16 bits.

    Se abre una sola vez y se comparte entre la detección de la palabra clave
    y la grabación de la solicitud, para no pelear por el dispositivo.
    """

    def __init__(self, frecuencia: int = 16_000, bloque: int = 512, dispositivo=None):
        self.frecuencia = frecuencia
        self.bloque = bloque
        self.dispositivo = dispositivo
        self._cola: queue.Queue[bytes] = queue.Queue()
        self._stream: sd.RawInputStream | None = None
        self._silenciado = False

    def _callback(self, datos, marcos, tiempo, estado):  # noqa: ARG002
        if estado:
            print(f"[audio] {estado}", file=sys.stderr)
        if not self._silenciado:
            self._cola.put(bytes(datos))

    def __enter__(self) -> "Microfono":
        self._stream = sd.RawInputStream(
            samplerate=self.frecuencia,
            blocksize=self.bloque,
            device=self.dispositivo,
            dtype="int16",
            channels=1,
            callback=self._callback,
        )
        self._stream.start()
        return self

    def __exit__(self, *_exc) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def silenciar(self, valor: bool) -> None:
        """Ignora el audio entrante (por ejemplo mientras hablamos nosotros)."""
        self._silenciado = valor
        if valor:
            self.vaciar()

    def vaciar(self) -> None:
        while True:
            try:
                self._cola.get_nowait()
            except queue.Empty:
                return

    def bloques(self, tiempo_maximo: float | None = None) -> Iterator[bytes]:
        inicio = time.monotonic()
        while True:
            if tiempo_maximo is not None and time.monotonic() - inicio > tiempo_maximo:
                return
            try:
                yield self._cola.get(timeout=0.25)
            except queue.Empty:
                continue


class DetectorDeVoz:
    """Decide si un bloque de audio contiene voz.

    Usa WebRTC VAD cuando está disponible; si no, cae a un umbral de energía
    calibrado con el ruido ambiente de los primeros bloques.
    """

    def __init__(self, frecuencia: int = 16_000, agresividad: int = 2):
        self.frecuencia = frecuencia
        self._vad = webrtcvad.Vad(agresividad) if webrtcvad else None
        self._ruido: float | None = None
        self._muestras_ruido: list[float] = []

    @staticmethod
    def _rms(bloque: bytes) -> float:
        muestras = np.frombuffer(bloque, dtype=np.int16).astype(np.float32)
        if muestras.size == 0:
            return 0.0
        return float(np.sqrt(np.mean(muestras**2)))

    def hay_voz(self, bloque: bytes) -> bool:
        if self._vad is not None:
            # WebRTC VAD exige tramas de 10, 20 o 30 ms.
            trama = int(self.frecuencia * 0.02) * 2  # 20 ms en bytes
            trozos = [bloque[i : i + trama] for i in range(0, len(bloque) - trama + 1, trama)]
            if trozos:
                return any(self._vad.is_speech(t, self.frecuencia) for t in trozos)

        nivel = self._rms(bloque)
        if self._ruido is None:
            self._muestras_ruido.append(nivel)
            if len(self._muestras_ruido) < 10:
                return False
            self._ruido = max(60.0, float(np.median(self._muestras_ruido)))
        return nivel > self._ruido * 3.0


def grabar_frase(
    microfono: Microfono,
    *,
    silencio_fin: float = 1.0,
    espera_inicial: float = 6.0,
    maximo: float = 30.0,
) -> bytes:
    """Graba hasta que el hablante calla.

    Devuelve PCM 16 bits crudo, o b"" si nadie llegó a hablar.
    """
    detector = DetectorDeVoz(microfono.frecuencia)
    segundos_por_bloque = microfono.bloque / microfono.frecuencia

    trozos: list[bytes] = []
    empezo_a_hablar = False
    silencio = 0.0
    espera = 0.0

    for bloque in microfono.bloques(tiempo_maximo=maximo):
        voz = detector.hay_voz(bloque)

        if not empezo_a_hablar:
            espera += segundos_por_bloque
            if voz:
                empezo_a_hablar = True
                trozos.append(bloque)
            elif espera >= espera_inicial:
                return b""
            else:
                # Guardamos algo de margen previo para no cortar la primera sílaba.
                trozos.append(bloque)
                if len(trozos) > int(0.4 / segundos_por_bloque):
                    trozos.pop(0)
            continue

        trozos.append(bloque)
        silencio = 0.0 if voz else silencio + segundos_por_bloque
        if silencio >= silencio_fin:
            break

    return b"".join(trozos) if empezo_a_hablar else b""


def a_float32(pcm: bytes) -> np.ndarray:
    """Convierte PCM 16 bits a float32 normalizado, como espera Whisper."""
    return np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0


def duracion(pcm: bytes, frecuencia: int = 16_000) -> float:
    return len(pcm) / 2 / frecuencia
