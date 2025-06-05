import os
import discord
from discord.ext import commands
from discord.ui import Button, View

# Ustawienia bota
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# ID kanału i roli
CHANNEL_ID = 1373258480382771270
ROLE_ID = 1373275307150278686
GUILD_ID = 1373253103176122399

# Zmienna do przechowywania ostatniej wysłanej wiadomości
last_message = None

class VerifyButton(Button):
    def __init__(self):
        super().__init__(label="Zweryfikuj", style=discord.ButtonStyle.green)

    async def callback(self, interaction: discord.Interaction):
        role = interaction.guild.get_role(ROLE_ID)
        if role:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(f"Rola {role.name} została przypisana!", ephemeral=True)
        else:
            await interaction.response.send_message("Nie znaleziono roli.", ephemeral=True)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'Zalogowano jako {bot.user} (ID: {bot.user.id})')

@bot.command()
async def send_verification(ctx):
    """Wysyła wiadomość z przyciskiem weryfikacyjnym do określonego kanału."""
    global last_message

    # Pobieranie kanału
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        await ctx.send("Nie znaleziono kanału.")
        return

    # Usuwanie poprzedniej wiadomości, jeśli istnieje
    if last_message:
        await last_message.delete()

    # Tworzenie widoku z przyciskiem
    view = View()
    view.add_item(VerifyButton())

    # Wysyłanie nowej wiadomości
    last_message = await channel.send("Kliknij przycisk, aby się zweryfikować:", view=view)

bot.run(os.getenv("DISCORD_TOKEN"))
