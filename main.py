import os
import discord
from discord.ext import commands
from discord.ui import View, Button

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ID kanału ticketów
TICKET_CHANNEL_ID = 1373305137228939416

# URL logo serwera (podmień na swój obrazek!)
SERVER_LOGO_URL = "https://twoja-domena.pl/sciezka/do/logo.png"

OFFERS = {
    1373266589310517338: (
        "<:elytra:1374797373406187580> Elytra — 12zł\n"
        "<:buty:1374796797222064230> Buty flasha — 5zł\n"
        "<:miecz:1374791139462352906> Miecz 6 — 3zł\n"
        "<:shulker:1374795916531335271> Shulker s2 — 7zł\n"
        "<:shulker:1374795916531335271> Shulker totemów — 6zł\n\n"
    ),
    1373267159576481842: (
        "💸 1mln$ — 18zł\n\n"
        "<:klata:1374793644246306866> Set 25 — 30zł\n"
        "<:miecz:1374791139462352906> Miecz 25 — 25zł\n"
        "<:kilof:1374795407493959751> Kilof 25 — 10zł\n"
    ),
    1373268875407396914: (
        "💵 4,5k$ — 1zł\n"
        "<:elytra:1374797373406187580> Elytra — 50zł\n"
        "<:ANA2:137479901735931494> Anarchiczny set 2 — 28zł\n"
        "<:klata:1374793644246306866> Anarchiczny set 1 — 9zł\n\n"
        "<:miecz:1374791139462352906> Anarchiczny miecz — 3zł\n"
        "🎉 Eventówki:\n"
        "<:MieczZjeczy:1375486003891929088> Zajęczy miecz — 65zł\n"
        "<:totem:1374788635211206757> Totem ułaskawienia — 630zł\n"
        "<:exalibur:1374785662191927416> Excalibur — 370zł"
    ),
    1373270295556788285: (
        "💵 50k$ — 1zł\n"
        "🎉 Eventówki:\n"
        "<:exalibur:1374785662191927416> Excalibur — 111zł\n"
        "<:totem:1374788635211206757> Totem ułaskawienia — 270zł\n"
        "<:sakiewka:1374799829120716892> Sakiewka — 50zł\n\n"
    ),
    1373273108093337640: (
        "💸 10mld$ — 2zł\n"
        "<:miecz:1374791139462352906> Miecz 35 — 65zł\n"
        "<:klata:1374793644246306866> Set 35 — 90zł\n\n"
    ),
    1374380939970347019: (
        "💵 15k$ — 1zł\n"
        "<:buda:1375488639496093828> Buda — 30zł\n"
        "<:loveswap:1375490111801790464> Love swap — 100zł\n"
        "<:klatameduzy:1375487632531918875> Klata meduzy — 140zł\n\n"
    ),
}

@bot.event
async def on_ready():
    print(f"Zalogowano jako {bot.user} (ID: {bot.user.id})")

    guild = None
    # Jeśli chcesz, żeby bot działał tylko na konkretnym serwerze,
    # możesz tu wpisać ID i pobrać obiekt guild, np:
    # guild = bot.get_guild(TWÓJ_GUILD_ID)

    for channel_id, offer_text in OFFERS.items():
        channel = bot.get_channel(channel_id)
        if not channel:
            print(f"Nie znaleziono kanału o ID {channel_id}")
            continue

        # Usuń stare wiadomości bota
        async for message in channel.history(limit=100):
            if message.author == bot.user:
                await message.delete()

        embed = discord.Embed(
            title="🛒 Oferta itemów na sprzedaż",
            description=offer_text,
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=SERVER_LOGO_URL)

        ticket_channel = bot.get_channel(TICKET_CHANNEL_ID)
        if ticket_channel:
            url = f"https://discord.com/channels/{ticket_channel.guild.id}/{TICKET_CHANNEL_ID}"
            view = View()
            view.add_item(Button(label="Utwórz ticket", style=discord.ButtonStyle.link, url=url))
        else:
            view = None

        await channel.send(embed=embed, view=view)

    print("Wszystkie oferty zostały wysłane.")

bot.run(os.getenv("DISCORD_TOKEN"))
