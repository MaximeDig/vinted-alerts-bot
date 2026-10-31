
import os
import sqlite3
import secrets
import hashlib
from typing import Optional

import discord
from discord.ext import commands
from discord import app_commands

from reception import demarrer_reception


# =====================================
# CONFIGURATION
# =====================================

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("La variable DISCORD_TOKEN est manquante.")

DB_PATH = "vinted_alerts.db"
SEUIL = 50
SALON_ANALYSE = "🌍︲prix-a-analyser"


# =====================================
# BASE DE DONNEES
# =====================================

db = sqlite3.connect(DB_PATH, check_same_thread=False)

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

db.execute("""
CREATE TABLE IF NOT EXISTS clients (
    guild_id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,
    channel_id TEXT,
    actif INTEGER DEFAULT 1
)
""")

colonnes = 
{
    ligne[1]
    for ligne in db.execute("PRAGMA table_info(clients)").fetchall()
}

if "token_hash" not in colonnes:
    db.execute("ALTER TABLE clients ADD COLUMN token_hash TEXT")

db.commit()


# =====================================
# CONFIGURATION DISCORD
# =====================================

intents = discord.Intents.default()
intents.guilds = True
intents.reactions = True

bot = commands.Bot(command_prefix="!", intents=intents)


# =====================================
# MARQUES ET SALONS
# =====================================

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

PAYS_AUTORISES = [
    "france",
    "belgique",
    "luxembourg",
    "allemagne",
    "espagne",
    "italie",
    "portugal",
]

SALONS = {
    "STREETWEAR": [
        "🇺🇸︲nike",
        "🇩🇪︲adidas",
        "🇺🇸︲stussy",
        "🇺🇸︲supreme",
        "🇺🇸︲carhartt",
    ],
    "PREMIUM": [
        "🇺🇸︲ralph-lauren",
        "🇫🇷︲lacoste",
        "🇺🇸︲tommy-hilfiger",
        "🇩🇪︲hugo-boss",
    ],
    "LUXE": [
        "🇮🇹︲stone-island",
        "🇬🇧︲burberry",
        "🇫🇷︲dior",
        "🇮🇹︲gucci",
        "🇮🇹︲prada",
    ],
    "VINTAGE-OUTDOOR": [
        "🇺🇸︲levis",
        "🇺🇸︲dickies",
        "🇺🇸︲patagonia",
        "🇺🇸︲the-north-face",
        "🇨🇦︲arcteryx",
    ],
    "SNEAKERS": [
        "🇺🇸︲nike-jordan",
        "🇺🇸︲new-balance",
        "🇯🇵︲asics",
        "🇫🇷︲salomon",
    ],
}


async def trouver_salon(guild: discord.Guild, nom: str):
    return discord.utils.get(guild.text_channels, name=nom)


# =====================================
# DEMARRAGE
# =====================================

commandes_synchronisees = False
reception_runner = None


@bot.event
async def on_ready():
    global commandes_synchronisees, reception_runner

    if not commandes_synchronisees:
        await bot.tree.sync()
        commandes_synchronisees = True
        print("Commandes Discord synchronisées.")

    if reception_runner is None:
        reception_runner = await demarrer_reception(bot)

    print(f"Vinted Bot connecté : {bot.user}")


# =====================================
# CONFIGURER UN CLIENT
# =====================================

@bot.tree.command(
    name="configurer_client",
    description="Configurer le salon de réception des annonces",
)
@app_commands.describe(salon="Salon dans lequel recevoir les annonces")
@app_commands.checks.has_permissions(manage_guild=True)
async def configurer_client(
    interaction: discord.Interaction,
    salon: discord.TextChannel,
):
    if interaction.guild is None:
        await interaction.response.send_message(
            "Cette commande doit être utilisée sur un serveur.",
            ephemeral=True,
        )
        return

    db.execute(
        """
        INSERT INTO clients (guild_id, owner_id, channel_id, actif)
        VALUES (?, ?, ?, 1)
        ON CONFLICT(guild_id) DO UPDATE SET
            owner_id = excluded.owner_id,
            channel_id = excluded.channel_id,
            actif = 1
        """,
        (
            str(interaction.guild.id),
            str(interaction.user.id),
            str(salon.id),
        ),
    )
    db.commit()

    await interaction.response.send_message(
        f"Configuration enregistrée ! Les annonces seront envoyées dans {salon.mention}.",
        ephemeral=True,
    )
    # =====================================
