import discord
from discord.ext import commands

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()  # Synchronizuje komendy z Discordem
    print(f'Zalogowano jako {bot.user} (ID: {bot.user.id})')

@bot.tree.command(name="ping", description="Sprawdź opóźnienie bota")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"Pong! 🏓 Opóźnienie: {latency} ms")

bot.run("TWÓJ_TOKEN_BOTA")
