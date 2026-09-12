# Vía SSH: tres acciones y la clave fuera del teléfono

Si tienes un ordenador que puedas dejar encendido (un Mac, un Linux, una
Raspberry Pi), la acción **Ejecutar script por SSH** de Atajos hace el atajo
mucho más simple que llamar a la API desde el teléfono.

```
Dictar texto  →  Ejecutar script por SSH  →  Hablar texto
```

Tres acciones. Sin construir JSON, sin variables incrustadas y, sobre todo,
**sin la clave de la API dentro del atajo**: vive en el ordenador.

La clave del asunto es el campo **Entrada** de la acción: lo que le pases ahí
llega al script por *stdin*. Así el texto dictado no viaja como argumento de
línea de comandos y desaparece el problema de las comillas y los escapes.

## En el ordenador

Instala el proyecto como dice el [README](../README.md) y comprueba que
responde:

```bash
echo "hola, ¿me oyes?" | .venv/bin/python -m voz.pregunta
```

`voz/pregunta.py` lee el texto de stdin, pregunta a Claude y escribe la
respuesta en stdout, sin markdown, lista para leerse en voz alta. Guarda el hilo
de la conversación durante 10 minutos en `~/.cache/quim/sesion.json`, así las
preguntas encadenadas mantienen el contexto sin que el teléfono tenga que llevar
el historial.

| Variable | Por defecto | Para qué |
|---|---|---|
| `VOZ_SESION_TTL` | `600` | Segundos que dura el hilo antes de empezar de cero |

Con `--nuevo` fuerza una conversación limpia.

Activa el acceso remoto:

- **macOS** → Ajustes → General → Compartir → **Sesión remota**.
- **Linux** → `sudo systemctl enable --now ssh`.

## En el iPhone

Atajos → **+** → tres acciones:

1. <b>Dictar texto</b> — Idioma `Español`, Dejar de escuchar `Tras una pausa`.
2. <b>Ejecutar script por SSH</b>:

   | Campo | Valor |
   |---|---|
   | **Script** | `cd ~/quim && .venv/bin/python -m voz.pregunta` |
   | **Host** | la IP local del ordenador, p. ej. `192.168.1.42` |
   | **Puerto** | `22` |
   | **Usuario** | tu usuario, **no** `root` |
   | **Autenticación** | `Clave SSH` (ver abajo) |
   | **Entrada** | la variable **Texto dictado** |

3. <b>Hablar texto</b> — con la salida del script. Activa **Esperar hasta terminar**.

Renombra el atajo a `Claude` y di **«Oye Siri, Claude»**.

> Los valores que Atajos muestra en gris (`192.168.1.100`, `raíz`) son ejemplos,
> no configuración: hay que escribir los tuyos.

## Autenticación: usa clave, no contraseña

En **Autenticación** elige `Clave SSH`. Atajos genera un par de claves y te deja
copiar la pública; pégala en el ordenador:

```bash
mkdir -p ~/.ssh && chmod 700 ~/.ssh
echo "ssh-ed25519 AAAA... (la que copiaste de Atajos)" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

Dos motivos para no usar `root` con contraseña, que es lo que sugiere el ejemplo
de Atajos: la contraseña queda guardada en el atajo igual que quedaría la clave
de la API, así que no ganas nada en seguridad; y si alguna vez expones ese puerto
a internet, un `root` con contraseña es el primer objetivo de cualquier escaneo
automático.

## Lo que pierdes

El ordenador tiene que estar **encendido y en la misma red**. Fuera de casa la IP
local no responde. Las salidas razonables, de menos a más trabajo:

- **Tailscale** en el teléfono y en el ordenador: te da una IP fija que funciona
  desde cualquier red, sin abrir puertos en el router. Es lo que yo haría.
- Una **VPN** propia (WireGuard), si ya tienes una.
- Abrir el puerto 22 en el router. Funciona, pero no lo hagas: es exponer tu
  máquina a internet para ahorrarte instalar Tailscale.

Y si el ordenador está apagado, el atajo no responde. Por eso esta vía va bien en
casa, y la que llama directamente a la API va bien en cualquier sitio. No es
descabellado tener las dos, con nombres distintos.