# GENERER UNE CLE D'ACCES
# =====================================

@bot.tree.command(
    name="generer_cle",
    description="Générer une clé d'accès personnelle",
)
@app_commands.checks.has_permissions(manage_guild=True)
async def generer_cle(interaction: discord.Interaction):
    if interaction.guild is None:
        await interaction.response.send_message(
            "Utilise cette commande sur un serveur.",
            ephemeral=True,
        )
        return

    cle = secrets.token_urlsafe(32)
    empreinte = hashlib.sha256(cle.encode("utf-8")).hexdigest()

    db.execute(
        """
        INSERT INTO clients (guild_id, owner_id, token_hash, actif)
        VALUES (?, ?, ?, 1)
        ON CONFLICT(guild_id) DO UPDATE SET
            owner_id = excluded.owner_id,
            token_hash = excluded.token_hash,
            actif = 1
        """,
        (
            str(interaction.guild.id),
            str(interaction.user.id),
            empreinte,
        ),
    )
    db.commit()

    await interaction.response.send_message(
        f"Voici ta nouvelle clé personnelle :\n`{cle}`\n"
        "Conserve-la en lieu sûr. Elle ne sera plus affichée.",
        ephemeral=True,
    )


# =====================================
# INSTALLER LES CATEGORIES ET SALONS
# =====================================

