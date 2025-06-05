import os
import discord
from discord.ext import commands
from discord.ui import View, Button

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

CHANNEL_ID = 1373258480382771270
ROLE_ID = 1373275307150278686

class VerificationView(View):
    def __init__(self, role_id):
        super().__init__(timeout=None)
        self.role_id = role_id

    @discord.ui.button(label="Zweryfikuj się", style=discord.ButtonStyle.green)
    async def verify_button(self, button: Button, interaction: discord.Interaction):
        print(f"Przycisk kliknięty przez {interaction.user} ({interaction.user.id})")
        role = discord.utils.get(interaction.guild.roles, id=self.role_id)
        if role is None:
            await interaction.response.send_message("Nie znaleziono roli weryfikacyjnej.", ephemeral=True)
            print("Nie znaleziono roli do nadania!")
            return

        try:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("Zostałeś zweryfikowany!", ephemeral=True)
            print(f"Dodano rolę {role.name} użytkownikowi {interaction.user}.")
            self.stop()
        except discord.Forbidden:
            await interaction.response.send_message(
                "Nie mam uprawnień, aby nadać Ci rolę.", ephemeral=True)
            print("Brak uprawnień do nadania roli!")
        except Exception as e:
            await interaction.response.send_message(
                f"Wystąpił błąd: {e}", ephemeral=True)
            print(f"Błąd przy dodawaniu roli: {e}")

@bot.event
async def on_ready():
    print(f'Zalogowano jako {bot.user} (ID: {bot.user.id})')
    channel = bot.get_channel(CHANNEL_ID)
    if channel is None:
        print("Nie znaleziono kanału.")
        return

    # Usuwamy stare wiadomości bota na kanale
    async for message in channel.history(limit=100):
        if message.author == bot.user:
            await message.delete()

    view = VerificationView(ROLE_ID)
    await channel.send("Kliknij przycisk, aby się zweryfikować.", view=view)
    print("Wiadomość weryfikacyjna wysłana.")

bot.run(os.getenv("DISCORD_TOKEN"))
