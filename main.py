import os
import discord
from discord.ext import commands
from discord.ui import View, Button, Select, Modal, TextInput

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- KONFIGURACJA (ID kanałów, kategorii, ról) ---
CHANNEL_VERIFICATION_ID = 1373258480382771270
ROLE_VERIFIED_ID = 1373275307150278686

CHANNEL_TICKET_START_ID = 1373305137228939416  # kanał z przyciskiem do tworzenia ticketu
CATEGORY_TICKET_ID = 1373277957446959135       # kategoria ticketów

ROLE_TICKET_CLOSE = [1373275898375176232, 1379538984031752212]

CHANNEL_SUMMARY_ID = 1374479815914291240        # kanał podsumowań

# --- Dane do wyborów ---
DATA = {
    "Serwer 1": {
        "Tryb A": ["item1", "item2", "kasa"],
        "Tryb B": ["item3", "item4", "kasa"],
    },
    "Serwer 2": {
        "Tryb C": ["item5", "item6", "kasa"],
        "Tryb D": ["item7", "item8", "kasa"],
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

# --- TICKET START VIEW ---

class TicketStartView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Utwórz ticket", style=discord.ButtonStyle.blurple, custom_id="create_ticket_button")
    async def create_ticket(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        category = guild.get_channel(CATEGORY_TICKET_ID)
        if category is None or not isinstance(category, discord.CategoryChannel):
            await interaction.response.send_message("❌ Nie znaleziono kategorii ticketów.", ephemeral=True)
            return

        # Sprawdź czy użytkownik ma już ticket
        existing_channel = discord.utils.get(guild.channels, name=f"ticket-{interaction.user.id}")
        if existing_channel:
            await interaction.response.send_message(f"❗ Masz już otwarty ticket: {existing_channel.mention}", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        for role_id in ROLE_TICKET_CLOSE:
            role = guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        ticket_channel = await guild.create_text_channel(
            name=f"ticket-{interaction.user.id}",
            category=category,
            overwrites=overwrites,
            reason=f"Ticket utworzony przez {interaction.user}"
        )

        await interaction.response.send_message(f"✅ Ticket utworzony: {ticket_channel.mention}", ephemeral=True)

        # Wyślij menu wyboru do ticketu
        await ticket_channel.send(
            f"Witaj {interaction.user.mention}! Wybierz, czy chcesz coś sprzedać lub kupić.",
            view=SellBuySelectView(interaction.user)
        )

        # Dodaj przycisk zamknięcia ticketu
        await ticket_channel.send(
            "Kliknij poniżej, aby zamknąć ticket, gdy skończysz:",
            view=CloseTicketView(interaction.user.id)
        )

# --- SELL OR BUY SELECT ---

class SellBuySelectView(View):
    def __init__(self, user):
        super().__init__(timeout=None)
        self.user = user

    @discord.ui.select(
        placeholder="Wybierz Sprzedaj lub Kup",
        options=[
            discord.SelectOption(label="Sprzedaj", description="Sprzedaj coś", value="sprzedaj"),
            discord.SelectOption(label="Kup", description="Kup coś", value="kup"),
        ],
        custom_id="sellbuy_select"
    )
    async def select_callback(self, select: discord.ui.Select, interaction: discord.Interaction):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ Nie możesz korzystać z czyjegoś ticketa.", ephemeral=True)
            return

        await interaction.response.defer()
        action = select.values[0]
        view = ServerSelectView(self.user, action)
        await interaction.message.edit(content=f"Wybrałeś: **{action.capitalize()}**. Teraz wybierz serwer.", view=view)

# --- SERVER SELECT ---

class ServerSelectView(View):
    def __init__(self, user, action):
        super().__init__(timeout=None)
        self.user = user
        self.action = action

        options = [discord.SelectOption(label=s) for s in DATA.keys()]
        self.select = discord.ui.Select(
            placeholder="Wybierz serwer",
            options=options,
            custom_id="server_select"
        )
        self.select.callback = self.server_select_callback
        self.add_item(self.select)

    async def server_select_callback(self, select: discord.ui.Select, interaction: discord.Interaction):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ Nie możesz korzystać z czyjegoś ticketa.", ephemeral=True)
            return

        server = select.values[0]
        view = ModeSelectView(self.user, self.action, server)
        await interaction.response.edit_message(content=f"Wybrałeś serwer: **{server}**. Teraz wybierz tryb.", view=view)

# --- MODE SELECT ---

class ModeSelectView(View):
    def __init__(self, user, action, server):
        super().__init__(timeout=None)
        self.user = user
        self.action = action
        self.server = server

        modes = DATA[server].keys()
        options = [discord.SelectOption(label=m) for m in modes]
        self.select = discord.ui.Select(
            placeholder="Wybierz tryb",
            options=options,
            custom_id="mode_select"
        )
        self.select.callback = self.mode_select_callback
        self.add_item(self.select)

    async def mode_select_callback(self, select: discord.ui.Select, interaction: discord.Interaction):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ Nie możesz korzystać z czyjegoś ticketa.", ephemeral=True)
            return

        mode = select.values[0]
        view = ItemSelectView(self.user, self.action, self.server, mode)
        await interaction.response.edit_message(content=f"Wybrałeś tryb: **{mode}**. Teraz wybierz itemy.", view=view)

# --- ITEM SELECT ---

class ItemSelectView(View):
    def __init__(self, user, action, server, mode):
        super().__init__(timeout=None)
        self.user = user
        self.action = action
        self.server = server
        self.mode = mode

        self.selected_items = {}  # item -> ilość (str)

        items = DATA[server][mode]
        options = [discord.SelectOption(label=i) for i in items]
        self.select = discord.ui.Select(
            placeholder="Wybierz item do dodania",
            options=options,
            custom_id="item_select"
        )
        self.select.callback = self.item_select_callback
        self.add_item(self.select)

        # Przycisk zakończenia wyboru
        self.add_item(Button(label="Zakończ wybór", style=discord.ButtonStyle.green, custom_id="finish_selection", row=1))

    async def item_select_callback(self, select: discord.ui.Select, interaction: discord.Interaction):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ Nie możesz korzystać z czyjegoś ticketa.", ephemeral=True)
            return

        item = select.values[0]

        if item == "kasa":
            modal = AmountModal(self, item, is_money=True)
        else:
            modal = AmountModal(self, item, is_money=False)

        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Zakończ wybór", style=discord.ButtonStyle.green, custom_id="finish_selection")
    async def finish_selection_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ Nie możesz korzystać z czyjegoś ticketa.", ephemeral=True)
            return
        if not self.selected_items:
            await interaction.response.send_message("❗ Nie wybrałeś żadnych itemów.", ephemeral=True)
            return

        embed = discord.Embed(title="📋 Podsumowanie ticketa", color=discord.Color.blue())
        embed.add_field(name="Użytkownik", value=self.user.mention, inline=False)
        embed.add_field(name="Akcja", value=self.action.capitalize(), inline=True)
        embed.add_field(name="Serwer", value=self.server, inline=True)
        embed.add_field(name="Tryb", value=self.mode, inline=True)

        items_str = ""
        for it, qty in self.selected_items.items():
            items_str += f"• **{it}**: {qty}\n"
        embed.add_field(name="Wybrane itemy", value=items_str, inline=False)
        embed.set_footer(text="Ktoś wkrótce odpowie na Twojego ticketa.")

        # Wyślij podsumowanie do kanału ticketu
        await interaction.response.edit_message(content=None, embed=embed, view=None)

        # Wyślij podsumowanie na kanał podsumowań
        summary_channel = interaction.guild.get_channel(CHANNEL_SUMMARY_ID)
        if summary_channel:
            await summary_channel.send(embed=embed)

# --- MODAL DO WPISANIA ILOŚCI / KWOTY ---

class AmountModal(Modal):
    def __init__(self, parent_view: ItemSelectView, item_name: str, is_money: bool):
        super().__init__(title=f"Wpisz ilość dla '{item_name}'")
        self.parent_view = parent_view
        self.item_name = item_name
        self.is_money = is_money

        self.amount_input = TextInput(
            label="Ilość" if not is_money else "Kwota (np. 100 lub 100k)",
            style=discord.TextStyle.short,
            placeholder="Wpisz ilość lub kwotę",
            required=True,
            max_length=20
        )
        self.add_item(self.amount_input)

    async def on_submit(self, interaction: discord.Interaction):
        raw = self.amount_input.value.strip().lower()

        if not self.validate_amount(raw):
            await interaction.response.send_message("❌ Niepoprawny format ilości/kwoty. Podaj liczbę, np. 10 lub 100k.", ephemeral=True)
            return

        # Zapamiętaj w rodzicu
        self.parent_view.selected_items[self.item_name] = raw

        await interaction.response.send_message(f"✅ Dodano **{self.item_name}**: {raw}", ephemeral=True)

    def validate_amount(self, val: str) -> bool:
        if val.endswith("k"):
            num_part = val[:-1]
            return num_part.isdigit()
        return val.isdigit()

# --- PRZYCISK ZAMKNIĘCIA TICKETA ---

class CloseTicketView(View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id

    @discord.ui.button(label="Zamknij ticket", style=discord.ButtonStyle.red, custom_id="close_ticket_button")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id and not any(role.id in ROLE_TICKET_CLOSE for role in interaction.user.roles):
            await interaction.response.send_message("❌ Nie masz uprawnień, aby zamknąć ten ticket.", ephemeral=True)
            return

        await interaction.response.send_message("🗑️ Zamykam ticket...", ephemeral=True)
        await interaction.channel.delete(reason=f"Ticket zamknięty przez {interaction.user}")

# --- WYDARZENIA BOT ---

@bot.event
async def on_ready():
    print(f"Zalogowano jako {bot.user}!")

    # Wysyłanie wiadomości z przyciskiem w kanałach startowych (weryfikacja i ticket)
    guild = bot.guilds[0]  # jeśli bot jest na 1 serwerze, można inaczej pobrać

    # Weryfikacja
    channel_ver = guild.get_channel(CHANNEL_VERIFICATION_ID)
    if channel_ver:
        async for message in channel_ver.history(limit=50):
            if message.author == bot.user:
                await message.delete()
        view = VerificationView(ROLE_VERIFIED_ID)
        await channel_ver.send("Kliknij przycisk, aby się zweryfikować:", view=view)

    # Ticket start
    channel_ticket_start = guild.get_channel(CHANNEL_TICKET_START_ID)
    if channel_ticket_start:
        async for message in channel_ticket_start.history(limit=50):
            if message.author == bot.user:
                await message.delete()
        view = TicketStartView()
        await channel_ticket_start.send("Kliknij przycisk, aby utworzyć ticket:", view=view)

bot.run(os.getenv("DISCORD_TOKEN"))
