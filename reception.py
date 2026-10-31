
import sqlite3
import hashlib
import os
import unicodedata
from datetime import datetime
from zoneinfo import ZoneInfo

import discord
from aiohttp import web


DB_PATH = "vinted_alerts.db"

# Estimation forfaitaire de 13 %
COEFFICIENT_ESTIMATION = 1.13

# Noms des salons Discord
MARQUES = {
    "nike": "🇺🇸︲nike",
    "adidas": "🇩🇪︲adidas",
    "stussy": "🇺🇸︲stussy",
    "supreme": "🇺🇸︲supreme",
    "carhartt": "🇺🇸︲carhartt",
    "ralph lauren": "🇺🇸︲ralph-lauren",
    "lacoste": "🇫🇷︲lacoste",
    "tommy hilfiger": "🇺🇸︲tommy-hilfiger",
    "hugo boss": "🇩🇪︲hugo-boss",
    "stone island": "🇮🇹︲stone-island",
    "burberry": "🇬🇧︲burberry",
    "dior": "🇫🇷︲dior",
    "gucci": "🇮🇹︲gucci",
    "prada": "🇮🇹︲prada",
    "levis": "🇺🇸︲levis",
    "dickies": "🇺🇸︲dickies",
    "patagonia": "🇺🇸︲patagonia",
    "the north face": "🇺🇸︲the-north-face",
    "arcteryx": "🇨🇦︲arcteryx",
    "nike jordan": "🇺🇸︲nike-jordan",
    "new balance": "🇺🇸︲new-balance",
    "asics": "🇯🇵︲asics",
    "salomon": "🇫🇷︲salomon",
}

SALON_ANALYSE = "🌍︲prix-a-analyser"


def normaliser_marque(marque):
    """Uniformise les accents, apostrophes et espaces."""
    texte = str(marque or "").lower().strip()

    texte = unicodedata.normalize("NFKD", texte)
    texte = "".join(
        caractere
        for caractere in texte
        if not unicodedata.combining(caractere)
    )

    # Enlever les caractères spéciaux
    texte = "".join(
        caractere
        for caractere in texte
        if caractere.isalnum()
    )

    return texte


def trouver_salon(marque):
    """Trouve le salon même si la marque a une écriture différente."""
    nom = normaliser_marque(marque)

    alias = {
        "levistrauss": "levis",
        "levistraussco": "levis",
        "arcteryx": "arcteryx",
        "stussy": "stussy",
    }

    nom = alias.get(nom, nom)

    for marque_connue, salon in MARQUES.items():
        if normaliser_marque(marque_connue) == nom:
            return salon

    return SALON_ANALYSE


async def recevoir_annonce(request):
    # Vérification de la clé API
    authorization = request.headers.get("Authorization", "")

    if not authorization.startswith("Bearer "):
        return web.json_response(
            {"erreur": "Clé manquante"},
            status=401,
        )

    cle = authorization.replace("Bearer ", "", 1)

    empreinte = hashlib.sha256(
        cle.encode("utf-8")
    ).hexdigest()

    with sqlite3.connect(DB_PATH) as db:
        client = db.execute(
            """
            SELECT guild_id, channel_id
            FROM clients
            WHERE token_hash = ? AND actif = 1
            """,
            (empreinte,),
        ).fetchone()

    if client is None:
        return web.json_response(
            {"erreur": "Clé invalide ou désactivée"},
            status=401,
        )

    guild_id, channel_id = client

    # Lecture des données de l'annonce
    try:
        data = await request.json()
    except Exception:
        return web.json_response(
            {"erreur": "JSON invalide"},
            status=400,
        )

    if not isinstance(data, dict):
        return web.json_response(
            {"erreur": "Format JSON invalide"},
            status=400,
        )

    lien = data.get("lien", "")
    titre = data.get("titre", "Annonce Vinted")
    marque = data.get("marque", "Non précisée")
    prix = data.get("prix")
    taille = data.get("taille", "Non précisée")
    etat = data.get("etat", "Non précisé")
    image = data.get("image")

    vendeur = data.get("vendeur", "Non précisé")
    note = data.get("note", "Non disponible")
    avis = data.get("avis", "Non disponible")

    # Vérification du lien
    if (
        not isinstance(lien, str)
        or not lien.startswith("https://")
    ):
        return web.json_response(
            {"erreur": "Lien invalide"},
            status=400,
        )

    # Vérification du prix
    try:
        prix = float(prix)

        if prix <= 0:
            raise ValueError

    except (TypeError, ValueError):
        return web.json_response(
            {"erreur": "Prix invalide"},
            status=400,
        )

    # Prix TTC estimé
    prix_estime = prix * COEFFICIENT_ESTIMATION

    prix_affiche = (
        f"{prix:.2f} € | ≈ {prix_estime:.2f} € "
        "(TTC estimé)"
    ).replace(".", ",")

    # Recherche du serveur Discord
    bot = request.app["discord_bot"]
    guild = bot.get_guild(int(guild_id))

    if guild is None:
        return web.json_response(
            {"erreur": "Serveur Discord introuvable"},
            status=503,
        )

    # Classement par marque
    nom_salon = trouver_salon(marque)

    # Recherche du salon
    channel = discord.utils.get(
        guild.text_channels,
        name=nom_salon,
    )

    if channel is None:
        return web.json_response(
            {"erreur": f"Salon #{nom_salon} introuvable"},
            status=503,
        )

    # Création de l'annonce Discord
    embed = discord.Embed(
        title=str(titre)[:256],
        url=lien,
        color=discord.Color.green(),
    )

    embed.add_field(
        name="🏷️ Marque",
        value=str(marque)[:1024],
        inline=False,
    )

    embed.add_field(
        name="📏 Taille",
        value=str(taille)[:1024],
        inline=False,
    )

    embed.add_field(
        name="💎 État",
        value=str(etat)[:1024],
        inline=False,
    )

    embed.add_field(
        name="💰 Prix",
        value=prix_affiche,
        inline=False,
    )

    if vendeur != "Non précisé":
        embed.add_field(
            name="👤 Vendeur",
            value=str(vendeur)[:1024],
            inline=True,
        )

    if note != "Non disponible":
        embed.add_field(
            name="⭐ Note",
            value=str(note)[:1024],
            inline=True,
        )

    if avis != "Non disponible":
        embed.add_field(
            name="💬 Avis",
            value=str(avis)[:1024],
            inline=True,
        )

    # Photo de l'annonce
    if isinstance(image, str) and image.startswith("https://"):
        embed.set_image(url=image)

    # Heure française
    heure_publication = datetime.now(
        ZoneInfo("Europe/Paris")
    ).strftime("%H:%M")

    embed.set_footer(
        text=(
            "Vinted Bot® | Alertes & analyse des annonces"
            f" • {heure_publication}"
        )
    )

    # Envoi vers Discord
    await channel.send(embed=embed)

    return web.json_response(
        {
            "ok": True,
            "prix_affiche": prix,
            "prix_estime": round(prix_estime, 2),
        }
    )


async def demarrer_reception(bot):
    app = web.Application(
        client_max_size=1024 * 1024
    )

    app["discord_bot"] = bot

    app.router.add_post(
        "/annonce",
        recevoir_annonce,
    )

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.getenv("PORT", "8080"))

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        port,
    )

    await site.start()

    print(
        f"Serveur de réception démarré sur le port {port}"
    )

    return runner

