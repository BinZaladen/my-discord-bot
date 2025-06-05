import os
import discord
from discord.ext import commands
from discord.ui import View, Button

# Intents wymagane do zarządzania członkami i czytania wiadomości
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

# Prefix komend i bot
bot = commands.Bot(command_prefix="!", intents=intents)

# Ustawienia serwera
CHANNEL_ID = 1373258480382771270  # ID kanału, gdzie wysłać przycisk
ROLE_ID = 1373275307150278686     # ID roli do nadania

# Klasa widoku z przyciskiem
class VerificationView(View):
    def __init__(self, role_id):
        super().__init__(timeout=None)
        self.role_id = role_id

    @discord.ui.button(label="Zweryfikuj się", style=discord.ButtonStyle.green)
    async def verify_button(self, button: Button, interaction: discord.Interaction):
        print(f"Kliknął: {interaction.user} ({interaction.user.id})")
        role = discord.utils.get(interaction.guild.roles, id=self.role_id)

        if role is None:
            await interaction.response.send_message("Nie znaleziono roli weryfikacyjnej.", ephemeral=True)
            print("Błąd: Rola nie istnieje.")
            return

        try:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("✅ Zostałeś zweryfikowany!", ephemeral=True)
            print(f"Rola '{role.name}' nadana użytkownikowi {interaction.user}.")
        except discord.Forbidden:
            await interaction.response.send_message("🚫 Brak uprawnień do nadania roli.", ephemeral=True)
            print("Błąd: Brak uprawnień.")
        except Exception as e:
            await interaction.response.send_message(f"❗ Wystąpił błąd: {e}", ephemeral=True)
            print(f"Błąd przy nadawaniu roli: {e}")

# Event: Po starcie bota
@bot.event
async def on_ready():
    print(f'Zalogowano jako {bot.user} (ID: {bot.user.id})')

    # Rejestrujemy widok, by działał globalnie (ważne!)
    bot.add_view(VerificationView(ROLE_ID))

    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print("❌ Nie znaleziono kanału.")
        return

    # Usuwanie starych wiadomości bota
    async for message in channel.history(limit=100):
        if message.author == bot.user:
            await message.delete()

    # Wysyłanie nowej wiadomości z przyciskiem
    await channel.send(
        "Kliknij przycisk poniżej, aby się zweryfikować:",
        view=VerificationView(ROLE_ID)
    )
    print("✅ Wysłano wiadomość weryfikacyjną.")

# Start bota
bot.run(os.getenv("DISCORD_TOKEN"))
