import os
import discord
from discord.ext import commands
from discord.ui import View, Button, Select, Modal, TextInput
from dotenv import load_dotenv  # dodajemy do ładowania .env

load_dotenv()  # ładujemy zmienne z .env, jeśli jest

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ID kanałów i ról
CHANNEL_VERIFICATION_ID = 1373258480382771270
ROLE_VERIFIED_ID = 1373275307150278686

CHANNEL_TICKET_ID = 1373305137228939416
CATEGORY_TICKET_ID = 1373277957446959135

CHANNEL_SUMMARY_ID = 1374479815914291240  # kanał podsumowań

# Przykładowa konfiguracja serwerów → tryby → itemy (możesz łatwo edytować)
CONFIG = {
    "Serwer 1": {
        "Tryb A": ["Item 1", "Item 2", "Kasa"],
        "Tryb B": ["Item 3", "Item 4", "Kasa"]
    },
    "Serwer 2": {
        "Tryb C": ["Item 5", "Item 6", "Kasa"],
        "Tryb D": ["Item 7", "Item 8", "Kasa"]
    },
    "Serwer 3": {
        "Tryb E": ["Item 9", "Item 10", "Kasa"],
        "Tryb F": ["Item 11", "Item 12", "Kasa"]
    },
    "Serwer 4": {
        "Tryb G": ["Item 13", "Item 14", "Kasa"],
        "Tryb H": ["Item 15", "Item 16", "Kasa"]
    }
}

# --- WERYFIKACJA ---

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
        except Exception as e:
            await interaction.followup.send(f"❗ Wystąpił błąd: {e}", ephemeral=True)

# --- TICKETY i Menu wyborów ---

