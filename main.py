import os
import discord
from discord.ext import commands
from discord.ui import View, Button
from discord import ButtonStyle

# Ustawienia bota
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ID kanału, na którym bot ma wysyłać wiadomości
CHANNEL_ID = 1373258480382771270
# ID roli do nadania po weryfikacji
ROLE_ID = 1373275307150278686

# Funkcja do wysyłania wiadomości z przyciskiem
async def send_verification_message():
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        # Usuwanie poprzednich wiadomości
        async for message in channel.history(limit=100):
            await message.delete()

        # Tworzenie przycisku
        button = Button(label="Zweryfikuj się", style=ButtonStyle.green)
        view = View()
        view.add_item(button)

        # Wysyłanie wiadomości z przyciskiem
        await channel.send("Kliknij przycisk, aby się zweryfikować:", view=view)

        # Funkcja obsługująca kliknięcie przycisku
        async def button_callback(interaction: discord.Interaction):
            role = discord.utils.get(interaction.guild.roles, id=ROLE_ID)
            if role:
                await interaction.user.add_roles(role)
                await interaction.response.send_message("Zostałeś zweryfikowany!", ephemeral=True)
            else:
                await interaction.response.send_message("Nie znaleziono roli do nadania.", ephemeral=True)

        # Rejestracja funkcji obsługującej kliknięcie przycisku
        button.callback = button_callback

# Komenda do wysyłania wiadomości z przyciskiem
@bot.command()
async def start_verification(ctx):
    await send_verification_message()

# Uruchomienie bota
token = os.getenv("DISCORD_TOKEN")
if token:
    bot.run(token)
else:
    print("Brak tokena bota.")
