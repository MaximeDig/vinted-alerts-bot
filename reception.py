
import sqlite3
import hashlib
import os
import discord
from aiohttp import web

DB_PATH = "vinted_alerts.db"


# Noms des salons : ils doivent correspondre à bot.py
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
    "salomon": "🇫🇷︲salomon"
}

SALON_ANALYSE = "🌍︲prix-a-analyser"


async def recevoir_annonce(request):
    authorization = request.headers.get("Authorization", "")

    if not authorization.startswith("Bearer "):
        return web.json_response(
            {"erreur": "Clé manquante"}, status=401
        )

    cle = authorization.replace("Bearer ", "", 1)

    empreinte = hashlib.sha256(
        cle.encode("utf-8")
    ).hexdigest()

    with sqlite3.connect(DB_PATH) as db:
        client = db.execute("""
            SELECT guild_id, channel_id
            FROM clients
            WHERE token_hash = ? AND actif = 1
        """, (empreinte,)).fetchone()

    if client is None:
        return web.json_response(
            {"erreur": "Clé invalide ou désactivée"}, status=401
        )

    guild_id, channel_id = client

    try:
        data = await request.json()
    except Exception:
        return web.json_response(
            {"erreur": "JSON invalide"}, status=400
        )

    if not isinstance(data, dict):
        return web.json_response(
            {"erreur": "Format JSON invalide"}, status=400
        )

    lien = data.get("lien", "")
    titre = data.get("titre", "Annonce Vinted")
    marque = data.get("marque", "Non précisée")
    prix = data.get("prix", "Non précisé")
    image = data.get("image")
    vendeur = data.get("vendeur", "Non précisé")
    note = data.get("note", "Non disponible")
    avis = data.get("avis", "Non disponible")

    if not isinstance(lien, str) or not lien.startswith("https://"):
        return web.json_response(
            {"erreur": "Lien invalide"}, status=400
        )

    bot = request.app["discord_bot"]
    guild = bot.get_guild(int(guild_id))

    if guild is None:
        return web.json_response(
            {"erreur": "Serveur Discord introuvable"}, status=503
        )

    nom_marque = str(marque).lower().strip()
    nom_salon = MARQUES.get(nom_marque, SALON_ANALYSE)

    channel = discord.utils.get(
        guild.text_channels,
        name=nom_salon
    )

    if channel is None:
        return web.json_response(
            {"erreur": f"Salon #{nom_salon} introuvable"},
            status=503
        )

    embed = discord.Embed(
        title=str(titre)[:256],
        url=lien,
        description=(
            f"**Marque :** {marque}\n"
            f"**Prix :** {prix}\n"
            f"**Vendeur :** {vendeur}\n"
            f"**Note :** {note}\n"
            f"**Avis :** {avis}"
        ),
        color=discord.Color.green()
    )

    if isinstance(image, str) and image.startswith("https://"):
        embed.set_image(url=image)

    embed.set_footer(
        text="Vinted Bot® | Alertes & analyse des annonces"
    )

    await channel.send(embed=embed)

    return web.json_response({"ok": True})


async def demarrer_reception(bot):
    app = web.Application(client_max_size=1024 * 1024)
    app["discord_bot"] = bot
    app.router.add_post("/annonce", recevoir_annonce)

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.getenv("PORT", "8080"))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    print(f"Serveur de réception démarré sur le port {port}")
    return runner
