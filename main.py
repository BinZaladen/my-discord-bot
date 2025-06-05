import os
import discord
from discord.ext import commands
from discord.ui import View, Button

intents = discord.Intents.default()
intents.members = True  # Wymagane do zarządzania rolami
bot = commands.Bot(command_prefix="!", intents=intents)

# ID kanału i roli
CHANNEL_ID = 1373258480382771270
ROLE_ID = 1373275307150278686

class VerificationView(View):
    def __init__(self, user, role_id):
        super().__init__(timeout=None)
        self.user = user
        self.role_id = role_id

    @discord.ui.button(label="Zweryfikuj się", style=discord.ButtonStyle.green)
    async def verify_button(self, button: Button, interaction: discord.Interaction):
        role = discord.utils.get(self.user.guild.roles, id=self.role_id)
        if role:
            await self.user.add_roles(role)
            await interaction.response.send_message("Zostałeś zweryfikowany!", ephemeral=True)
            self.stop()
        else:
            await interaction.response.send_message("Nie znaleziono roli weryfikacyjnej.", ephemeral=True)

@bot.event
async def on_ready():
    print(f'Zalogowano jako {bot.user} (ID: {bot.user.id})')

@bot.command()
async def send_verification(ctx):
    """Wysyła wiadomość z przyciskiem weryfikacyjnym na określony kanał."""
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        # Usuwamy poprzednie wiadomości bota w tym kanale
        async for message in channel.history(limit=100):
            if message.author == bot.user:
                await message.delete()

        # Wysyłamy nową wiadomość z przyciskiem
        view = VerificationView(ctx.author, ROLE_ID)
        await channel.send(
            f"{ctx.author.mention}, kliknij przycisk poniżej, aby się zweryfikować.",
            view=view
        )
    else:
        await ctx.send("Nie znaleziono kanału weryfikacyjnego.")

bot.run(os.getenv("DISCORD_TOKEN"))
