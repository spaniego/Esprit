# Cambios

## 0.1.0 — edición compartible

Configuración por usuario y módulos opcionales. Instalación mediante entrevista,
plantillas de workspace y personalización con Claude. Viajes UAM opcional con
registro propio; clúster asistido. Identificador independiente `es.asgomez.esprit`.

## 0.2.0-beta.1

- Primera beta Windows x64 con instalador NSIS y compilación CI.
- Fechas IANA, apertura de archivos, exportaciones y bloqueo de registros portables.
- Gmail/Calendar de Claude como fuentes de lectura explícitas de los rituales.
- Guía UAM → Gmail, instalación Windows y credenciales Mattermost nativas.
- LaTeX y clúster nativos pendientes en Windows; macOS conserva sus módulos.

## Sin publicar — correcciones Windows

- Chat: IDs de conversación con el RNG del sistema (`getrandom`); `/dev/urandom` no existe en Windows.
- Sin ventanas de consola: Python, Claude y Codex se lanzan con `CREATE_NO_WINDOW`.
- Puentes Python con `PYTHONUTF8=1`: tildes y eñes ya no rompen Mattermost.
- Conectores de claude.ai actuales: Gmail `search_threads`/`list_labels` y Calendar
  `search_events`; `calendarId` omitido equivale a `primary`.
- `check_config.py` valida la zona con `zoneinfo`; correcciones menores de plantilla y esquema.
