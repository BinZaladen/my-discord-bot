import os
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'Zalogowano jako {bot.user}')

@bot.tree.command(name="ping", description="Sprawdź opóźnienie bota")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"Pong! 🏓 Opóźnienie: {latency} ms")

bot.run(os.getenv("DISCORD_TOKEN"))