@bot.tree.command(
    name="installer",
    description="Créer les catégories et salons Vinted",
)
@app_commands.checks.has_permissions(manage_channels=True)
async def installer(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    guild = interaction.guild
    if guild is None:
        await interaction.followup.send(
            "Commande à utiliser sur un serveur.",
            ephemeral=True,
        )
        return

    for categorie_nom, salons in SALONS.items():
        categorie = discord.utils.get(
            guild.categories,
            name=categorie_nom,
        )

        if categorie is None:
            categorie = await guild.create_category(categorie_nom)

        for salon_nom in salons:
            salon = await trouver_salon(guild, salon_nom)

            if salon is None:
                await guild.create_text_channel(
                    salon_nom,
                    category=categorie,
                )

    analyse = discord.utils.get(guild.categories, name="ANALYSE")
    if analyse is None:
        analyse = await guild.create_category("ANALYSE")

    if await trouver_salon(guild, SALON_ANALYSE) is None:
        await guild.create_text_channel(
            SALON_ANALYSE,
            category=analyse,
        )

    await interaction.followup.send(
        "Installation terminée ! Les salons sont prêts.",
        ephemeral=True,
    )


# =====================================
# TESTER ET CLASSER UNE ANNONCE
# =====================================

@bot.tree.command(
    name="tester_annonce",
    description="Tester le classement et l'affichage d'une annonce",
)
@app_commands.describe(
    marque="Marque de l'article",
    prix="Prix affiché en euros",
    reference="Prix de référence estimé en euros",
    pays="Pays de l'annonce",
    lien="Lien HTTP ou HTTPS de l'annonce",
    taille="Taille de l'article",
    etat="État de l'article",
    prix_ttc="Prix total TTC facultatif",
)
async def tester_annonce(
    interaction: discord.Interaction,
    marque: str,
    prix: float,
    reference: float,
    pays: str,
    lien: str,
    taille: str = "Non précisée",
    etat: str = "Non précisé",
    prix_ttc: Optional[float] = None,
):
    if interaction.guild is None:
        await interaction.response.send_message(
            "Utilise cette commande sur ton serveur.",
            ephemeral=True,
        )
        return

    if prix <= 0 or reference <= 0:
        await interaction.response.send_message(
            "Les prix doivent être supérieurs à zéro.",
            ephemeral=True,
        )
        return

    if prix_ttc is not None and prix_ttc <= 0:
        await interaction.response.send_message(
            "Le prix TTC doit être supérieur à zéro.",
            ephemeral=True,
        )
        return

    if not lien.startswith(("https://", "http://")):
        await interaction.response.send_message(
            "Le lien doit commencer par http:// ou https://.",
            ephemeral=True,
        )
        return

    nom_marque = marque.lower().strip()
    salon_marque = MARQUES.get(nom_marque, SALON_ANALYSE)

    pays_normalise = pays.lower().strip()
    if pays_normalise not in PAYS_AUTORISES:
        await interaction.response.send_message(
            "Pays non autorisé dans la configuration.",
            ephemeral=True,
        )
        return

    deja_present = db.execute(
        "SELECT message_id FROM annonces WHERE lien = ?",
        (lien,),
    ).fetchone()

    if deja_present:
        await interaction.response.send_message(
            "Cette annonce a déjà été enregistrée.",
            ephemeral=True,
        )
        return

    ecart = ((prix - reference) / reference) * 100

    if abs(ecart) >= SEUIL:
        destination = SALON_ANALYSE
        if ecart < 0:
            statut = "🔻 PRIX BIEN EN DESSOUS DE LA RÉFÉRENCE"
        else:
            statut = "🔺 PRIX BIEN AU-DESSUS DE LA RÉFÉRENCE"
    else:
        destination = salon_marque
        statut = "✅ PRIX COHÉRENT"
            channel = await trouver_salon(interaction.guild, destination)
    if channel is None:
        await interaction.response.send_message(
            f"Le salon #{destination} est introuvable. Lance /installer.",
            ephemeral=True,
        )
        return

    if prix_ttc is not None:
        prix_affiche = f"{prix:.2f} € | ≈ {prix_ttc:.2f} € (TTC)"
    else:
        prix_affiche = f"{prix:.2f} €"

    embed = discord.Embed(
        title=f"VINTED ALERT - {marque.upper()}",
        description=f"**{statut}**",
        url=lien,
        color=(
            discord.Color.orange()
            if abs(ecart) >= SEUIL
            else discord.Color.green()
        ),
    )

    embed.add_field(name="🏷️ Marque", value=marque, inline=False)
    embed.add_field(name="📏 Taille", value=taille, inline=False)
    embed.add_field(name="💎 État", value=etat, inline=False)
    embed.add_field(name="💰 Prix", value=prix_affiche, inline=False)

    embed.set_footer(
        text="Vinted Bot® | Alertes & analyse des annonces"
    )

    await interaction.response.send_message(
        f"Annonce classée dans #{destination}.",
        ephemeral=True,
    )

    message = await channel.send(embed=embed)

    db.execute(
        """
        INSERT INTO annonces
        (message_id, marque, prix, reference, ecart, pays, lien)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(message.id),
            marque,
            prix,
            reference,
            ecart,
            pays,
            lien,
        ),
    )
    db.commit()

    if destination == SALON_ANALYSE:
        await message.add_reaction("✅")
        await message.add_reaction("❌")


# =====================================
# ENREGISTRER LES REACTIONS
# =====================================

@bot.event
async def on_raw_reaction_add(payload):
    if bot.user and payload.user_id == bot.user.id:
        return

    emoji = str(payload.emoji)
    if emoji not in ("✅", "❌"):
        return

    annonce = db.execute(
        "SELECT message_id FROM annonces WHERE message_id = ?",
        (str(payload.message_id),),
    ).fetchone()

    if annonce is None:
        return

    db.execute(
        """
        INSERT OR REPLACE INTO evaluations
        (message_id, user_id, reaction)
        VALUES (?, ?, ?)
        """,
        (
            str(payload.message_id),
            str(payload.user_id),
            emoji,
        ),
    )
    db.commit()

    print(f"Évaluation enregistrée : {emoji}")


# =====================================
# LANCEMENT
# =====================================

bot.run(TOKEN)
    
