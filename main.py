import os
import discord
from discord.ext import commands
from discord.ui import View, Button

intents = discord.Intents.default()
intents.members = True
intents.message_content = True  # ważne, żeby bot czytał komendy (jeśli potrzebne)

bot = commands.Bot(command_prefix="!", intents=intents)

# ID kanału i roli — wpisz swoje ID
CHANNEL_ID = 1373258480382771270
ROLE_ID = 1373275307150278686

class VerificationView(View):
    def __init__(self, role_id):
        super().__init__(timeout=None)
        self.role_id = role_id

    @discord.ui.button(label="Zweryfikuj się", style=discord.ButtonStyle.green)
    async def verify_button(self, button: Button, interaction: discord.Interaction):
        role = discord.utils.get(interaction.guild.roles, id=self.role_id)
        if role:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("Zostałeś zweryfikowany!", ephemeral=True)
            self.stop()
        else:
            await interaction.response.send_message("Nie znaleziono roli weryfikacyjnej.", ephemeral=True)

@bot.event
async def on_ready():
    print(f'Zalogowano jako {bot.user} (ID: {bot.user.id})')
    await send_verification_automatic()

async def send_verification_automatic():
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        # Usuwamy poprzednie wiadomości bota na kanale
        async for message in channel.history(limit=100):
            if message.author == bot.user:
                await message.delete()

        # Wysyłamy nową wiadomość z przyciskiem weryfikacyjnym
        view = VerificationView(ROLE_ID)
        await channel.send(
            "Kliknij przycisk poniżej, aby się zweryfikować.",
            view=view
        )
        print("Wysłano wiadomość weryfikacyjną")
    else:
        print("Nie znaleziono kanału do weryfikacji")

# Komenda send_verification nadal możesz zostawić, jeśli chcesz ją używać manualnie
@bot.command()
async def send_verification(ctx):
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        async for message in channel.history(limit=100):
            if message.author == bot.user:
                await message.delete()

        view = VerificationView(ROLE_ID)
        await channel.send(
            f"{ctx.author.mention}, kliknij przycisk poniżej, aby się zweryfikować.",
            view=view
        )
        await ctx.send("Wiadomość weryfikacyjna została wysłana.")
    else:
        await ctx.send("Nie znaleziono kanału weryfikacyjnego.")

bot.run(os.getenv("DISCORD_TOKEN"))
