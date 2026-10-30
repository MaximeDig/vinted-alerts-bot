
import os
import sqlite3
import discord
import secrets
import hashlib
from discord.ext import commands
from discord import app_commands
from reception import demarrer_reception

# Le token sera ajouté dans les variables d'environnement Railway.
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise ValueError("La variable DISCORD_TOKEN est manquante sur Railway.")

# Base de données
db = sqlite3.connect("vinted_alerts.db", check_same_thread=False)

db.execute("""
CREATE TABLE IF NOT EXISTS annonces (
    message_id TEXT PRIMARY KEY,
    marque TEXT,
    prix REAL,
    reference REAL,
    ecart REAL,
    pays TEXT,
    lien TEXT
)
""")

db.execute("""
CREATE TABLE IF NOT EXISTS evaluations (
    message_id TEXT,
    user_id TEXT,
    reaction TEXT,
    PRIMARY KEY (message_id, user_id)
)
""")

db.commit()

db.execute("""
CREATE TABLE IF NOT EXISTS clients (
    guild_id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    channel_id TEXT,
    actif INTEGER DEFAULT 1
)
""")
colonnes = {
    ligne[1]
    for ligne in db.execute(
        "PRAGMA table_info(clients)"
    ).fetchall()
}

if "token_hash" not in colonnes:
    db.execute(
        "ALTER TABLE clients ADD COLUMN token_hash TEXT"
    )
db.commit()

# Configuration Discord
intents = discord.Intents.default()
intents.guilds = True
intents.reactions = True

bot = commands.Bot(command_prefix="!", intents=intents)

SEUIL = 30

MARQUES = {
    "nike": "nike",
    "adidas": "adidas",
    "stussy": "stussy",
    "supreme": "supreme",
    "carhartt": "carhartt",
    "ralph lauren": "ralph-lauren",
    "lacoste": "lacoste",
    "tommy hilfiger": "tommy-hilfiger",
    "hugo boss": "hugo-boss",
    "stone island": "stone-island",
    "burberry": "burberry",
    "dior": "dior",
    "gucci": "gucci",
    "prada": "prada",
    "levis": "levis",
    "dickies": "dickies",
    "patagonia": "patagonia",
    "the north face": "the-north-face",
    "arcteryx": "arcteryx",
    "nike jordan": "nike-jordan",
    "new balance": "new-balance",
    "asics": "asics",
    "salomon": "salomon"
}

PAYS_AUTORISES = [
    "france",
    "belgique",
    "luxembourg",
    "allemagne",
    "espagne",
    "italie",
    "portugal"
]

SALONS = {
    "STREETWEAR": [
        "nike", "adidas", "stussy", "supreme", "carhartt"
    ],
    "PREMIUM": [
        "ralph-lauren", "lacoste", "tommy-hilfiger", "hugo-boss"
    ],
    "LUXE": [
        "stone-island", "burberry", "dior", "gucci", "prada"
    ],
    "VINTAGE-OUTDOOR": [
        "levis", "dickies", "patagonia", "the-north-face", "arcteryx"
    ],
    "SNEAKERS": [
        "nike-jordan", "new-balance", "asics", "salomon"
    ]
}


async def trouver_salon(guild, nom):
    return discord.utils.get(guild.text_channels, name=nom)


commandes_synchronisees = False
reception_runner = None

@bot.event
async def on_ready():
    global commandes_synchronisees, reception_runner

    if not commandes_synchronisees:
        guild_id = int(os.getenv("DISCORD_GUILD_ID"))
        guild = discord.Object(id=guild_id)

        # Supprimer les commandes propres au serveur
        bot.tree.clear_commands(guild=guild)
        await bot.tree.sync(guild=guild)

        # Synchroniser les commandes globales
        await bot.tree.sync()

        commandes_synchronisees = True
        print("Synchronisation terminée !")

    if reception_runner is None:
        reception_runner = await demarrer_reception(bot)

    print(f"Vinted Bot connecté : {bot.user}")

