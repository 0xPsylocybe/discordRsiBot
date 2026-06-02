# Bot de Verificación de RSI para Discord

Un bot de Discord que verifica cuentas de [Roberts Space Industries (RSI)](https://robertsspaceindustries.com) confirmando la propiedad mediante un token criptográfico único que el usuario coloca temporalmente en su bio pública. Los usuarios verificados se almacenan en una base de datos SQLite local, lo que habilita funciones adicionales como el comando `/hangar`.

## Cómo funciona

1. Un usuario ejecuta el comando slash `/verify` con su handle de RSI.
2. El bot genera un token criptográfico único y se lo muestra al usuario.
3. El usuario pega el token en la bio de su perfil de RSI (Short Bio / Description).
4. El usuario pulsa el botón **Confirmar Verificación** en Discord.
5. El bot obtiene el perfil de RSI, confirma que el token está en la bio y comprueba la antigüedad de la cuenta.
6. Si todo es válido, el bot asigna el rol configurado, sincroniza el apodo de Discord del usuario con su handle de RSI y **guarda el handle en la base de datos local** para uso futuro.

## Requisitos

- Python 3.10+
- Un token de bot de Discord del [Discord Developer Portal](https://discord.com/developers/applications)
- Los siguientes paquetes de Python (todos listados en `requirements.txt`):
  - `discord.py`
  - `aiohttp`
  - `beautifulsoup4`
  - `python-dotenv`
  - `aiosqlite`

## Configuración

### 1. Clonar el repositorio

```bash
git clone https://github.com/tu-usuario/discordRsiBot.git
cd discordRsiBot
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar el bot

Copia el archivo de ejemplo y renómbralo:

```bash
cp botVerify.example.py botVerify.py
```

Abre `botVerify.py` y edita la sección **⚙️ CONFIGURATION** al principio del archivo:

| Variable | Por defecto | Descripción |
|---|---|---|
| `VERIFIED_ROLE_NAME` | `"RSI Verified"` | Nombre del rol a asignar tras la verificación (debe existir en tu servidor) |
| `MIN_ACCOUNT_AGE_DAYS` | `0` | Antigüedad mínima de la cuenta RSI en días (pon 0 para pruebas) |
| `TOKEN_PREFIX` | `"VERIFY"` | Prefijo del token de verificación generado |
| `CACHE_TTL_SECONDS` | `600` | Segundos antes de que expire una verificación pendiente |
| `BOT_COMMAND_PREFIX` | `"!"` | Prefijo para los comandos de texto (ej. `!setup_verify`) |
| `DB_PATH` | `"verified_users.db"` | Ruta al archivo de base de datos SQLite local (está en el .gitignore) |

### 4. Crear el archivo `.env`

Crea un archivo llamado `.env` en la raíz del proyecto:

```env
DISCORD_TOKEN=tu_token_de_bot_aquí
```

> ⚠️ **Nunca subas tu archivo `.env` ni tu token real a un repositorio.** El `.gitignore` ya los excluye. El archivo de base de datos SQLite (`*.db`) también está excluido.

### 5. Configurar los permisos de Discord

En el [Discord Developer Portal](https://discord.com/developers/applications):
- Ve a **Bot → Privileged Gateway Intents** y activa:
  - **Server Members Intent**
  - **Message Content Intent**
- Ve a **OAuth2 → URL Generator**, selecciona los scopes `bot` y `applications.commands`, y otorga los siguientes permisos:
  - Gestionar Roles
  - Gestionar Apodos
  - Enviar Mensajes
  - Usar Comandos Slash

### 6. Ejecutar el bot

```bash
python botVerify.py
```

El bot creará automáticamente el archivo de base de datos `verified_users.db` la primera vez que arranque.

### 7. Publicar el panel de verificación

En tu servidor de Discord, ve al canal de verificación y ejecuta:

```
!setup_verify
```

> Requiere permiso de **Administrador**. El bot publicará el embed de verificación y borrará el mensaje del comando.

## Comandos

| Comando | Tipo | Descripción |
|---|---|---|
| `/verify [rsi_handle]` | Slash | Iniciar el proceso de verificación de RSI |
| `/hangar` | Slash | Mostrar tu hangar público de naves desde [FleetYards.net](https://fleetyards.net) |
| `!setup_verify` | Prefijo | Publicar el panel de verificación (solo admins) |

## Comando /hangar

El comando `/hangar` obtiene y muestra el hangar público de naves del usuario autenticado desde [FleetYards.net](https://fleetyards.net).

**Requisitos:**
- El usuario debe haber completado el flujo `/verify` previamente. Su handle de RSI queda guardado en la base de datos local en ese momento.
- El usuario debe tener una cuenta en [FleetYards.net](https://fleetyards.net) usando el **mismo nombre de usuario que su handle de RSI** (práctica estándar en la comunidad).
- El hangar debe estar configurado como **Público** en los ajustes de FleetYards (Perfil → Settings → Public Hangar).

> **Nota:** El hangar propio de RSI no es accesible públicamente sin iniciar sesión, por lo que este comando utiliza FleetYards.net como fuente de datos.

## Notas importantes

- El rol del bot en el servidor **debe estar por encima** del rol verificado en la jerarquía de roles (Ajustes del Servidor → Roles), de lo contrario no podrá asignarlo.
- El perfil de RSI del usuario **debe estar en modo Público** para que el bot pueda leer la bio y la fecha de alta.
- El token de verificación expira tras `CACHE_TTL_SECONDS` (por defecto: 10 minutos). El usuario debe completar el proceso antes de que expire.
- Los usuarios verificados se **almacenan de forma persistente** en una base de datos SQLite local (`verified_users.db`). Este archivo está en el `.gitignore` y solo existe en tu máquina.
- Si un usuario se verifica de nuevo (p. ej. con un handle diferente), su registro en la base de datos se actualiza automáticamente (`INSERT OR REPLACE`).
