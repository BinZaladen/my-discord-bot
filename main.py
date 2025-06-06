import os
import discord
from discord.ext import commands
from discord.ui import View, Button, Select, Modal, TextInput

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ID kanałów i ról
CHANNEL_VERIFICATION_ID = 1373258480382771270
ROLE_VERIFIED_ID = 1373275307150278686

CHANNEL_TICKET_ID = 1373305137228939416
CATEGORY_TICKET_ID = 1373277957446959135
SUMMARY_CHANNEL_ID = 1374479815914291240

ROLES_CAN_CLOSE = [1373275898375176232, 1379538984031752212]

# Konfiguracja dynamiczna
TICKET_CONFIG = {
    "Serwer 1": {
        "Tryb 1": ["Item1", "Item2", "Kasa"],
        "Tryb 2": ["Item3", "Item4", "Kasa"]
    },
    "Serwer 2": {
        "Tryb 1": ["ItemA", "ItemB", "Kasa"],
        "Tryb 2": ["ItemC", "ItemD", "Kasa"]
    },
    "Serwer 3": {
        "Tryb 1": ["ItemX", "ItemY", "Kasa"],
        "Tryb 2": ["ItemZ", "ItemW", "Kasa"]
    },
    "Serwer 4": {
        "Tryb 1": ["ItemQ", "ItemR", "Kasa"],
        "Tryb 2": ["ItemS", "ItemT", "Kasa"]
    }
}