class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Utwórz ticket", style=discord.ButtonStyle.blurple, custom_id="create_ticket_button")
    async def create_ticket(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        category = guild.get_channel(CATEGORY_TICKET_ID)
        if category is None or not isinstance(category, discord.CategoryChannel):
            await interaction.response.send_message("❌ Nie znaleziono kategorii ticketów.", ephemeral=True)
            return

        existing_channel = discord.utils.get(guild.channels, name=f"ticket-{interaction.user.id}")
        if existing_channel:
            await interaction.response.send_message(f"❗ Masz już otwarty ticket: {existing_channel.mention}", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }

        ticket_channel = await guild.create_text_channel(
            name=f"ticket-{interaction.user.id}",
            category=category,
            overwrites=overwrites,
            reason=f"Ticket utworzony przez {interaction.user}"
        )

        await interaction.response.send_message(f"✅ Ticket utworzony: {ticket_channel.mention}", ephemeral=True)

        # Startujemy wybór: Sprzedaj/Kup
        await ticket_channel.send(
            f"Witaj {interaction.user.mention}! Wybierz co chcesz zrobić:",
            view=StartMenuView(interaction.user)
        )

class StartMenuView(View):
    def __init__(self, user):
        super().__init__(timeout=300)
        self.user = user

    @discord.ui.select(
        placeholder="Wybierz akcję...",
        options=[
            discord.SelectOption(label="Sprzedaj", description="Chcę coś sprzedać", value="sell"),
            discord.SelectOption(label="Kup", description="Chcę coś kupić", value="buy")
        ],
        custom_id="action_select"
    )
    async def select_action(self, select: discord.ui.Select, interaction: discord.Interaction):
        if interaction.user != self.user:
            await interaction.response.send_message("To nie jest twój ticket!", ephemeral=True)
            return

        self.action = select.values[0]

        # Przechodzimy do wyboru serwera
        await interaction.response.send_message(f"Wybrałeś: **{self.action.capitalize()}**. Teraz wybierz serwer:", ephemeral=True)
        await interaction.message.delete()

        await interaction.channel.send(
            f"**Wybierz serwer:**",
            view=ServerSelectView(self.user, self.action)
        )

class ServerSelectView(View):
    def __init__(self, user, action):
        super().__init__(timeout=300)
        self.user = user
        self.action = action
        self.servers = list(CONFIG.keys())

    @discord.ui.select(
        placeholder="Wybierz serwer",
        min_values=1,
        max_values=1,
        options=[discord.SelectOption(label=s) for s in list(CONFIG.keys())],
        custom_id="server_select"
    )
    async def select_server(self, select: discord.ui.Select, interaction: discord.Interaction):
        if interaction.user != self.user:
            await interaction.response.send_message("To nie jest twój ticket!", ephemeral=True)
            return

        self.server = select.values[0]
        await interaction.response.send_message(f"Wybrałeś serwer: **{self.server}**. Teraz wybierz tryb:", ephemeral=True)
        await interaction.message.delete()

        await interaction.channel.send(
            f"**Wybierz tryb:**",
            view=ModeSelectView(self.user, self.action, self.server)
        )

class ModeSelectView(View):
    def __init__(self, user, action, server):
        super().__init__(timeout=300)
        self.user = user
        self.action = action
        self.server = server
        self.modes = list(CONFIG[server].keys())

    @discord.ui.select(
        placeholder="Wybierz tryb",
        min_values=1,
        max_values=1,
        options=[discord.SelectOption(label=m) for m in list(CONFIG[self.server].keys())],
        custom_id="mode_select"
    )
    async def select_mode(self, select: discord.ui.Select, interaction: discord.Interaction):
        if interaction.user != self.user:
            await interaction.response.send_message("To nie jest twój ticket!", ephemeral=True)
            return

        self.mode = select.values[0]
        await interaction.response.send_message(f"Wybrałeś tryb: **{self.mode}**. Teraz wybierz itemy:", ephemeral=True)
        await interaction.message.delete()

        await interaction.channel.send(
            f"**Wybierz itemy:**",
            view=ItemSelectView(self.user, self.action, self.server, self.mode)
        )

class ItemSelectView(View):
    def __init__(self, user, action, server, mode):
        super().__init__(timeout=300)
        self.user = user
        self.action = action
        self.server = server
        self.mode = mode
        self.selected_items = {}  # item:str -> quantity:int

        options = []
        for item in CONFIG[server][mode]:
            options.append(discord.SelectOption(label=item, value=item))
        self.select = discord.ui.Select(
            placeholder="Wybierz item do dodania (możesz wielokrotnie)",
            options=options,
            min_values=1,
            max_values=1,
            custom_id="item_select"
        )
        self.select.callback = self.select_item_callback
        self.add_item(self.select)

    async def select_item_callback(self, interaction: discord.Interaction):
        if interaction.user != self.user:
            await interaction.response.send_message("To nie jest twój ticket!", ephemeral=True)
            return
        item = self.select.values[0]

        if item.lower() == "kasa":
            # jeśli kasa, wpisz ręcznie kwotę
            modal = CashInputModal(self.user, self)
            await interaction.response.send_modal(modal)
        else:
            # jeśli item, wybierz ilość (1-15)
            modal = QuantityInputModal(self.user, self, item)
            await interaction.response.send_modal(modal)

    async def add_item_with_quantity(self, item, quantity):
        if item in self.selected_items:
            self.selected_items[item] += quantity
        else:
            self.selected_items[item] = quantity

        # Wyślij podsumowanie do kanału
        await self.send_summary()

    async def send_summary(self):
        lines = []
        for item, qty in self.selected_items.items():
            lines.append(f"**{item}**: {qty}")
        description = "\n".join(lines)
        description += "\n\nKtoś wkrótce odpowie na ticket."

        embed = discord.Embed(
            title="Podsumowanie wyborów",
            description=description,
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Użytkownik: {self.user} | Serwer: {self.server} | Tryb: {self.mode} | Akcja: {self.action}")

        channel = self.user.guild.get_channel(self.user.channel.id) if hasattr(self.user, "channel") else None
        if channel is None:
            channel = interaction.channel

        # Wyślij do kanału ticketa
        await interaction.channel.send(embed=embed)

        # Wyślij też na kanał podsumowań
        summary_channel = self.user.guild.get_channel(CHANNEL_SUMMARY_ID)
        if summary_channel:
            await summary_channel.send(embed=embed)

class QuantityInputModal(Modal):
    def __init__(self, user, parent_view, item):
        super().__init__(title=f"Ilość dla {item}")
        self.user = user
        self.parent_view = parent_view
        self.item = item

        self.quantity = TextInput(label="Ilość (1-15)", placeholder="Wpisz ilość", min_length=1, max_length=2)
        self.add_item(self.quantity)

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user != self.user:
            await interaction.response.send_message("To nie jest twój ticket!", ephemeral=True)
            return

        try:
            qty = int(self.quantity.value)
            if qty < 1 or qty > 15:
                raise ValueError
        except ValueError:
            await interaction.response.send_message("Niepoprawna ilość, wpisz liczbę od 1 do 15.", ephemeral=True)
            return

        await self.parent_view.add_item_with_quantity(self.item, qty)
        await interaction.response.send_message(f"Dodano {self.item} x{qty}", ephemeral=True)

class CashInputModal(Modal):
    def __init__(self, user, parent_view):
        super().__init__(title="Kwota Kasa")
        self.user = user
        self.parent_view = parent_view

        self.amount = TextInput(label="Wpisz kwotę (np. 50k)", placeholder="Np. 50k, 100k, 1M")
        self.add_item(self.amount)

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user != self.user:
            await interaction.response.send_message("To nie jest twój ticket!", ephemeral=True)
            return

        kwota = self.amount.value.strip()
        if not kwota:
            await interaction.response.send_message("Wpisz kwotę.", ephemeral=True)
            return

        # Dodaj "Kasa" jako item z kwotą
        await self.parent_view.add_item_with_quantity("Kasa", kwota)
        await interaction.response.send_message(f"Dodano kwotę: {kwota}", ephemeral=True)

# --- Komendy i eventy ---

@bot.event
async def on_ready():
    print(f"Zalogowano jako {bot.user} (ID: {bot.user.id})")
    # Wysyłamy wiadomość weryfikacyjną, jeśli chcesz
    channel = bot.get_channel(CHANNEL_VERIFICATION_ID)
    if channel:
        await channel.send("Kliknij, aby się zweryfikować:", view=VerificationView(ROLE_VERIFIED_ID))

@bot.command()
@commands.has_permissions(administrator=True)
async def ticket(ctx):
    """Wysyła przycisk do tworzenia ticketów"""
    await ctx.send("Kliknij, aby utworzyć ticket:", view=TicketView())

# --- Uruchomienie ---

token = os.getenv("DISCORD_TOKEN")
if not token:
    print("❌ Nie znaleziono tokena bota. Ustaw zmienną środowiskową TOKEN.")
    exit(1)
