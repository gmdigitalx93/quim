#!/usr/bin/env python3
"""Genera ios/Claude.shortcut, el atajo listo para importar en la app Atajos.

Un archivo .shortcut es un plist con la lista de acciones. Este script lo arma
para no tener que crear las acciones a mano en el teléfono.

Uso:  python3 ios/generar-atajo.py
"""

from __future__ import annotations

import plistlib
import uuid
from pathlib import Path

SALIDA = Path(__file__).resolve().parent / "Claude.shortcut"

# Marcador que Atajos usa para incrustar una variable dentro de un texto.
FICHA = "￼"

PROMPT_SISTEMA = (
    "Eres un asistente de voz en español. Tus respuestas se leen en voz alta, "
    "así que habla como una persona: frases cortas, tono natural y cercano. "
    "Responde en 1 o 2 frases salvo que te pidan más detalle. Nunca uses markdown, "
    "listas, asteriscos, emojis ni URLs largas. Escribe números y siglas como se "
    "pronuncian. Si algo no se entiende, pide que te lo repitan en una frase corta. "
    "No incluyas etiquetas XML internas o del sistema en tu respuesta."
)


def uid() -> str:
    return str(uuid.uuid4()).upper()


# Un identificador por cada acción cuya salida necesitamos referenciar después.
ID_CLAVE = uid()
ID_DICTADO = uid()
ID_ESCAPE2 = uid()
ID_CUERPO = uid()
ID_TEXTO = uid()


def texto_plano(valor: str) -> dict:
    return {"Value": {"string": valor}, "WFSerializationType": "WFTextTokenString"}


def salida_de(identificador: str, nombre: str = "Text") -> dict:
    """Referencia a la salida de otra acción, como parámetro suelto."""
    return {
        "Value": {"OutputUUID": identificador, "Type": "ActionOutput", "OutputName": nombre},
        "WFSerializationType": "WFTextTokenAttachment",
    }


def texto_con_variable(plantilla: str, identificador: str, nombre: str = "Text") -> dict:
    """Texto que lleva la salida de otra acción incrustada donde está la FICHA."""
    posicion = plantilla.index(FICHA)
    return {
        "Value": {
            "string": plantilla,
            "attachmentsByRange": {
                f"{{{posicion}, 1}}": {
                    "OutputUUID": identificador,
                    "Type": "ActionOutput",
                    "OutputName": nombre,
                }
            },
        },
        "WFSerializationType": "WFTextTokenString",
    }


def campo(clave: str, valor) -> dict:
    return {
        "WFItemType": 0,
        "WFKey": texto_plano(clave),
        "WFValue": valor if isinstance(valor, dict) else texto_plano(valor),
    }


def diccionario(*campos: dict) -> dict:
    return {
        "Value": {"WFDictionaryFieldValueItems": list(campos)},
        "WFSerializationType": "WFDictionaryFieldValue",
    }


def accion(identificador: str, **parametros) -> dict:
    return {
        "WFWorkflowActionIdentifier": identificador,
        "WFWorkflowActionParameters": parametros,
    }


# El cuerpo de la petición va como texto crudo, no con el constructor de JSON de
# Atajos: así evitamos armar a mano una matriz anidada dentro de un diccionario,
# que es la parte más frágil del formato.
CUERPO_JSON = (
    '{"model":"claude-opus-5",'
    '"max_tokens":500,'
    '"thinking":{"type":"disabled"},'
    '"output_config":{"effort":"low"},'
    f'"system":"{PROMPT_SISTEMA}",'
    f'"messages":[{{"role":"user","content":"{FICHA}"}}]}}'
)

