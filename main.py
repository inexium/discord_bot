import logging
import os
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands
from rcon.source import rcon

# ---------------------------------------------------------------------------
# Config (tout vient de l'environnement)
# ---------------------------------------------------------------------------

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
GUILD_ID = os.environ.get("GUILD_ID")  # optionnel : sync instantanée sur un seul serveur

RCON_HOST = os.environ.get("RCON_HOST", "pzserver")  # nom du service docker, PAS une IP publique
RCON_PORT = int(os.environ.get("RCON_PORT", "16262"))
RCON_PASSWORD = os.environ["RCON_PASSWORD"]

ALLOWED_USER_IDS = {
    int(uid.strip())
    for uid in os.environ.get("ALLOWED_USER_IDS", "").split(",")
    if uid.strip()
}
if not ALLOWED_USER_IDS:
    raise RuntimeError("ALLOWED_USER_IDS est vide — personne ne pourrait utiliser /reboot")

COOLDOWN_SECONDS = 180  # 3 minutes, cooldown GLOBAL (partagé entre tous les users)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("pz-reboot-bot")

# ---------------------------------------------------------------------------
# Bot
# ---------------------------------------------------------------------------

intents = discord.Intents.default()  # pas besoin d'intents privilégiés pour des slash commands
bot = commands.Bot(command_prefix="!", intents=intents)

# État du cooldown, en mémoire, partagé par tout le monde (pas de bucket par user)
_last_reboot_at: datetime | None = None


def is_allowed(user_id: int) -> bool:
    return user_id in ALLOWED_USER_IDS


@bot.event
async def on_ready():
    if GUILD_ID:
        guild = discord.Object(id=int(GUILD_ID))
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)
    else:
        await bot.tree.sync()
    logger.info("Connecté en tant que %s", bot.user)


@bot.tree.command(name="reboot", description="Redémarre le serveur Project Zomboid")
async def reboot(interaction: discord.Interaction):
    global _last_reboot_at

    # 1. Vérification de la whitelist AVANT toute logique de cooldown,
    #    pour qu'un utilisateur non autorisé ne puisse pas brûler le
    #    cooldown global à la place de quelqu'un d'autorisé.
    if not is_allowed(interaction.user.id):
        logger.warning("Tentative refusée: %s (%s)", interaction.user, interaction.user.id)
        await interaction.response.send_message(
            "Tu n'es pas autorisé à utiliser cette commande.", ephemeral=True
        )
        return

    # 2. Cooldown global
    now = datetime.now(timezone.utc)
    if _last_reboot_at is not None:
        elapsed = (now - _last_reboot_at).total_seconds()
        if elapsed < COOLDOWN_SECONDS:
            remaining = int(COOLDOWN_SECONDS - elapsed)
            await interaction.response.send_message(
                f"⏳ Un redémarrage a déjà été déclenché récemment. Réessaie dans {remaining}s.",
                ephemeral=True,
            )
            return

    _last_reboot_at = now
    await interaction.response.defer(thinking=True)

    logger.info("Reboot demandé par %s (%s)", interaction.user, interaction.user.id)

    try:
        await rcon("quit", host=RCON_HOST, port=RCON_PORT, passwd=RCON_PASSWORD)
    except Exception as e:
        logger.error("Erreur RCON: %s", e)
        await interaction.followup.send(f"❌ Échec de l'envoi de la commande RCON : {e}")
        _last_reboot_at = None  # on ne pénalise pas tout le monde pour un échec technique
        return

    await interaction.followup.send(
        f"✅ Commande `quit` envoyée par {interaction.user.mention}. Le serveur redémarre."
    )


@bot.tree.command(name="players", description="Affiche le nombre de joueurs connectés sur le serveur Project Zomboid")
async def players(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)

    try:
        response = await rcon("players", host=RCON_HOST, port=RCON_PORT, passwd=RCON_PASSWORD)
    except Exception as e:
        logger.error("Erreur RCON: %s", e)
        await interaction.followup.send(f"❌ Échec de la récupération des joueurs : {e}")
        return

    names = [
        line.strip()[1:].strip()
        for line in response.splitlines()
        if line.strip().startswith("-")
    ]

    if names:
        liste = "\n".join(f"- {name}" for name in names)
        await interaction.followup.send(f"🧟 **{len(names)} joueur(s) connecté(s)** :\n{liste}")
    else:
        await interaction.followup.send("🧟 **0 joueur connecté** sur le serveur.")


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
