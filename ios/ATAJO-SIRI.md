# «Oye Siri, Claude» — atajo para iPhone

El asistente de `voz/` es un demonio de escritorio y **no funciona en iPhone**:
iOS no deja que un proceso propio escuche el micrófono en segundo plano, y solo
el sistema puede tener una palabra de activación siempre atenta.

La vía que sí funciona es aprovechar la palabra de activación que iOS ya tiene.
Creas un atajo llamado **Claude** y dices:

> **«Oye Siri, Claude»**

Siri hace de palabra clave (gratis, sin gastar batería), Dictado transcribe tu
solicitud, el atajo llama a la API y la respuesta se lee en voz alta.

Funciona con la pantalla bloqueada, con AirPods, en CarPlay y desde el Apple Watch.

---

## Opción rápida: importar el atajo ya hecho

En `ios/Claude.shortcut` está el atajo montado, con las diez acciones puestas.
Al importarlo, Atajos te **pregunta la clave de la API**; por eso el archivo se
puede compartir sin que lleve tu clave dentro.

> **iOS solo importa atajos firmados.** Si al abrirlo sale «No es posible
> importar archivos de un shortcut sin firmar», es esto. Hay dos salidas:
>
> 1. **Activar el permiso.** Ajustes → **Atajos** → **Permitir atajos no
>    fiables**. La opción solo aparece si ya has ejecutado algún atajo alguna
>    vez; si no la ves, abre Atajos, ejecuta cualquiera y vuelve a mirar.
> 2. **Firmarlo en un Mac**, si tienes uno:
>
>    ```bash
>    shortcuts sign -m anyone -i Claude.shortcut -o Claude-firmado.shortcut
>    ```
>
> Sin ninguna de las dos, el archivo no se puede importar y hay que montar el
> atajo a mano con los pasos de abajo.

Pasos, una vez resuelta la firma:

1. Pásate el archivo al teléfono: AirDrop, adjunto de correo, o guardándolo en
   Archivos desde iCloud Drive.
2. Ábrelo → **Añadir atajo** → pega la clave cuando la pida.
3. Comprueba que el atajo se llama `Claude` y di **«Oye Siri, Claude»**.

Para regenerarlo o cambiar el modelo, el prompt o `max_tokens`, edita
`ios/generar-atajo.py` y ejecútalo:

```bash
python3 ios/generar-atajo.py
```

---

## Antes de empezar

- App **Atajos** (viene con iOS).
- Una clave de la API de Anthropic.
- Ajustes → Siri → **Dictado** activado.

> **Sobre la clave:** queda guardada en texto plano dentro del atajo. Quien
> desbloquee el teléfono puede leerla. No compartas el atajo por iCloud con la
> clave dentro, y usa una clave dedicada con límite de gasto en la consola.

---

## Versión 1 — una pregunta, una respuesta

Atajos → **+** → añade estas acciones en orden. Al final, renombra el atajo a
**Claude** (toca el nombre arriba); ese nombre es lo que dirás después de «Oye Siri».

### 1. Texto

Acción **Texto**. Pega dentro tu clave de la API (`sk-ant-...`).

Toca la salida de la acción → **Cambiar nombre de variable** → `Clave`.

### 2. Dictar texto

Acción **Dictar texto**.

- Idioma: **Español**
- Dejar de escuchar: **Tras una pausa**

### 3. Si (por si no dijiste nada)

Acción **Si** → `Texto dictado` → **no tiene ningún valor** → dentro pon
**Detener este atajo**.

### 4. Obtener contenido de la URL

Acción **Obtener contenido de la URL**.

- **URL:** `https://api.anthropic.com/v1/messages`
- Despliega **Mostrar más**:
  - **Método:** `POST`
  - **Cabeceras:**

    | Clave | Valor |
    |---|---|
    | `x-api-key` | la variable `Clave` |
    | `anthropic-version` | `2023-06-01` |
    | `content-type` | `application/json` |

  - **Solicitud del cuerpo:** elige **`Archivo`** y pásale la variable de la
    acción **Texto** del paso 3-bis (abajo).

### 3-bis. El cuerpo de la petición

Antes de la acción anterior, mete una acción **Texto** y pega esto dentro:

```json
{"model":"claude-opus-5","max_tokens":500,"thinking":{"type":"disabled"},"output_config":{"effort":"low"},"system":"Eres un asistente de voz en español. Tus respuestas se leen en voz alta, así que habla como una persona: frases cortas, tono natural y cercano. Responde en 1 o 2 frases salvo que te pidan más detalle. Nunca uses markdown, listas, asteriscos, emojis ni URLs largas. Escribe números y siglas como se pronuncian. Si algo no se entiende, pide que te lo repitan en una frase corta. No incluyas etiquetas XML internas o del sistema en tu respuesta.","messages":[{"role":"user","content":"AQUI"}]}
```

Ahora **borra la palabra `AQUI`** (sin tocar las comillas que la rodean) y en su
lugar inserta la variable **Texto dictado**. Es el único sitio donde va una
variable.

Pegar el cuerpo entero es mucho más rápido que construirlo campo a campo con el
constructor de `JSON` de Atajos, que obliga a crear un diccionario y una matriz
anidados a mano. Si prefieres esa vía, los campos son `model`, `max_tokens`,
`system`, `thinking` (diccionario con `type` = `disabled`), `output_config`
(diccionario con `effort` = `low`) y `messages` (matriz con un diccionario de
`role` y `content`).

