import os
import discord
from discord.ext import commands
from discord.ui import View, Button

# Intents wymagane do zarządzania członkami i odczytu wiadomości
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ID kanału i roli
CHANNEL_ID = 1373258480382771270  # ← ZMIEŃ NA SWÓJ KANAŁ
ROLE_ID = 1373275307150278686     # ← ZMIEŃ NA SWOJĄ ROLĘ

# Persistent View z przyciskiem
class VerificationView(View):
    def __init__(self, role_id):
        super().__init__(timeout=None)
        self.role_id = role_id

    @discord.ui.button(
        label="Zweryfikuj się",
        style=discord.ButtonStyle.green,
        custom_id="verify_button"  # wymagane dla persistent View
    )
    async def verify_button(self, button: Button, interaction: discord.Interaction):
        print(f"Kliknął: {interaction.user} ({interaction.user.id})")
        role = discord.utils.get(interaction.guild.roles, id=self.role_id)

        if role is None:
            await interaction.response.send_message("❌ Nie znaleziono roli.", ephemeral=True)
            return

        try:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("✅ Zostałeś zweryfikowany!", ephemeral=True)
            print(f"Rola '{role.name}' nadana użytkownikowi {interaction.user}.")
        except discord.Forbidden:
            await interaction.response.send_message("🚫 Brak uprawnień do nadania roli.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message("❗ Błąd: " + str(e), ephemeral=True)

# Event: Bot się uruchomił
@bot.event
async def on_ready():
    print(f'Zalogowano jako {bot.user} (ID: {bot.user.id})')

    # Zarejestruj View globalnie (musi być persistent!)
    bot.add_view(VerificationView(ROLE_ID))

    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print("❌ Nie znaleziono kanału.")
        return

    # Usuń stare wiadomości bota
    async for message in channel.history(limit=100):
        if message.author == bot.user:
            await message.delete()

    # Wyślij nową wiadomość z przyciskiem
    await channel.send(
        "Kliknij przycisk poniżej, aby się zweryfikować:",
        view=VerificationView(ROLE_ID)
    )
    print("✅ Wysłano wiadomość weryfikacyjną.")

# Uruchom bota
bot.run(os.getenv("DISCORD_TOKEN"))
