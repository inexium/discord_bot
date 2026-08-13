# PZ Reboot Bot

Bot Discord minimal avec une seule commande : `/reboot`, qui envoie `quit` en
RCON au serveur Project Zomboid.

## Fonctionnement

- **Whitelist** : seuls les IDs Discord listés dans `ALLOWED_USER_IDS` (séparés
  par des virgules) peuvent utiliser la commande. Tout le monde peut la voir
  et l'exécuter, mais elle est rejetée pour les non-autorisés.
- **Cooldown** : 3 minutes, **global** (pas par utilisateur) — si quelqu'un
  vient de déclencher un reboot, personne d'autre ne peut en relancer un
  avant l'expiration du délai, peu importe qui.
- **RCON** : `RCON_HOST` doit pointer vers une adresse **interne**
  (nom du service Docker, ou `127.0.0.1` si tout tourne sur le même hôte) —
  jamais une IP/port exposé publiquement.

## Setup

1. Crée une application sur https://discord.com/developers/applications,
   ajoute un Bot, récupère le token.
2. Sous OAuth2 > URL Generator, coche `bot` + `applications.commands`,
   permission minimale (Send Messages), génère le lien d'invitation, ajoute
   le bot à ton serveur.
3. Récupère ton `GUILD_ID` (clic droit sur le serveur > Copier l'ID, mode
   développeur activé dans Discord) pour une synchro instantanée des
   commandes en dev. Laisse vide pour une synchro globale (peut prendre
   jusqu'à 1h à se propager).
4. Récupère les IDs Discord des personnes autorisées (clic droit sur leur
   profil > Copier l'ID utilisateur).
5. Copie `.env.example` en `.env` et remplis tout.

## Intégration dans ton compose existant

Copie `pz-reboot-bot/` à côté de ton compose du serveur PZ, puis ajoute le
contenu de `docker-compose.snippet.yml` à ton `docker-compose.yml` principal
(en adaptant le nom du réseau pour qu'il corresponde à celui de ton
conteneur PZ).

```bash
docker compose up -d --build pz-bot
docker compose logs -f pz-bot
```

## Test

Dans Discord, tape `/reboot`. Avec un compte autorisé : la commande envoie
`quit` en RCON et confirme. Avec un compte non listé : message de refus,
sans consommer le cooldown. En répétant trop vite : message d'attente avec
le temps restant.
