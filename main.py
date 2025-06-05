import os
import discord
from discord.ext import commands
from discord.ui import View, Button

# Intents potrzebne do nadawania ról i obsługi wiadomości
intents = discord.Intents.default()
intents.members = True
intents.message_content = True  # Wymagane do odczytu treści wiadomości

bot = commands.Bot(command_prefix="!", intents=intents)

# Stałe ID kanału i roli – ZMIEŃ NA SWOJE
CHANNEL_ID = 1373258480382771270
ROLE_ID = 1373275307150278686

# Persistent View z poprawnym callbackiem
class VerificationView(View):
    def __init__(self, role_id):
        super().__init__(timeout=None)
        self.role_id = role_id

    @discord.ui.button(
        label="Zweryfikuj się",
        style=discord.ButtonStyle.green,
        custom_id="verify_button"  # wymagane dla persistent view
    )
    async def verify_button(self, interaction: discord.Interaction, button: Button):
        print(f"Kliknął: {interaction.user} ({interaction.user.id})")
        role = discord.utils.get(interaction.guild.roles, id=self.role_id)

        if not role:
            await interaction.response.send_message("❌ Nie znaleziono roli.", ephemeral=True)
            return

        try:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("✅ Zostałeś zweryfikowany!", ephemeral=True)
            print(f"Nadano rolę '{role.name}' użytkownikowi {interaction.user}.")
        except discord.Forbidden:
            await interaction.response.send_message("🚫 Bot nie ma uprawnień do nadania roli.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❗ Wystąpił błąd: {e}", ephemeral=True)

# Event po zalogowaniu bota
@bot.event
async def on_ready():
    print(f'Zalogowano jako {bot.user} (ID: {bot.user.id})')

    # Zarejestruj persistent view, aby działał po restarcie
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

# Uruchomienie bota z tokenem z ENV
bot.run(os.getenv("DISCORD_TOKEN"))
