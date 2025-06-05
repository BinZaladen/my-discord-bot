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
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Zweryfikuj się", style=discord.ButtonStyle.green, custom_id="verify_button")
    async def verify_button(self, button: Button, interaction: discord.Interaction):
        print(f"Kliknął: {interaction.user} ({interaction.user.id})")
        role = discord.utils.get(interaction.guild.roles, id=ROLE_ID)

        if role is None:
            await interaction.response.send_message("Nie znaleziono roli weryfikacyjnej.", ephemeral=True)
            return

        try:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("Zostałeś zweryfikowany!", ephemeral=True)
            print(f"Nadano rolę {role.name} użytkownikowi {interaction.user}.")
        except discord.Forbidden:
            await interaction.response.send_message("Nie mam uprawnień do nadania roli.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Wystąpił błąd: {e}", ephemeral=True)

@bot.event
async def on_ready():
    print(f'Zalogowano jako {bot.user} (ID: {bot.user.id})')
    # Rejestrujemy persistent view
    bot.add_view(VerificationView())

    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        async for msg in channel.history(limit=100):
            if msg.author == bot.user:
                await msg.delete()

        await channel.send("Kliknij przycisk, aby się zweryfikować:", view=VerificationView())
        print("Wiadomość weryfikacyjna wysłana.")
    else:
        print("Nie znaleziono kanału.")

bot.run(os.getenv("DISCORD_TOKEN"))
