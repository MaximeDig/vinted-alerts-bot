import sqlite3
import hashlib
import os
import discord
from aiohttp import web

API_SECRET = os.getenv("RECEPTION_SECRET")

if not API_SECRET:
    raise RuntimeError("RECEPTION_SECRET est manquante.")

async def recevoir_annonce(request):
    secret = request.headers.get("Authorization", "")

    if secret != f"Bearer {API_SECRET}":
        return web.json_response(
            {"erreur": "Accès refusé"}, status=401
        )

    try:
        data = await request.json()
    except Exception:
        return web.json_response(
            {"erreur": "JSON invalide"}, status=400
        )

    lien = data.get("lien", "")
    titre = data.get("titre", "Annonce Vinted")
    marque = data.get("marque", "Non précisée")
    prix = data.get("prix", "Non précisé")
    image = data.get("image")
    vendeur = data.get("vendeur", "Non précisé")
    note = data.get("note", "Non disponible")
    avis = data.get("avis", "Non disponible")

    if not lien.startswith("https://"):
        return web.json_response(
            {"erreur": "Lien invalide"}, status=400
        )

    bot = request.app["discord_bot"]
    guild_id = int(os.getenv("DISCORD_GUILD_ID", "0"))
    guild = bot.get_guild(guild_id)

    if guild is None:
        return web.json_response(
            {"erreur": "Serveur Discord introuvable"}, status=503
        )

    embed = discord.Embed(
        title=titre[:256],
        url=lien,
        description=f"**Marque :** {marque}\n**Prix :** {prix}\n"
                    f"**Vendeur :** {vendeur}\n"
                    f"**Note :** {note}\n**Avis :** {avis}",
        color=discord.Color.green()
    )

    if isinstance(image, str) and image.startswith("https://"):
        embed.set_image(url=image)

    embed.set_footer(
        text="Vinted Bot® | Alertes & analyse des annonces"
    )

    channel = discord.utils.get(
        guild.text_channels, name="prix-a-analyser"
    )

    if channel is None:
        return web.json_response(
            {"erreur": "Salon introuvable"}, status=503
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
