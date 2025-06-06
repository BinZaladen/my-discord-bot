import os
import discord
from discord.ext import commands
from discord.ui import View, Button, Select, Modal, TextInput

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# --- KONFIGURACJA ---
CHANNEL_VERIFICATION_ID = 1373258480382771270
CHANNEL_TICKET_ID = 1373305137228939416
CATEGORY_TICKET_ID = 1373277957446959135
SUMMARY_CHANNEL_ID = 1374479815914291240

ROLE_VERIFIED_ID = 1373275307150278686
ROLE_SUPPORT_IDS = [1373275898375176232, 1379538984031752212]

# --- STRUKTURA DANYCH ---
STRUCTURE = {
    "Serwer 1": {
        "Tryb A": ["Item 1", "Item 2", "Kasa"],
        "Tryb B": ["Item 3", "Item 4", "Kasa"]
    },
    "Serwer 2": {
        "Tryb C": ["Item 5", "Item 6", "Kasa"],
        "Tryb D": ["Item 7", "Item 8", "Kasa"]
    }
}

# --- WERYFIKACJA ---
class VerificationView(View):
    def __init__(self, role_id):
        super().__init__(timeout=None)
        self.role_id = role_id

    @discord.ui.button(label="Zweryfikuj się", style=discord.ButtonStyle.green, custom_id="verify_button")
    async def verify_button(self, interaction: discord.Interaction, button: Button):
        role = interaction.guild.get_role(self.role_id)
        if role:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("✅ Zostałeś zweryfikowany!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Nie znaleziono roli.", ephemeral=True)

# --- MODAL NA ITEMY ---
class ItemModal(Modal, title="Podaj przedmioty i ilości"):
    def __init__(self, context_data):
        super().__init__()
        self.context_data = context_data
        self.items_input = TextInput(label="Przedmioty (np. Item1 (2), Kasa (50k))", placeholder="Wpisz przedmioty", style=discord.TextStyle.paragraph)
        self.add_item(self.items_input)

    async def on_submit(self, interaction: discord.Interaction):
        self.context_data["items"] = self.items_input.value
        await interaction.response.send_message("✅ Dziękujemy! Ticket został zarejestrowany.", ephemeral=True)
        await send_summary(interaction, self.context_data)

# --- WIDOKI DYNAMICZNE ---
class FinalStep(View):
    def __init__(self, context_data):
        super().__init__(timeout=300)
        self.context_data = context_data

    @discord.ui.button(label="Podaj itemy i ilości", style=discord.ButtonStyle.primary)
    async def open_modal(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(ItemModal(self.context_data))

class ModeSelect(Select):
    def __init__(self, context_data):
        self.context_data = context_data
        options = [discord.SelectOption(label=mode) for mode in STRUCTURE[context_data["server"]]]
        super().__init__(placeholder="Wybierz tryb", options=options, custom_id="select_mode")

    async def callback(self, interaction: discord.Interaction):
        self.context_data["mode"] = self.values[0]
        await interaction.response.edit_message(content="📦 Teraz podaj itemy i ilości:", view=FinalStep(self.context_data))

class ServerSelect(Select):
    def __init__(self, context_data):
        self.context_data = context_data
        options = [discord.SelectOption(label=server) for server in STRUCTURE]
        super().__init__(placeholder="Wybierz serwer", options=options, custom_id="select_server")

    async def callback(self, interaction: discord.Interaction):
        self.context_data["server"] = self.values[0]
        await interaction.response.edit_message(content="🎮 Wybierz tryb:", view=View().add_item(ModeSelect(self.context_data)))

class TypeSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Sprzedaj"),
            discord.SelectOption(label="Kup")
        ]
        super().__init__(placeholder="Wybierz typ transakcji", options=options, custom_id="select_type")
        self.context_data = {}

    async def callback(self, interaction: discord.Interaction):
        self.context_data["type"] = self.values[0]
        self.context_data["user"] = interaction.user
        await interaction.response.edit_message(content="🌍 Wybierz serwer:", view=View().add_item(ServerSelect(self.context_data)))

class TicketCloseView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Zamknij ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        if any(role.id in ROLE_SUPPORT_IDS for role in interaction.user.roles):
            await interaction.channel.delete()
        else:
            await interaction.response.send_message("❌ Nie masz uprawnień do zamknięcia ticketu.", ephemeral=True)

# --- POCZĄTKOWY PRZYCISK ---
class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎫 Utwórz ticket", style=discord.ButtonStyle.blurple, custom_id="create_ticket_button")
    async def create_ticket(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        category = guild.get_channel(CATEGORY_TICKET_ID)
        existing_channel = discord.utils.get(guild.channels, name=f"ticket-{interaction.user.id}")

        if existing_channel:
            await interaction.response.send_message(f"❗ Masz już otwarty ticket: {existing_channel.mention}", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            **{guild.get_role(rid): discord.PermissionOverwrite(read_messages=True, send_messages=True) for rid in ROLE_SUPPORT_IDS}
        }

        channel = await guild.create_text_channel(
            name=f"ticket-{interaction.user.id}",
            category=category,
            overwrites=overwrites
        )

        await interaction.response.send_message(f"✅ Ticket utworzony: {channel.mention}", ephemeral=True)
        await channel.send(f"{interaction.user.mention}, wybierz opcję poniżej, aby rozpocząć:", view=View().add_item(TypeSelect()))
        await channel.send(view=TicketCloseView())

# --- PODSUMOWANIE ---
async def send_summary(interaction: discord.Interaction, context_data: dict):
    embed = discord.Embed(
        title="📋 Nowy ticket",
        color=discord.Color.blue()
    )
    embed.add_field(name="Użytkownik", value=f"{context_data['user'].mention}", inline=False)
    embed.add_field(name="Typ", value=context_data['type'], inline=True)
    embed.add_field(name="Serwer", value=context_data['server'], inline=True)
    embed.add_field(name="Tryb", value=context_data['mode'], inline=True)
    embed.add_field(name="Itemy / Kasa", value=context_data['items'], inline=False)
    embed.set_footer(text="Ktoś z zespołu wkrótce się z Tobą skontaktuje.")

    await interaction.channel.send(embed=embed)
    await bot.get_channel(SUMMARY_CHANNEL_ID).send(embed=embed)

# --- ON READY ---
@bot.event
async def on_ready():
    print(f"Zalogowano jako {bot.user} (ID: {bot.user.id})")
    bot.add_view(VerificationView(ROLE_VERIFIED_ID))
    bot.add_view(TicketView())

    # Weryfikacja
    channel_ver = bot.get_channel(CHANNEL_VERIFICATION_ID)
    if channel_ver:
        async for message in channel_ver.history(limit=50):
            if message.author == bot.user:
                await message.delete()
        await channel_ver.send(
            embed=discord.Embed(title="🔒 Weryfikacja", description="Kliknij przycisk poniżej, aby się zweryfikować.", color=discord.Color.green()),
            view=VerificationView(ROLE_VERIFIED_ID)
        )

    # Ticket
    channel_ticket = bot.get_channel(CHANNEL_TICKET_ID)
    if channel_ticket:
        async for message in channel_ticket.history(limit=50):
            if message.author == bot.user:
                await message.delete()
        await channel_ticket.send(
            embed=discord.Embed(title="🎫 System Ticketów", description="Kliknij przycisk poniżej, aby utworzyć ticket.", color=discord.Color.blurple()),
            view=TicketView()
        )

# --- START ---
bot.run(os.getenv("DISCORD_TOKEN"))