# WERYFIKACJA
class VerificationView(View):
    def __init__(self, role_id):
        super().__init__(timeout=None)
        self.role_id = role_id

    @discord.ui.button(label="Zweryfikuj się", style=discord.ButtonStyle.green, custom_id="verify_button")
    async def verify_button(self, interaction: discord.Interaction, button: Button):
        role = discord.utils.get(interaction.guild.roles, id=self.role_id)
        if not role:
            await interaction.response.send_message("❌ Nie znaleziono roli.", ephemeral=True)
            return
        try:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("✅ Zostałeś zweryfikowany!", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("🚫 Bot nie ma uprawnień do nadania roli.", ephemeral=True)

# TICKETY
class TicketFlow(View):
    def __init__(self, author: discord.Member):
        super().__init__(timeout=300)
        self.author = author
        self.data = {
            "typ": None,
            "serwer": None,
            "tryb": None,
            "itemy": []
        }
        self.serwer_select = None
        self.tryb_select = None
        self.item_select = None
        self.add_item(Select(placeholder="Wybierz: Sprzedajesz czy Kupujesz?", options=[
            discord.SelectOption(label="Sprzedaj", value="sprzedaj"),
            discord.SelectOption(label="Kup", value="kup")
        ], custom_id="select_typ"))

    async def interaction_check(self, interaction):
        return interaction.user.id == self.author.id

    @discord.ui.button(label="Zamknij ticket", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        if any(role.id in ROLES_CAN_CLOSE for role in interaction.user.roles):
            await interaction.channel.delete()
        else:
            await interaction.response.send_message("⛔ Nie masz uprawnień do zamknięcia tego ticketa.", ephemeral=True)

    async def on_select_option(self, interaction: discord.Interaction):
        selected = interaction.data["values"][0]
        self.data["typ"] = selected.capitalize()
        self.clear_items()

        # Serwery
        self.serwer_select = Select(placeholder="Wybierz serwer", options=[
            discord.SelectOption(label=s) for s in TICKET_CONFIG.keys()
        ], custom_id="select_serwer")
        self.add_item(self.serwer_select)
        await interaction.response.edit_message(content="🔄 Wybierz serwer:", view=self)

    async def process_next(self, interaction: discord.Interaction):
        cid = interaction.data["custom_id"]
        value = interaction.data["values"][0]

        if cid == "select_serwer":
            self.data["serwer"] = value
            self.clear_items()

            self.tryb_select = Select(placeholder="Wybierz tryb", options=[
                discord.SelectOption(label=t) for t in TICKET_CONFIG[value].keys()
            ], custom_id="select_tryb")
            self.add_item(self.tryb_select)
            await interaction.response.edit_message(content="🔄 Wybierz tryb:", view=self)

        elif cid == "select_tryb":
            self.data["tryb"] = value
            self.clear_items()

            self.item_select = Select(placeholder="Wybierz itemy", options=[
                discord.SelectOption(label=i) for i in TICKET_CONFIG[self.data["serwer"]][value]
            ], custom_id="select_item", min_values=1, max_values=5)
            self.add_item(self.item_select)
            await interaction.response.edit_message(content="🔄 Wybierz itemy (max 5):", view=self)

        elif cid == "select_item":
            selected_items = interaction.data["values"]
            self.data["itemy"] = []

            modal = Modal(title="Wpisz ilości")
            for i, item in enumerate(selected_items):
                modal.add_item(TextInput(label=f"{item} - ilość", custom_id=f"item_{item}", required=True))
            await interaction.response.send_modal(modal)

    async def on_timeout(self):
        try:
            await self.message.edit(content="⏳ Czas na odpowiedź minął.", view=None)
        except:
            pass

    async def on_modal_submit(self, interaction: discord.Interaction):
        for k, v in interaction.data["components"][0].items():
            label = k.replace("item_", "")
            self.data["itemy"].append(f"{label} ({v})")

        await self.send_summary(interaction)
        await interaction.response.edit_message(content="✅ Podsumowanie wysłane!", view=None)

    async def send_summary(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📦 Nowy Ticket",
            color=discord.Color.blurple()
        )
        embed.add_field(name="Użytkownik", value=f"{self.author.mention}", inline=False)
        embed.add_field(name="Typ transakcji", value=self.data["typ"], inline=True)
        embed.add_field(name="Serwer", value=self.data["serwer"], inline=True)
        embed.add_field(name="Tryb", value=self.data["tryb"], inline=True)
        embed.add_field(name="Wybrane", value="\n".join(self.data["itemy"]), inline=False)
        embed.set_footer(text="Czekaj na odpowiedź ze strony administracji.")

        await interaction.channel.send(embed=embed)

        summary_channel = bot.get_channel(SUMMARY_CHANNEL_ID)
        if summary_channel:
            await summary_channel.send(embed=embed)

class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Utwórz ticket", style=discord.ButtonStyle.blurple, custom_id="create_ticket_button")
    async def create_ticket(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        category = guild.get_channel(CATEGORY_TICKET_ID)

        existing = discord.utils.get(guild.channels, name=f"ticket-{interaction.user.id}")
        if existing:
            await interaction.response.send_message(f"Masz już ticket: {existing.mention}", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        ticket_channel = await guild.create_text_channel(
            name=f"ticket-{interaction.user.id}",
            category=category,
            overwrites=overwrites
        )
        await interaction.response.send_message(f"✅ Ticket utworzony: {ticket_channel.mention}", ephemeral=True)
        view = TicketFlow(interaction.user)
        view.message = await ticket_channel.send(f"{interaction.user.mention}, rozpocznij konfigurację:", view=view)

@bot.event
async def on_ready():
    print(f'Zalogowano jako {bot.user} (ID: {bot.user.id})')

    bot.add_view(VerificationView(ROLE_VERIFIED_ID))
    bot.add_view(TicketView())

    channel_ver = bot.get_channel(CHANNEL_VERIFICATION_ID)
    if channel_ver:
        async for msg in channel_ver.history(limit=50):
            if msg.author == bot.user:
                await msg.delete()
        embed = discord.Embed(title="🔒 Weryfikacja", description="Kliknij, aby uzyskać dostęp do serwera.", color=discord.Color.green())
        await channel_ver.send(embed=embed, view=VerificationView(ROLE_VERIFIED_ID))

    channel_ticket = bot.get_channel(CHANNEL_TICKET_ID)
    if channel_ticket:
        async for msg in channel_ticket.history(limit=50):
            if msg.author == bot.user:
                await msg.delete()
        embed = discord.Embed(title="🎫 Ticket", description="Kliknij, aby utworzyć ticket.", color=discord.Color.blurple())
        await channel_ticket.send(embed=embed, view=TicketView())

bot.run(os.getenv("DISCORD_TOKEN"))
