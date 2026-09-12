# Asistente de voz «oye claude»

Automatización que escucha el micrófono de tu equipo en segundo plano y, cuando
dices **«oye claude»**, graba tu solicitud, la transcribe, se la envía a Claude y
te responde **hablando**. La conversación sigue abierta unos segundos, así que
puedes encadenar preguntas sin repetir la palabra clave.

```
micrófono ──▶ palabra clave (Vosk, offline) ──▶ grabación hasta que callas
   ▲                                                      │
   │                                                      ▼
voz hablada ◀── síntesis (Piper / voz del sistema) ◀── Claude (streaming)
```

La detección de la palabra clave es **local**: no se envía audio a ningún sitio
hasta que dices «oye claude». Solo entonces se manda la transcripción a la API.

## Requisitos

- Python 3.10 o superior
- Un micrófono y altavoces
- Una clave de la API de Anthropic

## Instalación

```bash
git clone <este-repo> quim && cd quim

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

bash scripts/descargar_modelos.sh  # modelo de palabra clave (~40 MB)

cp .env.example .env               # y escribe tu ANTHROPIC_API_KEY dentro
```

### Dependencias del sistema por plataforma

| Sistema | Audio de entrada | Voz de salida |
|---|---|---|
| **macOS** | `brew install portaudio` | ya incluida (`say`) |
| **Linux (Debian/Ubuntu)** | `sudo apt install portaudio19-dev python3-dev` | `sudo apt install espeak-ng` o [Piper](https://github.com/rhasspy/piper) para una voz mucho mejor |
| **Windows** | nada extra | ya incluida (SAPI) |

## Uso

```bash
python -m voz
```

```
Asistente de voz listo.
Di «oye claude» para empezar. Ctrl+C para salir.

· Esperando la palabra clave…
· ¡Te escucho!
  Tú: ¿qué tiempo hace mañana en Valencia?
  Claude: No tengo acceso al tiempo en directo, pero...
```

Para cerrar la conversación di «adiós», «para» o «hasta luego»; también se cierra
sola tras unos segundos de silencio y vuelve a esperar la palabra clave.

Ver los micrófonos disponibles (por si necesitas fijar uno con `VOZ_DISPOSITIVO`):

```bash
python -m voz --dispositivos
```

## Que arranque solo con el equipo

- **macOS** → `servicios/com.quim.voz.plist`
- **Linux** → `servicios/quim-voz.service`
- **Windows** → `servicios/windows-autoarranque.md`

Cada archivo lleva las instrucciones en sus primeras líneas.

## Ajustes

Todo se configura por variables de entorno o en el `.env`. Los más útiles:

| Variable | Por defecto | Para qué sirve |
|---|---|---|
| `VOZ_PALABRAS_CLAVE` | `oye claude,oye clod,…` | Frases que activan el asistente. Añade variantes: el reconocedor no siempre oye «claude» igual |
| `VOZ_MODELO` | `claude-opus-5` | Modelo de Claude |
| `VOZ_ESFUERZO` | `low` | `low` responde antes; `high` razona más |
| `VOZ_STT` | `whisper` | `whisper` transcribe mejor; `vosk` gasta mucha menos CPU |
| `VOZ_WHISPER_MODELO` | `small` | `tiny`/`base` si el equipo va justo |
| `VOZ_TTS` | `auto` | `say`, `piper`, `espeak`, `powershell` o `pyttsx3` |
| `VOZ_TTS_VOZ` | — | Nombre de la voz (`Mónica` en macOS, por ejemplo) |
| `VOZ_SILENCIO` | `1.0` | Segundos de silencio que dan por terminada tu frase |
| `VOZ_SEGUIMIENTO` | `8.0` | Cuánto sigue escuchando tras responder |
| `VOZ_DISPOSITIVO` | — | Índice o nombre del micrófono |

## Si algo no funciona

**No reacciona a «oye claude».** El reconocedor puede estar oyendo otra cosa.
Añade variantes a `VOZ_PALABRAS_CLAVE` (`oye clod`, `oye cloud`, `oye claudio`) o
cambia a una palabra clave más fácil de distinguir en español, como `oye asistente`.

**Corta tus frases a media palabra.** Sube `VOZ_SILENCIO` a `1.5`.

**Se activa solo mientras habla.** El micrófono se silencia durante la respuesta,
pero con altavoces muy cerca puede colarse eco: usa auriculares o baja el volumen.

**Va lento.** Baja `VOZ_WHISPER_MODELO` a `base`, o pon `VOZ_STT=vosk`. La
transcripción local es casi siempre el cuello de botella, no la API.

**`OSError: PortAudio library not found`.** Falta la dependencia del sistema de la
tabla de arriba.

## Estructura

```
voz/
  app.py      bucle principal: palabra clave → grabar → responder
  audio.py    micrófono y detección de fin de frase
  wake.py     detección de «oye claude» (Vosk, offline)
  stt.py      transcripción (faster-whisper o Vosk)
  cerebro.py  conversación con Claude, emitida frase a frase
  tts.py      voz sintetizada (Piper / say / SAPI / espeak)
  config.py   configuración y carga del .env
```

## Coste y privacidad

Solo se envía a Anthropic el **texto** transcrito de lo que digas después de la
palabra clave; el audio nunca sale del equipo. Con `VOZ_ESFUERZO=low` una
conversación corriente cuesta céntimos. El historial vive en memoria y se borra
al cerrar cada conversación.
