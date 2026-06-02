# ============================================================
# botVerify.example.py — Discord RSI Verification Bot (Template)
# botVerify.example.py — Bot de Verificación de RSI para Discord (Plantilla)
#
# EN: Copy this file, rename it to botVerify.py, and edit the
#     CONFIGURATION section below to set it up for your community.
#     Also create a .env file with: DISCORD_TOKEN=your_token_here
#
# ES: Copia este archivo, renómbralo como botVerify.py, y edita la
#     sección CONFIGURATION de abajo para adaptarlo a tu comunidad.
#     Crea también un archivo .env con: DISCORD_TOKEN=tu_token_aquí
# ============================================================

import asyncio
import secrets
import re
import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime
import os
import aiosqlite
from dotenv import load_dotenv

# EN: Load environment variables from the .env file
# ES: Cargar las variables de entorno desde el archivo .env
load_dotenv()

# ==========================================
# ⚙️  CONFIGURATION / CONFIGURACIÓN
# ==========================================
# EN: Everything you need to customize is in this block.
# ES: Todo lo que necesitas personalizar está en este bloque.

# EN: Bot token — get it from https://discord.com/developers/applications
#     Store it in your .env file as:  DISCORD_TOKEN=your_token_here
# ES: Token del bot — obtenlo en https://discord.com/developers/applications
#     Guárdalo en tu archivo .env como:  DISCORD_TOKEN=tu_token_aquí
TOKEN = os.getenv("DISCORD_TOKEN")

# EN: The exact name (case-sensitive) of the Discord role to grant after verification.
#     You must create this role manually in your server before running the bot.
# ES: El nombre exacto (sensible a mayúsculas) del rol de Discord a otorgar tras la verificación.
#     Debes crear este rol manualmente en tu servidor antes de ejecutar el bot.
VERIFIED_ROLE_NAME = "RSI Verified"  # ← customize / personaliza

# EN: Minimum RSI account age in days to pass verification.
#     Set to 0 for testing, then raise it for production (e.g. 30).
# ES: Antigüedad mínima de la cuenta RSI en días para pasar la verificación.
#     Pon 0 para pruebas, luego auméntalo para producción (ej. 30).
MIN_ACCOUNT_AGE_DAYS = 0  # ← change me / cámbiame

# EN: Prefix used in the generated verification token.
#     Use your community's tag or acronym.
#     Example: "VERIFY" → token looks like "VERIFY-a3f9c12e45b67d89"
# ES: Prefijo del token de verificación generado.
#     Usa el tag o acrónimo de tu comunidad.
#     Ejemplo: "VERIFY" → el token tiene el aspecto "VERIFY-a3f9c12e45b67d89"
TOKEN_PREFIX = "VERIFY"  # ← change me / cámbiame

# EN: Time in seconds before an unconfirmed pending verification expires.
#     Default: 600 seconds = 10 minutes.
# ES: Tiempo en segundos antes de que una verificación pendiente no confirmada expire.
#     Por defecto: 600 segundos = 10 minutos.
CACHE_TTL_SECONDS = 600

# EN: Prefix for text-based commands (e.g. !setup_verify).
# ES: Prefijo para los comandos de texto (ej. !setup_verify).
BOT_COMMAND_PREFIX = "!"  # ← change me / cámbiame

# EN: Path to the local SQLite database file that stores verified user records.
#     This file is gitignored — it stays only on your machine.
# ES: Ruta al archivo de base de datos SQLite que almacena los usuarios verificados.
#     Este archivo está en el .gitignore — solo existe en tu máquina.
DB_PATH = "verified_users.db"


# ==========================================
# DATABASE HELPERS / FUNCIONES DE BASE DE DATOS
# ==========================================

