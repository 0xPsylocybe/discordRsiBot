# Discord RSI Verification Bot

A Discord bot that verifies [Roberts Space Industries (RSI)](https://robertsspaceindustries.com) accounts by confirming ownership through a unique cryptographic token that the user temporarily places in their public bio.

## How It Works

1. A user runs the `/verify` slash command with their RSI handle.
2. The bot generates a unique cryptographic token and shows it to the user.
3. The user pastes the token into their RSI profile bio (Short Bio / Description).
4. The user clicks the **Confirm Verification** button in Discord.
5. The bot fetches the RSI profile, confirms the token is in the bio, and checks the account's age.
6. If valid, the bot assigns the configured role and syncs the user's Discord nickname with their RSI handle.

## Requirements

- Python 3.10+
- A Discord bot token from the [Discord Developer Portal](https://discord.com/developers/applications)
- The following Python packages:
  - `discord.py`
  - `aiohttp`
  - `beautifulsoup4`
  - `python-dotenv`

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/your-username/discordRsiVerificationBot.git
cd discordRsiVerificationBot
```

### 2. Install dependencies

```bash
pip install discord.py aiohttp beautifulsoup4 python-dotenv
```

### 3. Configure the bot

Copy the example file and rename it:

```bash
cp botVerify.example.py botVerify.py
```

Open `botVerify.py` and edit the **⚙️ CONFIGURATION** section at the top:

| Variable | Default | Description |
|---|---|---|
| `VERIFIED_ROLE_NAME` | `"RSI Verified"` | Role name to assign after verification (must exist in your server) |
| `MIN_ACCOUNT_AGE_DAYS` | `0` | Minimum RSI account age in days (set to 0 for testing) |
| `TOKEN_PREFIX` | `"VERIFY"` | Prefix for the generated verification token |
| `CACHE_TTL_SECONDS` | `600` | Seconds before a pending verification expires |
| `BOT_COMMAND_PREFIX` | `"!"` | Prefix for text commands (e.g. `!setup_verify`) |

### 4. Create the `.env` file

Create a file named `.env` in the project root:

```env
DISCORD_TOKEN=your_bot_token_here
```

> ⚠️ **Never commit your `.env` file or your real bot token.** The `.gitignore` already excludes both.

### 5. Configure Discord permissions

In the [Discord Developer Portal](https://discord.com/developers/applications):
- Go to **Bot → Privileged Gateway Intents** and enable:
  - **Server Members Intent**
  - **Message Content Intent**
- Go to **OAuth2 → URL Generator**, select the `bot` and `applications.commands` scopes, and grant the following permissions:
  - Manage Roles
  - Manage Nicknames
  - Send Messages
  - Use Slash Commands

### 6. Run the bot

```bash
python botVerify.py
```

### 7. Post the verification panel

In your Discord server, go to the verification channel and run:

```
!setup_verify
```

> Requires **Administrator** permission. The bot will post the verification embed and delete the command message.

## Commands

| Command | Type | Description |
|---|---|---|
| `/verify [rsi_handle]` | Slash | Start the RSI verification flow |
| `!setup_verify` | Prefix | Post the verification panel (admin only) |

## Important Notes

- The bot's role in the server **must be positioned above** the verified role in the role hierarchy (Server Settings → Roles), otherwise it won't be able to assign it.
- The user's RSI profile **must be set to Public** for the bio scraping and date extraction to work.
- The verification token expires after `CACHE_TTL_SECONDS` (default: 10 minutes). The user must complete the process before it expires.
- This bot does **not** store any data permanently — the verification cache is in memory only and resets on restart.
