import os
import discord
from discord.ext import commands
from discord.ui import Button, View

# Inicjalizacja bota z odpowiednimi uprawnieniami
intents = discord.Intents.default()
intents.members = True  # Wymagane do zarządzania rolami
bot = commands.Bot(command_prefix="!", intents=intents)

# ID kanału i roli
CHANNEL_ID = 1373258480382771270
ROLE_ID = 1373275307150278686

# Usuwanie poprzednich wiadomości bota w kanale
async def clear_previous_messages(channel):
    async for message in channel.history(limit=10):
        if message.author == bot.user:
            await message.delete()

# Komenda do wysyłania wiadomości z przyciskiem
@bot.command()
async def verify(ctx):
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        # Tworzenie przycisku
        button = Button(label="Zweryfikuj się", style=discord.ButtonStyle.green)

        # Definicja akcji po kliknięciu przycisku
        async def button_callback(interaction):
            member = interaction.user
            role = discord.utils.get(interaction.guild.roles, id=ROLE_ID)
            if role:
                await member.add_roles(role)
                await interaction.response.send_message("Zostałeś zweryfikowany!", ephemeral=True)
            else:
                await interaction.response.send_message("Nie znaleziono roli weryfikacyjnej.", ephemeral=True)

        # Przypisanie akcji do przycisku
        button.callback = button_callback

        # Tworzenie widoku z przyciskiem
        view = View()
        view.add_item(button)

        # Usuwanie poprzednich wiadomości bota
        await clear_previous_messages(channel)

        # Wysyłanie nowej wiadomości z przyciskiem
        await channel.send("Kliknij przycisk, aby się zweryfikować:", view=view)
    else:
        await ctx.send("Nie znaleziono kanału weryfikacyjnego.")

# Uruchomienie bota
token = os.getenv("DISCORD_TOKEN")
if token:
    bot.run(token)
else:
    print("Brak tokena bota.")
