import os
import discord
from discord.ext import commands
from discord.ui import View, Button, Select, Modal, TextInput

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ID kanałów, kategorii i ról
CHANNEL_VERIFICATION_ID = 1373258480382771270
ROLE_VERIFIED_ID = 1373275307150278686

CHANNEL_TICKET_START_ID = 1373305137228939416  # kanał, gdzie jest przycisk "Utwórz ticket"
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

# --- Ticket Start View ---

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

        # Sprawdź, czy użytkownik już ma otwarty ticket (kanał z nazwą ticket-<user_id>)
        existing_channel = discord.utils.get(guild.channels, name=f"ticket-{interaction.user.id}")
        if existing_channel:
            await interaction.response.send_message(f"❗ Masz już otwarty ticket: {existing_channel.mention}", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        # Role do obsługi ticketów mają pełny dostęp
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

        # Wyślij menu startowe w kanale ticketu
        await ticket_channel.send(f"Witaj {interaction.user.mention}! Wybierz, czy chcesz coś sprzedać lub kupić.", view=SellBuySelectView(interaction.user))

# --- Sell or Buy Select ---

class SellBuySelectView(View):
    def __init__(self, user):
        super().__init__(timeout=300)
        self.user = user

    @discord.ui.select(
        placeholder="Wybierz Sprzedaj lub Kup",
        options=[
            discord.SelectOption(label="Sprzedaj", description="Sprzedaj coś", value="sprzedaj"),
            discord.SelectOption(label="Kup", description="Kup coś", value="kup")
        ],
        custom_id="sellbuy_select"
    )
    async def select_callback(self, select: discord.ui.Select, interaction: discord.Interaction):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ Nie możesz korzystać z czyjegoś ticketa.", ephemeral=True)
            return

        await interaction.response.defer()
        # zapisz wybór i idź do wyboru serwera
        view = ServerSelectView(self.user, select.values[0])
        await interaction.message.edit(content=f"Wybrałeś: **{select.values[0].capitalize()}**. Teraz wybierz serwer.", view=view)

# --- Server Select ---

class ServerSelectView(View):
    def __init__(self, user, action):  # action = sprzedaj/kup
        super().__init__(timeout=300)
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

# --- Mode Select ---

class ModeSelectView(View):
    def __init__(self, user, action, server):
        super().__init__(timeout=300)
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

# --- Item Select ---

class ItemSelectView(View):
    def __init__(self, user, action, server, mode):
        super().__init__(timeout=300)
        self.user = user
        self.action = action
        self.server = server
        self.mode = mode

        self.selected_items = {}  # item -> ilość (str)

        # Opcje selecta to itemy z danego serwera i trybu + kasa
        items = DATA[server][mode]
        options = [discord.SelectOption(label=i) for i in items]
        self.select = discord.ui.Select(
            placeholder="Wybierz item do dodania",
            options=options,
            custom_id="item_select"
        )
        self.select.callback = self.item_select_callback
        self.add_item(self.select)

        # Przycisk do zakończenia wyboru i pokazania podsumowania
        self.add_item(Button(label="Zakończ wybór", style=discord.ButtonStyle.green, custom_id="finish_selection", row=1))

    async def item_select_callback(self, select: discord.ui.Select, interaction: discord.Interaction):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ Nie możesz korzystać z czyjegoś ticketa.", ephemeral=True)
            return

        item = select.values[0]

        # Jeśli to kasa, poprosimy o kwotę, inaczej o ilość
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

        # Tworzymy ładnego embeda z podsumowaniem
        embed = discord.Embed(title="Podsumowanie ticketa", color=discord.Color.blue())
        embed.add_field(name="Użytkownik", value=self.user.mention, inline=False)
        embed.add_field(name="Akcja", value=self.action.capitalize(), inline=True)
        embed.add_field(name="Serwer", value=self.server, inline=True)
        embed.add_field(name="Tryb", value=self.mode, inline=True)

        items_str = ""
        for it, qty in self.selected_items.items():
            items_str += f"- **{it}**: {qty}\n"
        embed.add_field(name="Wybrane itemy", value=items_str, inline=False)
        embed.set_footer(text="Ktoś wkrótce odpowie na Twojego ticketa.")

        await interaction.response.edit_message(content=None, embed=embed, view=None)

        # Wyślij też podsumowanie na kanał podsumowań
        summary_channel = bot.get_channel(CHANNEL_SUMMARY_ID)
        if summary_channel:
            await summary_channel.send(embed=embed)

# --- Modal do wpisywania ilości / kwoty ---

class AmountModal(Modal):
    def __init__(self, parent_view: ItemSelectView, item_name: str, is_money: bool):
        super().__init__(title=f"Wpisz {'kwotę' if is_money else 'ilość'} dla: {item_name}")

        self.parent_view = parent_view
        self.item_name = item_name
        self.is_money = is_money

        self.amount_input = TextInput(label="Wpisz tutaj:", placeholder="Np. 50 lub 100k", required=True, max_length=20)
        self.add_item(self.amount_input)

    async def on_submit(self, interaction: discord.Interaction):
        amount = self.amount_input.value.strip()
        # Możesz tu dodać walidację ilości/kwoty

        # Dopisz do wybranych itemów (jeśli jest już, to sumujemy lub nadpisujemy)
        if self.item_name in self.parent_view.selected_items:
            # Możesz wybrać czy sumować, albo nadpisywać — tu nadpisujemy
            self.parent_view.selected_items[self.item_name] = amount
        else:
            self.parent_view.selected_items[self.item_name] = amount

        await interaction.response.send_message(f"Dodano **{self.item_name}** z ilością/kwotą: **{amount}**", ephemeral=True)

# --- Przycisk do zamknięcia ticketa ---

class CloseTicketView(View):
    def __init__(self, author_id):
        super().__init__(timeout=None)
        self.author_id = author_id

    @discord.ui.button(label="Zamknij ticket", style=discord.ButtonStyle.red, custom_id="close_ticket_button")
    async def close_ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Sprawdzamy czy użytkownik ma odpowiednią rolę
        if not any(role.id in ROLE_TICKET_CLOSE for role in interaction.user.roles):
            await interaction.response.send_message("❌ Nie masz uprawnień do zamknięcia tego ticketa.", ephemeral=True)
            return

        channel = interaction.channel
        await channel.delete(reason=f"Ticket zamknięty przez {interaction.user}")

@bot.event
async def on_ready():
    print(f'Zalogowano jako {bot.user} (ID: {bot.user.id})')

    # Dodajemy widoki persistent (przyciski działają po restarcie bota)
    bot.add_view(VerificationView(ROLE_VERIFIED_ID))
    bot.add_view(TicketStartView())

    # Weryfikacja - automatycznie wysyłamy embed + przycisk na kanale weryfikacji
    channel_ver = bot.get_channel(CHANNEL_VERIFICATION_ID)
    if channel_ver:
        async for message in channel_ver.history(limit=100):
            if message.author == bot.user:
                await message.delete()

        embed_ver = discord.Embed(
            title="🔒 Weryfikacja",
            description="Kliknij przycisk poniżej, aby otrzymać dostęp do serwera.",
            color=discord.Color.green()
        )
        await channel_ver.send(embed=embed_ver, view=VerificationView(ROLE_VERIFIED_ID))
        print("✅ Wysłano wiadomość weryfikacyjną (embed + przycisk).")
    else:
        print("❌ Nie znaleziono kanału weryfikacji.")

    # Ticket start - wiadomość z przyciskiem do tworzenia ticketa
    channel_ticket_start = bot.get_channel(CHANNEL_TICKET_START_ID)
    if channel_ticket_start:
        async for message in channel_ticket_start.history(limit=100):
            if message.author == bot.user:
                await message.delete()

        embed_ticket_start = discord.Embed(
            title="🎫 System Ticketów",
            description="Kliknij przycisk poniżej, aby utworzyć ticket i otrzymać pomoc.",
            color=discord.Color.blurple()
        )
        await channel_ticket_start.send(embed=embed_ticket_start, view=TicketStartView())
        print("✅ Wysłano wiadomość ticketową (embed + przycisk).")
    else:
        print("❌ Nie znaleziono kanału ticketów.")

bot.run(os.getenv("DISCORD_TOKEN"))