@bot.tree.command(
    name="configurer_client",
    description="Configurer le salon de réception des annonces"
)
@app_commands.describe(
    salon="Salon dans lequel recevoir les annonces"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def configurer_client(
    interaction: discord.Interaction,
    salon: discord.TextChannel
):
    if interaction.guild is None:
        await interaction.response.send_message(
            "Cette commande doit être utilisée sur un serveur.",
            ephemeral=True
        )
        return

    db.execute("""
        INSERT INTO clients (guild_id, owner_id, channel_id, actif)
        VALUES (?, ?, ?, 1)
        ON CONFLICT(guild_id) DO UPDATE SET
            owner_id = excluded.owner_id,
            channel_id = excluded.channel_id,
            actif = 1
    """, (
        str(interaction.guild.id),
        str(interaction.user.id),
        str(salon.id)
    ))

    db.commit()

    await interaction.response.send_message(
        f"Configuration enregistrée ! Les annonces seront envoyées dans {salon.mention}.",
        ephemeral=True
    )


@bot.tree.command(
    name="generer_cle",
    description="Générer une clé d'accès personnelle"
)
@app_commands.checks.has_permissions(manage_guild=True)
async def generer_cle(interaction: discord.Interaction):

    if interaction.guild is None:
        await interaction.response.send_message(
            "Utilise cette commande sur un serveur.",
            ephemeral=True
        )
        return

    cle = secrets.token_urlsafe(32)
    empreinte = hashlib.sha256(
        cle.encode("utf-8")
    ).hexdigest()

    db.execute("""
        INSERT INTO clients (
            guild_id, owner_id, token_hash, actif
        )
        VALUES (?, ?, ?, 1)
        ON CONFLICT(guild_id) DO UPDATE SET
            owner_id = excluded.owner_id,
            token_hash = excluded.token_hash,
            actif = 1
    """, (
        str(interaction.guild.id),
        str(interaction.user.id),
        empreinte
    ))

    db.commit()

    await interaction.response.send_message(
        f"Voici ta nouvelle clé personnelle :\n`{cle}`\n"
        "Conserve-la en lieu sûr. Elle ne sera plus affichée.",
        ephemeral=True
    )
@bot.tree.command(
    name="installer",
    description="Créer les catégories et salons Vinted"
)
@app_commands.checks.has_permissions(manage_channels=True)
async def installer(interaction: discord.Interaction):

    await interaction.response.defer(ephemeral=True)

    guild = interaction.guild

    if guild is None:
        await interaction.followup.send("Commande à utiliser sur un serveur.")
        return

    for categorie_nom, salons in SALONS.items():

        categorie = discord.utils.get(
            guild.categories, name=categorie_nom
        )

        if categorie is None:
            categorie = await guild.create_category(categorie_nom)

        for salon_nom in salons:

            salon = discord.utils.get(
                guild.text_channels, name=salon_nom
            )

            if salon is None:
                await guild.create_text_channel(
                    salon_nom,
                    category=categorie
                )

    analyse = discord.utils.get(
        guild.categories, name="ANALYSE"
    )

    if analyse is None:
        analyse = await guild.create_category("ANALYSE")

    if await trouver_salon(guild, "prix-a-analyser") is None:
        await guild.create_text_channel(
            "prix-a-analyser",
            category=analyse
        )

    await interaction.followup.send(
        "Installation terminée ! Les salons sont prêts."
    )


@bot.tree.command(
    name="tester_annonce",
    description="Tester le classement d'une annonce"
)
@app_commands.describe(
    marque="Marque de l'article",
    prix="Prix affiché en euros",
    reference="Prix de référence estimé en euros",
    pays="Pays de l'annonce",
    lien="Lien HTTP ou HTTPS de l'annonce"
)
async def tester_annonce(
    interaction: discord.Interaction,
    marque: str,
    prix: float,
    reference: float,
    pays: str,
    lien: str
):

    if interaction.guild is None:
        await interaction.response.send_message(
            "Utilise cette commande sur ton serveur.",
            ephemeral=True
        )
        return

    if prix <= 0 or reference <= 0:
        await interaction.response.send_message(
            "Les prix doivent être supérieurs à zéro.",
            ephemeral=True
        )
        return

    if not lien.startswith(("https://", "http://")):
        await interaction.response.send_message(
            "Le lien doit commencer par http:// ou https://.",
            ephemeral=True
        )
        return

    nom = marque.lower().strip()
    salon = MARQUES.get(nom)

    if salon is None:
        await interaction.response.send_message(
            "Marque non reconnue. Vérifie son nom.",
            ephemeral=True
        )
        return

    pays_normalise = pays.lower().strip()

    if pays_normalise not in PAYS_AUTORISES:
        await interaction.response.send_message(
            "Pays non autorisé dans la configuration.",
            ephemeral=True
        )
        return

    deja_present = db.execute(
        "SELECT message_id FROM annonces WHERE lien = ?",
        (lien,)
    ).fetchone()

    if deja_present:
        await interaction.response.send_message(
            "Cette annonce a déjà été enregistrée.",
            ephemeral=True
        )
        return

    ecart = ((prix - reference) / reference) * 100

    if abs(ecart) >= SEUIL:
        destination = "prix-a-analyser"

        if ecart < 0:
            statut = "🔻 PRIX BIEN EN DESSOUS DE LA RÉFÉRENCE"
        else:
            statut = "🔺 PRIX BIEN AU-DESSUS DE LA RÉFÉRENCE"

    else:
        destination = salon
        statut = "✅ PRIX COHÉRENT"

    channel = await trouver_salon(
        interaction.guild, destination
    )

    if channel is None:
        await interaction.response.send_message(
            f"Le salon #{destination} est introuvable. Lance /installer.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title=f"VINTED ALERT - {marque.upper()}",
        description=f"**{statut}**",
        url=lien,
        color=(
            discord.Color.orange()
            if abs(ecart) >= SEUIL
            else discord.Color.green()
        )
    )

    embed.add_field(
        name="Prix affiché",
        value=f"{prix:.2f} €",
        inline=True
    )

    embed.add_field(
        name="Référence estimée",
        value=f"{reference:.2f} €",
        inline=True
    )

    embed.add_field(
        name="Écart",
        value=f"{ecart:+.1f} %",
        inline=True
    )

    embed.add_field(name="Pays", value=pays, inline=True)
    embed.add_field(name="Marque", value=marque, inline=True)

    embed.set_footer(
        text="Vinted Bot® | Alertes & analyse des annonces"
    )

    await interaction.response.send_message(
        f"Annonce classée dans #{destination}.",
        ephemeral=True
    )

    message = await channel.send(embed=embed)

    db.execute(
        """
        INSERT INTO annonces
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(message.id),
            marque,
            prix,
            reference,
            ecart,
            pays,
            lien
        )
    )

    db.commit()

    if destination == "prix-a-analyser":
        await message.add_reaction("✅")
        await message.add_reaction("❌")


@bot.event
async def on_raw_reaction_add(payload):

    if bot.user and payload.user_id == bot.user.id:
        return

    emoji = str(payload.emoji)

    if emoji not in ["✅", "❌"]:
        return

    annonce = db.execute(
        "SELECT message_id FROM annonces WHERE message_id = ?",
        (str(payload.message_id),)
    ).fetchone()

    if annonce is None:
        return

    db.execute(
        """
        INSERT OR REPLACE INTO evaluations
        VALUES (?, ?, ?)
        """,
        (
            str(payload.message_id),
            str(payload.user_id),
            emoji
        )
    )

    db.commit()

    print(f"Évaluation enregistrée : {emoji}")


@bot.tree.command(
    name="tester_reception",
    description="Tester la réception d'une annonce fictive"
)
async def tester_reception(interaction: discord.Interaction):

    import aiohttp

    secret = os.getenv("RECEPTION_SECRET")
    port = os.getenv("PORT", "8080")

    url = f"http://127.0.0.1:{port}/annonce"

    annonce = {
        "titre": "Veste Nike vintage - TEST",
        "marque": "nike",
        "prix": "25 €",
        "vendeur": "vendeur_test",
        "note": "4,9/5",
        "avis": "127",
        "lien": "https://www.vinted.fr/"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            url,
            json=annonce,
            headers={"Authorization": f"Bearer {secret}"}
        ) as response:
            resultat = await response.text()

    await interaction.response.send_message(
        f"Résultat du test : {response.status}\n{resultat}",
        ephemeral=True
    )


bot.run(TOKEN)