ACCIONES = [
    # 1. La clave de la API. Atajos la pide al importar (ver WFWorkflowImportQuestions).
    accion(
        "is.workflow.actions.gettext",
        UUID=ID_CLAVE,
        WFTextActionText="PEGA-AQUI-TU-CLAVE",
    ),
    # 2. Dictado: escucha hasta que haces una pausa.
    accion(
        "is.workflow.actions.dictatetext",
        UUID=ID_DICTADO,
        WFSpeechLanguage="es-ES",
        WFDictateTextStopListening="After Pause",
    ),
    # 3 y 4. Escapamos \ y " para que lo dictado no rompa el JSON. El orden importa.
    accion(
        "is.workflow.actions.text.replace",
        WFReplaceTextFind="\\",
        WFReplaceTextReplace="\\\\",
        WFReplaceTextRegularExpression=False,
        WFReplaceTextCaseSensitive=True,
    ),
    accion(
        "is.workflow.actions.text.replace",
        UUID=ID_ESCAPE2,
        WFReplaceTextFind='"',
        WFReplaceTextReplace='\\"',
        WFReplaceTextRegularExpression=False,
        WFReplaceTextCaseSensitive=True,
    ),
    # 5. El cuerpo de la petición, con lo dictado ya escapado dentro.
    accion(
        "is.workflow.actions.gettext",
        UUID=ID_CUERPO,
        WFTextActionText=texto_con_variable(CUERPO_JSON, ID_ESCAPE2, "Updated Text"),
    ),
    # 6. La llamada a la API.
    accion(
        "is.workflow.actions.downloadurl",
        WFURL="https://api.anthropic.com/v1/messages",
        WFHTTPMethod="POST",
        ShowHeaders=True,
        WFHTTPHeaders=diccionario(
            campo("x-api-key", texto_con_variable(FICHA, ID_CLAVE)),
            campo("anthropic-version", "2023-06-01"),
            campo("content-type", "application/json"),
        ),
        WFHTTPBodyType="File",
        WFRequestVariable=salida_de(ID_CUERPO),
    ),
    # 7, 8 y 9. Sacar el texto de la respuesta: content → primer bloque → text.
    accion("is.workflow.actions.getvalueforkey", WFDictionaryKey="content"),
    accion("is.workflow.actions.getitemfromlist", WFItemSpecifier="First Item"),
    accion("is.workflow.actions.getvalueforkey", UUID=ID_TEXTO, WFDictionaryKey="text"),
    # 10. Responder en voz alta.
    accion(
        "is.workflow.actions.speaktext",
        WFText=salida_de(ID_TEXTO, "Dictionary Value"),
        WFSpeakTextWait=True,
        WFSpeakTextLanguage="es-ES",
    ),
]

ATAJO = {
    "WFWorkflowClientVersion": "2605.0.5",
    "WFWorkflowMinimumClientVersion": 900,
    "WFWorkflowMinimumClientVersionString": "900",
    "WFWorkflowIcon": {
        "WFWorkflowIconStartColor": 3980825855,  # magenta, el color de Atajos
        "WFWorkflowIconGlyphNumber": 59504,
        "WFWorkflowIconImageData": b"",
    },
    "WFWorkflowTypes": ["NCWidget", "WatchKit"],
    "WFWorkflowInputContentItemClasses": [
        "WFAppStoreAppContentItem",
        "WFArticleContentItem",
        "WFContactContentItem",
        "WFDateContentItem",
        "WFEmailAddressContentItem",
        "WFGenericFileContentItem",
        "WFImageContentItem",
        "WFiTunesProductContentItem",
        "WFLocationContentItem",
        "WFDCMapsLinkContentItem",
        "WFAVAssetContentItem",
        "WFPDFContentItem",
        "WFPhoneNumberContentItem",
        "WFRichTextContentItem",
        "WFSafariWebPageContentItem",
        "WFStringContentItem",
        "WFURLContentItem",
    ],
    # Atajos pregunta esto al importar, así la clave no viaja dentro del archivo.
    "WFWorkflowImportQuestions": [
        {
            "ActionIndex": 0,
            "Category": "Parameter",
            "ParameterKey": "WFTextActionText",
            "Text": "Pega tu clave de la API de Anthropic (empieza por sk-ant-)",
            "DefaultValue": "",
        }
    ],
    "WFWorkflowActions": ACCIONES,
    "WFWorkflowHasOutputFallback": False,
    "WFWorkflowHasShortcutInputVariables": False,
    "WFQuickActionSurfaces": [],
}


def main() -> None:
    with SALIDA.open("wb") as f:
        plistlib.dump(ATAJO, f, fmt=plistlib.FMT_BINARY)
    print(f"✓ {SALIDA}  ({SALIDA.stat().st_size} bytes, {len(ACCIONES)} acciones)")


if __name__ == "__main__":
    main()