async def init_db():
    """
    EN: Initialises the SQLite database and creates the verified_users table if it does not exist.
        Called once at bot startup from setup_hook.
    ES: Inicializa la base de datos SQLite y crea la tabla verified_users si no existe.
        Se llama una vez al inicio del bot desde setup_hook.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS verified_users (
                discord_id  INTEGER PRIMARY KEY,
                rsi_handle  TEXT    NOT NULL,
                verified_at TEXT    NOT NULL
            )
        """)
        await db.commit()


async def save_verified_user(discord_id: int, rsi_handle: str):
    """
    EN: Inserts or updates the RSI handle for a Discord user after successful verification.
    ES: Inserta o actualiza el handle de RSI para un usuario de Discord tras la verificación exitosa.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO verified_users (discord_id, rsi_handle, verified_at) VALUES (?, ?, ?)",
            (discord_id, rsi_handle, datetime.now().isoformat())
        )
        await db.commit()


async def get_rsi_handle(discord_id: int) -> str | None:
    """
    EN: Returns the RSI handle linked to a Discord user ID, or None if not found.
    ES: Devuelve el handle de RSI vinculado a un ID de Discord, o None si no se encuentra.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT rsi_handle FROM verified_users WHERE discord_id = ?",
            (discord_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


class VerificationBot(commands.Bot):
    """
    EN: Custom bot class that registers the persistent verification view and syncs
        slash commands globally on startup.
    ES: Clase de bot personalizada que registra la vista de verificación persistente
        y sincroniza los comandos slash globalmente al iniciar.
    """
    def __init__(self):
        intents = discord.Intents.default()
        # EN: Required to read message content
        # ES: Necesario para leer el contenido de mensajes
        intents.message_content = True
        # EN: Required to manage members and roles
        # ES: Necesario para gestionar miembros y roles
        intents.members = True
        super().__init__(command_prefix=BOT_COMMAND_PREFIX, intents=intents)

    async def setup_hook(self):
        # EN: Initialise the SQLite database before anything else runs
        # ES: Inicializar la base de datos SQLite antes de que se ejecute nada más
        await init_db()
        # EN: Register the persistent view so the button survives bot restarts
        # ES: Registrar la vista persistente para que el botón sobreviva a los reinicios del bot
        self.add_view(VerificationView())
        # EN: Sync slash commands globally (may take up to 1h to propagate on first run)
        # ES: Sincronizar comandos slash globalmente (puede tardar hasta 1h en propagarse la primera vez)
        await self.tree.sync()
        print("[Bot] Slash commands synced globally. / Comandos slash sincronizados globalmente.")


bot = VerificationBot()

# EN: In-memory dictionary storing pending verifications.
#     Format: { discord_user_id: { "rsi_name": str, "code": str } }
# ES: Diccionario en memoria que almacena las verificaciones pendientes.
#     Formato: { discord_user_id: { "rsi_name": str, "code": str } }
verification_cache: dict = {}


async def expire_verification(user_id: int):
    """
    EN: Background task that removes a user's pending verification from the cache
        after CACHE_TTL_SECONDS if they haven't completed the process in time.
    ES: Tarea en segundo plano que elimina la verificación pendiente de un usuario del caché
        tras CACHE_TTL_SECONDS si no completó el proceso a tiempo.
    """
    await asyncio.sleep(CACHE_TTL_SECONDS)
    if user_id in verification_cache:
        del verification_cache[user_id]
        print(f"[Cache] Verification expired for user_id={user_id} / Verificación expirada para user_id={user_id}")


class VerificationView(discord.ui.View):
    def __init__(self):
        # EN: timeout=None makes this view persistent across bot restarts (requires stable custom_id)
        # ES: timeout=None hace esta vista persistente entre reinicios del bot (requiere custom_id estable)
        super().__init__(timeout=None)

    @discord.ui.button(
        label="✅ Confirm Verification / Confirmar Verificación",  # ← customize / personaliza
        style=discord.ButtonStyle.primary,
        # EN: do NOT change custom_id — must remain stable across bot restarts for persistence
        # ES: NO cambies custom_id — debe permanecer estable entre reinicios del bot para la persistencia
        custom_id="confirm_verification_btn"
    )
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # EN: Guard: DMs are not supported
        # ES: Guardia: mensajes directos no admitidos
        if not interaction.guild:
            await interaction.response.send_message(
                "❌ This command can only be used inside a server. / "
                "Este comando solo puede usarse dentro de un servidor.",
                ephemeral=True
            )
            return

        user_id = interaction.user.id

        # EN: Check if the user has an active verification entry in cache
        # ES: Comprobar si el usuario tiene una entrada de verificación activa en el caché
        if user_id not in verification_cache:
            await interaction.response.send_message(
                "❌ You haven't started a verification process. Use `/verify` first. / "
                "No has iniciado ningún proceso de verificación. Usa primero el comando `/verify`.",
                ephemeral=True
            )
            return

        # EN: Defer to avoid hitting Discord's 3-second interaction timeout during web requests
        # ES: Diferir para evitar el timeout de 3 segundos de Discord durante las peticiones web
        await interaction.response.defer(ephemeral=True)

        rsi_name = verification_cache[user_id]["rsi_name"]
        expected_code = verification_cache[user_id]["code"]

        # EN: RSI handles are case-insensitive on their site, so we lowercase the URL
        # ES: Los handles de RSI no son sensibles a mayúsculas en su web, así que usamos minúsculas en la URL
        rsi_url = f"https://robertsspaceindustries.com/citizens/{rsi_name.lower()}"

        # EN: Fetch the RSI public profile page via HTTP
        # ES: Obtener la página de perfil público de RSI por HTTP
        async with aiohttp.ClientSession() as session:
            try:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                async with session.get(rsi_url, headers=headers) as response:
                    if response.status == 404:
                        await interaction.followup.send(
                            f"❌ Citizen `{rsi_name}` was not found in the RSI database. / "
                            f"El ciudadano `{rsi_name}` no se encontró en la base de datos de RSI.",
                            ephemeral=True
                        )
                        return
                    elif response.status != 200:
                        await interaction.followup.send(
                            "⚠️ Connection error with RSI servers. Please try again later. / "
                            "Error de conexión con los servidores de RSI. Inténtalo de nuevo más tarde.",
                            ephemeral=True
                        )
                        return
                    html = await response.text()
            except Exception as e:
                await interaction.followup.send(
                    f"⚠️ Error connecting to RSI: {str(e)} / Error al conectar con RSI: {str(e)}",
                    ephemeral=True
                )
                return

        soup = BeautifulSoup(html, 'html.parser')

        # ------------------------------------------------------------------
        # DATE EXTRACTION / EXTRACCIÓN DE LA FECHA DE ALTA
        # EN: Find the 'Enlisted' label anywhere in the HTML and read the adjacent date element
        # ES: Buscar la etiqueta 'Enlisted' en cualquier parte del HTML y leer el elemento de fecha adyacente
        # ------------------------------------------------------------------
        enlisted_date = None
        enlisted_label = soup.find('span', class_='label', string=re.compile('Enlisted', re.IGNORECASE))

        if enlisted_label:
            date_strong = enlisted_label.find_next_sibling('strong')
            if date_strong:
                enlisted_str = date_strong.get_text(strip=True)  # EN: e.g. "May 22, 2026" | ES: ej. "May 22, 2026"
                try:
                    enlisted_date = datetime.strptime(enlisted_str, "%b %d, %Y")
                except ValueError:
                    print(f"[Date] Could not parse: {enlisted_str} / No se pudo parsear: {enlisted_str}")

        if not enlisted_date:
            await interaction.followup.send(
                "⚠️ Could not extract the enlisted date. Make sure your 'Overview' data is public on RSI. / "
                "No se pudo extraer la fecha de alta. Asegúrate de que los datos de 'Overview' sean públicos en RSI.",
                ephemeral=True
            )
            return

        # EN: Calculate the number of days since the RSI account was created
        # ES: Calcular el número de días desde que se creó la cuenta de RSI
        account_age_days = (datetime.now() - enlisted_date).days

        # EN: Reject if the account doesn't meet the minimum age requirement
        # ES: Rechazar si la cuenta no cumple el requisito mínimo de antigüedad
        if account_age_days < MIN_ACCOUNT_AGE_DAYS:
            await interaction.followup.send(
                f"❌ **Access denied.** Your account is `{account_age_days}` day(s) old. "
                f"A minimum of **{MIN_ACCOUNT_AGE_DAYS} days** is required. / "
                f"**Acceso denegado.** Tu cuenta tiene `{account_age_days}` día(s). "
                f"Se requiere un mínimo de **{MIN_ACCOUNT_AGE_DAYS} días**.",
                ephemeral=True
            )
            return

        # ------------------------------------------------------------------
        # TOKEN VALIDATION IN BIO / VALIDACIÓN DEL TOKEN EN LA BIO
        # EN: Check if the generated verification token is present in the user's public RSI bio
        # ES: Verificar si el token de verificación generado está presente en la bio pública del usuario en RSI
        # ------------------------------------------------------------------
        bio_div = soup.find('div', class_='bio')
        bio_text = bio_div.get_text() if bio_div else ""

        if expected_code in bio_text:
            guild = interaction.guild
            member = interaction.user

            # EN: Look up the verified role by its configured name
            # ES: Buscar el rol verificado por su nombre configurado
            role = discord.utils.get(guild.roles, name=VERIFIED_ROLE_NAME)
            if role:
                try:
                    await member.add_roles(role)
                    # EN: Sync the Discord nickname with the verified RSI handle
                    # ES: Sincronizar el apodo de Discord con el handle de RSI verificado
                    await member.edit(nick=rsi_name)

                    await interaction.followup.send(
                        f"✅ **Verification successful!** Your account is `{account_age_days}` day(s) old.\n"
                        f"You have been granted the `{VERIFIED_ROLE_NAME}` role. Welcome! / \n"
                        f"**¡Verificación exitosa!** Tu cuenta tiene `{account_age_days}` día(s) de antigüedad.\n"
                        f"Se te ha otorgado el rol `{VERIFIED_ROLE_NAME}`. ¡Bienvenido!",
                        ephemeral=True
                    )
                    # EN: Persist the verified user's RSI handle in the database for future commands
                    # ES: Guardar el handle RSI del usuario verificado en la base de datos para futuros comandos
                    await save_verified_user(user_id, rsi_handle)
                    # EN: Remove cache entry after successful verification to free memory
                    # ES: Eliminar la entrada del caché tras la verificación exitosa para liberar memoria
                    del verification_cache[user_id]
                except discord.Forbidden:
                    await interaction.followup.send(
                        "⚠️ Token verified, but the bot lacks permissions to assign the role or change your nickname. "
                        "Move the bot's role above all other roles in Server Settings. / "
                        "Token verificado, pero el bot no tiene permisos para asignar el rol o cambiar tu apodo. "
                        "Sube el rol del bot por encima de los demás en Ajustes del Servidor.",
                        ephemeral=True
                    )
            else:
                await interaction.followup.send(
                    f"⚠️ Token verified, but the role `{VERIFIED_ROLE_NAME}` does not exist in this server. / "
                    f"Token verificado, pero el rol `{VERIFIED_ROLE_NAME}` no existe en este servidor.",
                    ephemeral=True
                )
        else:
            await interaction.followup.send(
                f"❌ Token `{expected_code}` was not found in your public bio.\n"
                "Make sure you saved the changes and try again. / \n"
                f"El token `{expected_code}` no se encontró en tu bio pública.\n"
                "Asegúrate de que guardaste los cambios e inténtalo de nuevo.",
                ephemeral=True
            )


# ==========================================
# EVENTS AND COMMANDS / EVENTOS Y COMANDOS
# ==========================================

@bot.event
async def on_ready():
    print(f"[Bot] Ready. Logged in as {bot.user} / Listo. Conectado como {bot.user}")


@bot.command(name="setup_verify")
@commands.has_permissions(administrator=True)
async def setup_verify(ctx):
    """
    EN: Admin prefix command (!setup_verify). Posts the verification panel embed in
        the current channel and deletes the trigger message.
        Requires: Administrator permission.
    ES: Comando de prefijo de admin (!setup_verify). Publica el embed del panel de
        verificación en el canal actual y borra el mensaje que lo activó.
        Requiere: permiso de Administrador.
    """
    await ctx.message.delete()

    # EN: Customize the embed title, description, and color to match your community's theme
    # ES: Personaliza el título, la descripción y el color del embed para que coincida con el tema de tu comunidad
    embed = discord.Embed(
        title="🛸 RSI Verification Portal",  # ← customize / personaliza
        description=(
            "**Welcome!** To access the full server, verify your RSI account.\n\n"
            "🔹 **Step 1:** Use `/verify` with your RSI handle.\n"
            "🔹 **Step 2:** The bot will give you a unique verification token.\n"
            "🔹 **Step 3:** Paste the token into your RSI profile bio "
            "([Short Bio / Description](https://robertsspaceindustries.com/account/profile)).\n\n"
            "Once saved, press the button below to confirm.\n\n"
            "---\n\n"
            "**¡Bienvenido!** Para acceder al servidor completo, verifica tu cuenta de RSI.\n\n"
            "🔹 **Paso 1:** Usa `/verify` con tu handle de RSI.\n"
            "🔹 **Paso 2:** El bot te dará un token de verificación único.\n"
            "🔹 **Paso 3:** Pega el token en la bio de tu perfil de RSI "
            "([Short Bio / Description](https://robertsspaceindustries.com/account/profile)).\n\n"
            "Una vez guardado, pulsa el botón de abajo para confirmar."
        ),
        color=0x00aaff  # ← customize color / personaliza el color (hex)
    )
    await ctx.send(embed=embed)


@bot.tree.command(name="verify", description="Start the RSI account verification process. / Inicia el proceso de verificación de tu cuenta RSI.")
@app_commands.describe(rsi_handle="Your exact RSI handle / Tu handle exacto de RSI")
async def verify(interaction: discord.Interaction, rsi_handle: str):
    """
    EN: Slash command (/verify) that starts the RSI verification flow for the calling user.
    ES: Comando slash (/verify) que inicia el flujo de verificación de RSI para el usuario que lo ejecuta.
    """
    # EN: Guard: this command only works inside a server
    # ES: Guardia: este comando solo funciona dentro de un servidor
    if not interaction.guild:
        await interaction.response.send_message(
            "❌ This command can only be used inside a server. / "
            "Este comando solo puede usarse dentro de un servidor.",
            ephemeral=True
        )
        return

    user_id = interaction.user.id

    # EN: Generate a cryptographically secure random token using the secrets module
    # ES: Generar un token aleatorio criptográficamente seguro usando el módulo secrets
    generated_token = f"{TOKEN_PREFIX}-{secrets.token_hex(8)}"

    # EN: Store the RSI handle and token in the in-memory cache for this user
    # ES: Guardar el handle de RSI y el token en el caché en memoria para este usuario
    verification_cache[user_id] = {
        "rsi_name": rsi_handle,
        "code": generated_token
    }

    # EN: Schedule the TTL expiration task in the background to auto-clean the cache
    # ES: Programar la tarea de expiración TTL en segundo plano para limpiar el caché automáticamente
    asyncio.create_task(expire_verification(user_id))

    edit_profile_url = "https://robertsspaceindustries.com/account/profile"

    # EN: Build the response embed with the token and step-by-step instructions
    # ES: Construir el embed de respuesta con el token y las instrucciones paso a paso
    embed = discord.Embed(
        description=(
            f"🖥️ **Token generated for RSI handle / Token generado para el handle de RSI:** `{rsi_handle}`\n\n"
            f"Copy the token below and paste it into your RSI profile bio "
            f"(Short Bio or Description): /\n"
            f"Copia el token de abajo y pégalo en la bio de tu perfil de RSI "
            f"(Short Bio o Description):\n\n"
            f"```\n{generated_token}\n```\n"
            f"🔗 [Edit your RSI profile / Editar perfil de RSI]({edit_profile_url})\n\n"
            f"Once saved, press the button below to confirm. /\n"
            f"Una vez guardado, pulsa el botón de abajo para confirmar.\n\n"
            f"⏱️ *This token expires in {CACHE_TTL_SECONDS // 60} minute(s). / "
            f"Este token expira en {CACHE_TTL_SECONDS // 60} minuto(s).*"
        ),
        color=0x00aaff
    )

    await interaction.response.send_message(
        embed=embed,
        view=VerificationView(),
        ephemeral=True
    )


@bot.tree.command(name="hangar", description="Show your public FleetYards.net hangar. / Muestra tu hangar público en FleetYards.net.")
async def hangar(interaction: discord.Interaction):
    """
    EN: Slash command (/hangar) that fetches and displays the public FleetYards hangar
        of the verified user. Uses the RSI handle stored at verification time.
        Assumes the FleetYards username matches the RSI handle (standard in the community).
        Requires the user to be verified and to have a public hangar on FleetYards.
    ES: Comando slash (/hangar) que obtiene y muestra el hangar público de FleetYards
        del usuario verificado. Usa el handle RSI guardado en el momento de la verificación.
        Asume que el usuario de FleetYards coincide con el handle RSI (estándar en la comunidad).
        Requiere que el usuario esté verificado y tenga el hangar público en FleetYards.
    """
    # EN: Guard: this command only works inside a server
    # ES: Guardia: este comando solo funciona dentro de un servidor
    if not interaction.guild:
        await interaction.response.send_message(
            "❌ This command can only be used inside a server. / "
            "Este comando solo puede usarse dentro de un servidor.",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    user_id = interaction.user.id

    # EN: Look up the RSI handle stored when this user completed verification
    # ES: Buscar el handle RSI guardado cuando este usuario completó la verificación
    rsi_handle = await get_rsi_handle(user_id)

    if not rsi_handle:
        await interaction.followup.send(
            "❌ You are not verified yet. Use `/verify` first to link your RSI account. / "
            "No estás verificado aún. Usa primero `/verify` para enlazar tu cuenta de RSI.",
            ephemeral=True
        )
        return

    # EN: Assume the FleetYards username matches the RSI handle (standard practice in the community)
    # ES: Asumir que el usuario de FleetYards coincide con el handle de RSI (práctica estándar en la comunidad)
    fleetyards_url = f"https://fleetyards.net/{rsi_handle.lower()}/hangar"

    # EN: Fetch the public FleetYards hangar page
    # ES: Obtener la página pública del hangar en FleetYards
    async with aiohttp.ClientSession() as session:
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            async with session.get(fleetyards_url, headers=headers) as response:
                if response.status == 404:
                    await interaction.followup.send(
                        f"❌ Profile `{rsi_handle}` not found on FleetYards.net. / "
                        f"No se encontró el perfil `{rsi_handle}` en FleetYards.net.\n"
                        f"Register at [fleetyards.net]({fleetyards_url}) with your RSI handle to use this command. / "
                        f"Regístrate en [fleetyards.net]({fleetyards_url}) con tu handle de RSI para usar este comando.",
                        ephemeral=True
                    )
                    return
                elif response.status != 200:
                    await interaction.followup.send(
                        "⚠️ Could not connect to FleetYards.net. Please try again later. / "
                        "Error al conectar con FleetYards.net. Inténtalo más tarde.",
                        ephemeral=True
                    )
                    return
                html = await response.text()
        except Exception as e:
            await interaction.followup.send(
                f"⚠️ Connection error with FleetYards: {str(e)} / Error de conexión con FleetYards: {str(e)}",
                ephemeral=True
            )
            return

    soup = BeautifulSoup(html, 'html.parser')

    # ------------------------------------------------------------------
    # SHIP LIST EXTRACTION / EXTRACCCIÓN DE LA LISTA DE NAVES
    # EN: FleetYards renders hangar items server-side. We look for ship name
    #     elements using the known CSS class patterns from their HTML structure.
    # ES: FleetYards renderiza los items del hangar en el servidor. Buscamos los
    #     elementos de nombre de nave usando los patrones de clase CSS conocidos.
    # ------------------------------------------------------------------
    ships = []

    # EN: Primary selector: data-name attribute on hangar item containers
    # ES: Selector primario: atributo data-name en los contenedores de items del hangar
    for item in soup.find_all(attrs={"data-name": True}):
        name = item.get("data-name", "").strip()
        if name:
            manufacturer = item.get("data-manufacturer", "").strip()
            ships.append((name, manufacturer))

    # EN: Fallback selector: look for elements with class containing 'name' inside hangar items
    # ES: Selector alternativo: buscar elementos con clase que contenga 'name' dentro de items del hangar
    if not ships:
        for item in soup.select(".hangar-item .name, .ship-item .name, [class*='ship'] .name"):
            name = item.get_text(strip=True)
            if name:
                ships.append((name, ""))

    # EN: If no ships found, the hangar is likely private or the user has no ships registered
    # ES: Si no se encuentran naves, el hangar probablemente es privado o el usuario no tiene naves registradas
    if not ships:
        await interaction.followup.send(
            f"🔒 The hangar of `{rsi_handle}` on FleetYards is empty or set to private. / "
            f"El hangar de `{rsi_handle}` en FleetYards está vacío o configurado como privado.\n\n"
            f"To enable it, go to [fleetyards.net]({fleetyards_url}) → Profile → **Settings** → enable **Public Hangar**. / "
            f"Para activarlo, entra en [fleetyards.net]({fleetyards_url}) → Perfil → **Settings** → activa **Public Hangar**.",
            ephemeral=True
        )
        return

    # EN: Build the embed with the ship list, capping at 25 ships to stay within Discord embed limits
    # ES: Construir el embed con la lista de naves, limitando a 25 para no superar los límites de Discord
    MAX_DISPLAY = 25
    shown_ships = ships[:MAX_DISPLAY]
    overflow = len(ships) - MAX_DISPLAY

    # EN: Format each ship as a line: "• Ship Name — Manufacturer" or "• Ship Name" if no manufacturer
    # ES: Formatear cada nave como una línea: "• Nombre — Fabricante" o "• Nombre" si no hay fabricante
    ship_lines = [
        f"• **{name}**" + (f" — *{mfr}*" if mfr else "")
        for name, mfr in shown_ships
    ]

    if overflow > 0:
        ship_lines.append(f"*... and {overflow} more ship(s). See full hangar below. / y {overflow} nave(s) más. Ver hangar completo abajo.*")

    embed = discord.Embed(
        title=f"🚀 {rsi_handle}'s Hangar / Hangar de {rsi_handle}",
        description="\n".join(ship_lines),
        color=0x00aaff,
        url=fleetyards_url
    )
    embed.set_footer(text=f"Data via FleetYards.net · Datos via FleetYards.net · {len(ships)} ship(s) total")

    await interaction.followup.send(embed=embed, ephemeral=True)


# EN: Start the bot — make sure DISCORD_TOKEN is set in your .env file
# ES: Iniciar el bot — asegúrate de que DISCORD_TOKEN está definido en tu archivo .env
bot.run(TOKEN)
