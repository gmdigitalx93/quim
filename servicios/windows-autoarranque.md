# Autoarranque en Windows

1. Crea `iniciar-voz.vbs` en la carpeta del proyecto (arranca sin ventana de consola):

   ```vbscript
   Set sh = CreateObject("WScript.Shell")
   sh.CurrentDirectory = "C:\ruta\al\proyecto"
   sh.Run """C:\ruta\al\proyecto\.venv\Scripts\pythonw.exe"" -m voz", 0, False
   ```

2. Pulsa `Win+R`, escribe `shell:startup` y pega ahí un acceso directo al `.vbs`.

Alternativa con el Programador de tareas (permite reinicio automático):

```powershell
schtasks /create /tn "Asistente de voz Claude" /sc onlogon /rl highest ^
  /tr "C:\ruta\al\proyecto\.venv\Scripts\pythonw.exe -m voz"
```

Comprueba que Windows tiene permitido el acceso al micrófono en
*Configuración → Privacidad y seguridad → Micrófono*.
