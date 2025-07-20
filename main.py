import os
import discord
from discord.ext import commands
from discord.ui import View, Button

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

class TicketButton(Button):
    def __init__(self):
        super().__init__(
            label="Kup wybrane itemy",
            style=discord.ButtonStyle.green,
            url="https://discord.com/channels/1373253103174604810/1373305137228939416"
        )

class OfertaView(View):
    def __init__(self):
        super().__init__()
        self.add_item(TicketButton())

@bot.event
async def on_ready():
    print(f"Zalogowano jako {bot.user.name}")
    
    logo_url = "https://cdn.discordapp.com/icons/1373253103174604810/4e244f4eaa6c447fd59cfeec3a6a8df6.webp"

    oferty = [
        {
            "channel_id": 1373266589310517338,
            "content": """
**🛒 Oferta itemów na sprzedaż:**
<:Elytra:1374797373406187580> **Elytra** — `12zł`
<:Buty:1374796797222064230> **Buty flasha** — `5zł`
<:Miecz:1374791139462352906> **Miecz 6** — `3zł`
<:Shulker:1374795916531335271> **Shulker s2** — `7zł`
<:Shulker:1374795916531335271> **Shulker totemów** — `6zł`
"""
        },
        {
            "channel_id": 1373267159576481842,
            "content": """
**🛒 Oferta itemów na sprzedaż:**
<:Klata:1374793644246306866> **Set 25** — `30zł`
<:Miecz:1374791139462352906> **Miecz 25** — `25zł`
<:Kilof:1374795407493959751> **Kilof 25** — `10zł`
💸 **1mln$** — `18zł`
"""
        },
        {
            "channel_id": 1373268875407396914,
            "content": """
**🛒 Oferta itemów na sprzedaż:**
💵 **4,5k$** — `1zł`
💸 **50k$** — `12zł`
💸 **550k$** — `130zł`
<:ANA2:137479901735931494> **Anarchiczny set 2** — `28zł`
<:Klata:1374793644246306866> **Anarchiczny set 1** — `9zł`

🎉 **Eventówki:**
<:Miecz:1374791139462352906> **Anarchiczny miecz** — `3zł`
<:MieczZajeczy:1375486003891929088> **Zajęczy miecz** — `65zł`
<:Totem:1374788635211206757> **Totem ułaskawienia** — `630zł`
<:Excalibur:1374785662191927416> **Excalibur** — `370zł`
"""
        },
        {
            "channel_id": 1373270295556788285,
            "content": """
**🛒 Oferta itemów na sprzedaż:**
💵 **50k$** — `1zł`
💸 **1mln$** — `33zł`

🎉 **Eventówki:**
<:Excalibur:1374785662191927416> **Excalibur** — `111zł`
<:Totem:1374788635211206757> **Totem ułaskawienia** — `270zł`
<:Sakiewka:1374799829120716892> **Sakiewka** — `50zł`
"""
        },
        {
            "channel_id": 1373273108093337640,
            "content": """
**🛒 Oferta itemów na sprzedaż:**
💸 **10mld$** — `2zł`
<:Miecz:1374791139462352906> **Miecz 35** — `65zł`
<:Klata:1374793644246306866> **Set 35** — `90zł`
"""
        },
        {
            "channel_id": 1374380939970347019,
            "content": """
**🛒 Oferta itemów na sprzedaż:**
💵 **15k$** — `1zł`
<:Buda:1375488639496093828> **Buda** — `30zł`
<:LoveSwap:1375490111801790464> **Love swap** — `100zł`
<:Klatameduzy:1375487632531918875> **Klata meduzy** — `140zł`
"""
        }
    ]

    for oferta in oferty:
        channel = bot.get_channel(oferta["channel_id"])
        if channel:
            embed = discord.Embed(
                description=oferta["content"].strip(),
                color=discord.Color.blue()
            )
            embed.set_thumbnail(url=logo_url)
            await channel.purge(limit=5)
            await channel.send(embed=embed, view=OfertaView())

bot.run(os.getenv("DISCORD_TOKEN"))
