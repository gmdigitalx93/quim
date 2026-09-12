#!/usr/bin/env bash
# Descarga los modelos offline: Vosk (palabra clave) y, opcionalmente, Piper (voz).
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODELOS="$RAIZ/modelos"
mkdir -p "$MODELOS"

VOSK_URL="https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip"

if [ ! -d "$MODELOS/vosk-es" ]; then
  echo "→ Descargando el modelo de Vosk en español (~40 MB)…"
  curl -L --fail -o "$MODELOS/vosk.zip" "$VOSK_URL"
  unzip -q "$MODELOS/vosk.zip" -d "$MODELOS"
  mv "$MODELOS"/vosk-model-small-es-* "$MODELOS/vosk-es"
  rm "$MODELOS/vosk.zip"
  echo "✓ Vosk instalado en $MODELOS/vosk-es"
else
  echo "✓ Vosk ya estaba instalado."
fi

# Voz Piper (solo Linux; en macOS y Windows se usa la voz del sistema).
if command -v piper >/dev/null 2>&1 && [ ! -f "$MODELOS/es_ES-sharvard-medium.onnx" ]; then
  echo "→ Descargando la voz de Piper en español…"
  BASE="https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/sharvard/medium"
  curl -L --fail -o "$MODELOS/es_ES-sharvard-medium.onnx" "$BASE/es_ES-sharvard-medium.onnx"
  curl -L --fail -o "$MODELOS/es_ES-sharvard-medium.onnx.json" \
    "$BASE/es_ES-sharvard-medium.onnx.json"
  echo "✓ Voz de Piper instalada."
fi

echo "Listo."
