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

        # Sprawdź, czy użytkownik już ma otwarty ticket (kanał z nazwą ticket-<user_id> w kategorii ticketów)
        existing_channel = None
        for channel in guild.channels:
            if (
                channel.name == f"ticket-{interaction.user.id}"
                and isinstance(channel, discord.TextChannel)
                and channel.category and channel.category.id == CATEGORY_TICKET_ID
            ):
                existing_channel = channel
                break

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
        if interaction.user.id != self.user.id:
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
        if interaction.user.id != self.user.id:
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
        if interaction.user.id != self.user.id:
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
        if interaction.user.id != self.user.id:
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
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ Nie możesz korzystać z czyjegoś ticketa.", ephemeral=True)
            return
        if not self.selected_items:
            await interaction.response.send_message("❗ Nie wybrałeś żadnych itemów.", ephemeral=True)
            return

        # Tworzymy ładnego embeda z podsumowaniem
        embed = discord.Embed(title="Podsumowanie ticketa", color=discord.Color.blue())
        embed.add_field(name="Użytkownik", value=self.user.mention, inline=False)
        embed.add_field(name="Akcja", value=self.action.capitalize(), inline=False)
        embed.add_field(name="Serwer", value=self.server, inline=False)
        embed.add_field(name="Tryb", value=self.mode, inline=False)

        desc = ""
        for item, amount in self.selected_items.items():
            desc += f"**{item}**: {amount}\n"

        embed.add_field(name="Wybrane itemy", value=desc, inline=False)
        embed.set_footer(text="Ticket System Bot")

        await interaction.response.send_message("✅ Podsumowanie utworzone. Przesłane na kanał podsumowań.", ephemeral=True)

        # Wysyłamy embed na kanał podsumowań
        channel = interaction.guild.get_channel(CHANNEL_SUMMARY_ID)
        if channel:
            await channel.send(embed=embed)
        else:
            await interaction.followup.send("❗ Nie znaleziono kanału podsumowań.", ephemeral=True)

# --- Amount Modal ---

class AmountModal(Modal):
    def __init__(self, parent_view, item, is_money):
        super().__init__(title=f"Ilość dla {item}", timeout=300)
        self.parent_view = parent_view
        self.item = item
        self.is_money = is_money

        label = "Kwota" if is_money else "Ilość"
        self.amount = TextInput(label=label, placeholder="Podaj liczbę", required=True)
        self.add_item(self.amount)

    async def on_submit(self, interaction: discord.Interaction):
        val = self.amount.value
        if not val.isdigit():
            await interaction.response.send_message("❌ Podaj poprawną liczbę.", ephemeral=True)
            return

        self.parent_view.selected_items[self.item] = val
        await interaction.response.send_message(f"✅ Dodano {self.item} - {val}.", ephemeral=True)

# --- Komenda do uruchomienia ticket start message ---

@bot.command()
@commands.has_permissions(administrator=True)
async def ticketstart(ctx):
    view = TicketStartView()
    await ctx.send("Kliknij przycisk, aby utworzyć ticket.", view=view)

# --- Weryfikacja start (na kanale) ---

@bot.command()
@commands.has_permissions(administrator=True)
async def sendverify(ctx):
    view = VerificationView(ROLE_VERIFIED_ID)
    await ctx.send("Kliknij przycisk, aby się zweryfikować.", view=view)

bot.run(os.getenv("DISCORD_TOKEN"))