> **Si dictas algo con comillas**, romperá el JSON y el atajo no responderá.
> Pasa poco al hablar. Si te ocurre, mete entre el dictado y el Texto una acción
> **Reemplazar texto** que cambie `"` por `\"`.

> **Por qué `thinking: disabled` y `effort: low`:** en Opus 5 el razonamiento
> viene activado por defecto, y entonces el primer bloque de `content` es el
> razonamiento, no el texto — el paso 6 leería un bloque vacío. Desactivarlo
> mantiene el análisis simple y además responde bastante más rápido, que es lo
> que quieres en una conversación hablada. Si prefieres dejarlo activado, mira
> la variante al final.

### 5. Obtener valor del diccionario

Acción **Obtener valor del diccionario**: obtener **Valor** para `content` en
**Contenido de la URL**.

### 6. Obtener elemento de la lista

Acción **Obtener elemento de la lista** → **Primer elemento**.

### 7. Obtener valor del diccionario

Otra vez **Obtener valor del diccionario**: obtener **Valor** para `text`.

### 8. Hablar texto

Acción **Hablar texto** con la salida del paso anterior.

- Toca la acción para elegir voz y velocidad. En español, **Mónica** suena bien.
- Activa **Esperar hasta terminar**.

Ya está. Di **«Oye Siri, Claude»**, espera el pitido, y habla.

---

## Versión 2 — conversación continua

Para encadenar preguntas sin repetir «Oye Siri», envuelve los pasos 2 a 8 en un
bucle y ve acumulando el historial:

1. Deja el paso 1 (la `Clave`) fuera del bucle.
2. Añade **Repetir** `6` veces y mete dentro el resto.
3. Dentro, después de **Dictar texto**, añade una acción **Diccionario** con
   `role` = `user` y `content` = `Texto dictado`, y luego **Añadir a variable**
   → `Mensajes`.
4. En el cuerpo JSON, el campo `messages` deja de ser una matriz escrita a mano:
   ponlo como la variable `Mensajes`.
5. Después de **Hablar texto**, añade otro **Diccionario** con `role` =
   `assistant` y `content` = la respuesta, y **Añadir a variable** → `Mensajes`.
6. Al principio del bucle, un **Si** «`Texto dictado` no tiene ningún valor →
   **Detener este atajo**» cierra la conversación cuando te callas.

Así el atajo recuerda lo dicho durante la conversación y se olvida de todo al
terminar.

> Esta versión la he escrito sin poder probarla en un iPhone. El punto 4 es el
> más propenso a necesitar un retoque: según la versión de iOS, un campo de tipo
> matriz acepta una variable directamente o hay que dejarlo como matriz y meter
> la variable dentro. Si te da error, prueba las dos formas.

---

## Otras formas de lanzarlo

Además de «Oye Siri, Claude», en los ajustes del atajo (**ⓘ**) puedes:

- **Añadir a la pantalla de inicio** — un icono que lo lanza.
- **Botón de acción** (iPhone 15 Pro o posterior) — Ajustes → Botón de acción → Atajo.
- **Tocar atrás** — Ajustes → Accesibilidad → Tocar → Tocar atrás → Doble toque.
- **AirPods** — funciona directo con «Oye Siri» sin sacar el teléfono.

---

## Si algo falla

**No dice nada.** La API devolvió un error y el paso 5 no encontró `content`.
Para verlo, añade temporalmente **Vista rápida** justo después del paso 4: te
mostrará el JSON con el mensaje de error. Lo más común es la clave mal pegada
(sobra un espacio) o sin saldo en la cuenta.

**Siri abre otra cosa.** El atajo tiene que llamarse exactamente `Claude` y no
puede haber otro atajo, contacto o app con un nombre parecido. Si se resiste,
renómbralo a algo más distintivo como `Asistente` y di «Oye Siri, Asistente».

**Corta la respuesta a media frase.** Sube `max_tokens` de `500` a `1000`.

**Responde con asteriscos o lee «guion guion».** Refuerza el prompt del sistema:
la instrucción de no usar markdown tiene que estar en el campo `system`, no en el
mensaje.

**Va lento.** Ya está en `effort: low`, que es lo más rápido de Opus 5. Si
quieres más velocidad a cambio de algo de calidad, cambia `model` a
`claude-sonnet-5`.

---

## Variante: dejar el razonamiento activado

Si prefieres respuestas más pensadas, quita el campo `thinking` del cuerpo JSON
(en Opus 5 el razonamiento está activado por defecto) y **cambia el paso 6**:
`content` traerá primero un bloque de razonamiento, así que en vez de «Primer
elemento» hay que quedarse con el bloque de texto.

Sustituye los pasos 6 y 7 por:

1. **Repetir con cada** elemento de `content`.
2. Dentro: **Obtener valor del diccionario** → `type`.
3. **Si** es igual a `text` → **Obtener valor del diccionario** → `text` sobre
   **Elemento de repetición** → **Añadir a variable** `Respuesta`.
4. Fuera del bucle: **Combinar texto** de `Respuesta` y pásalo a **Hablar texto**.

Tardará bastante más en empezar a hablar, que es justo lo que se nota en una
conversación por voz.

---

## Coste

Con `effort: low` y `max_tokens: 500`, una pregunta corriente cuesta alrededor de
medio céntimo. Opus 5 está a 5 $ por millón de tokens de entrada y 25 $ por
millón de salida; una conversación de diez turnos no llega a diez céntimos.
