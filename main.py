import os
import discord
from discord.ext import commands
from discord.ui import View, Button, Select, Modal, TextInput

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- KONFIGURACJA ---

CHANNEL_VERIFICATION_ID = 1373258480382771270
ROLE_VERIFIED_ID = 1373275307150278686

CHANNEL_TICKET_ID = 1373305137228939416
CATEGORY_TICKET_ID = 1373277957446959135
CHANNEL_SUMMARY_ID = 1374479815914291240

# Role z prawem zamykania ticketów
TICKET_CLOSE_ROLES = {1373275898375176232, 1379538984031752212}

# Konfiguracja serwerów -> trybów -> itemów
CONFIG = {
    "Serwer 1": {
        "Tryb A": ["Item1", "Item2", "Kasa"],
        "Tryb B": ["Item3", "Item4", "Kasa"],
    },
    "Serwer 2": {
        "Tryb C": ["Item5", "Item6", "Kasa"],
        "Tryb D": ["Item7", "Item8", "Kasa"],
    },
    "Serwer 3": {
        "Tryb E": ["Item9", "Item10", "Kasa"],
        "Tryb F": ["Item11", "Item12", "Kasa"],
    },
    "Serwer 4": {
        "Tryb G": ["Item13", "Item14", "Kasa"],
        "Tryb H": ["Item15", "Item16", "Kasa"],
    },
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

# --- TICKETY ---

class TicketCloseView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Zamknij ticket", style=discord.ButtonStyle.red, custom_id="close_ticket_button")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        # Sprawdź role użytkownika
        if not any(role.id in TICKET_CLOSE_ROLES for role in interaction.user.roles):
            await interaction.response.send_message("🚫 Nie masz uprawnień do zamknięcia ticketu.", ephemeral=True)
            return
        channel = interaction.channel
        try:
            await interaction.response.send_message("Ticket zostanie zamknięty za 5 sekund...", ephemeral=True)
            await discord.utils.sleep_until(discord.utils.utcnow() + discord.utils.timedelta(seconds=5))
            await channel.delete(reason=f"Ticket zamknięty przez {interaction.user}")
        except Exception as e:
            await interaction.followup.send(f"❗ Błąd przy zamykaniu ticketu: {e}", ephemeral=True)

class ItemModal(Modal):
    def __init__(self, mode, server, mode_name, item_name):
        super().__init__(title="Wpisz szczegóły")
        self.mode = mode          # "kupno" lub "sprzedaz"
        self.server = server
        self.mode_name = mode_name
        self.item_name = item_name

        # Pole na ilość lub opis
        self.add_item(TextInput(label="Wpisz szczegóły (np. ilość, cena, opis)", placeholder="Np. 50k, 3 sztuki itp."))

    async def on_submit(self, interaction: discord.Interaction):
        details = self.children[0].value

        summary_channel = interaction.guild.get_channel(CHANNEL_SUMMARY_ID)
        if not summary_channel:
            await interaction.response.send_message("❌ Nie znaleziono kanału z podsumowaniem.", ephemeral=True)
            return

        embed = discord.Embed(title="Nowa oferta w tickecie", color=discord.Color.blue())
        embed.add_field(name="Tryb", value=self.mode.capitalize(), inline=True)
        embed.add_field(name="Serwer", value=self.server, inline=True)
        embed.add_field(name="Tryb serwera", value=self.mode_name, inline=True)
        embed.add_field(name="Item", value=self.item_name, inline=True)
        embed.add_field(name="Szczegóły", value=details, inline=False)
        embed.set_footer(text=f"Od: {interaction.user} | ID: {interaction.user.id}")

        await summary_channel.send(embed=embed)
        await interaction.response.send_message("✅ Twoja oferta została wysłana na kanał podsumowania.", ephemeral=True)

class ItemSelect(Select):
    def __init__(self, mode, server, mode_name):
        self.mode = mode
        self.server = server
        self.mode_name = mode_name

        # Pobierz itemy z CONFIG
        items = CONFIG[server][mode_name]
        options = [discord.SelectOption(label=item) for item in items]

        super().__init__(placeholder="Wybierz item", options=options, custom_id="item_select")

    async def callback(self, interaction: discord.Interaction):
        item = self.values[0]

        if item.lower() == "kasa":
            # Pokaż modal do wpisania kwoty
            modal = ItemModal(self.mode, self.server, self.mode_name, item)
            await interaction.response.send_modal(modal)
        else:
            # Pokaż modal do wpisania szczegółów itemu
            modal = ItemModal(self.mode, self.server, self.mode_name, item)
            await interaction.response.send_modal(modal)

class ModeSelect(Select):
    def __init__(self, mode, server):
        self.mode = mode
        self.server = server

        modes = list(CONFIG[server].keys())
        options = [discord.SelectOption(label=mode_name) for mode_name in modes]

        super().__init__(placeholder="Wybierz tryb", options=options, custom_id="mode_select")

    async def callback(self, interaction: discord.Interaction):
        mode_name = self.values[0]
        view = View()
        view.add_item(ItemSelect(self.mode, self.server, mode_name))
        view.add_item(TicketCloseView().children[0])  # Dodaj przycisk zamknięcia ticketa

        await interaction.response.edit_message(content=f"Wybrałeś tryb: **{mode_name}**. Teraz wybierz item:", view=view)

class ServerSelect(Select):
    def __init__(self, mode):
        self.mode = mode

        servers = list(CONFIG.keys())
        options = [discord.SelectOption(label=server) for server in servers]

        super().__init__(placeholder="Wybierz serwer", options=options, custom_id="server_select")

    async def callback(self, interaction: discord.Interaction):
        server = self.values[0]
        view = View()
        view.add_item(ModeSelect(self.mode, server))
        # przycisk do zamknięcia ticketa:
        view.add_item(TicketCloseView().children[0])
        await interaction.response.edit_message(content=f"Wybrałeś serwer: **{server}**. Teraz wybierz tryb:", view=view)

class ModeChoiceSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Kupno"),
            discord.SelectOption(label="Sprzedaż"),
        ]
        super().__init__(placeholder="Wybierz czy chcesz kupić czy sprzedać", options=options, custom_id="mode_choice_select")

    async def callback(self, interaction: discord.Interaction):
        choice = self.values[0].lower()
        view = View()
        view.add_item(ServerSelect(choice))
        # przycisk do zamknięcia ticketa:
        view.add_item(TicketCloseView().children[0])
        await interaction.response.edit_message(content=f"Wybrałeś: **{choice.capitalize()}**. Teraz wybierz serwer:", view=view)

class TicketStartView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ModeChoiceSelect())
        self.add_item(TicketCloseView().children[0])

    @discord.ui.button(label="Utwórz ticket", style=discord.ButtonStyle.blurple, custom_id="create_ticket_button")
    async def create_ticket(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        category = guild.get_channel(CATEGORY_TICKET_ID)
        if category is None or not isinstance(category, discord.CategoryChannel):
            await interaction.response.send_message("❌ Nie znaleziono kategorii ticketów.", ephemeral=True)
            return

        # Sprawdź, czy użytkownik już ma ticket
        existing = discord.utils.get(guild.channels, name=f"ticket-{interaction.user.id}")
        if existing:
            await interaction.response.send_message(f"❗ Masz już otwarty ticket: {existing.mention}", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        # Dodaj role do odczytu (np. moderatorzy, admini) - dodaj jeśli chcesz

        channel = await guild.create_text_channel(
            name=f"ticket-{interaction.user.id}",
            category=category,
            overwrites=overwrites,
            reason=f"Ticket utworzony przez {interaction.user}"
        )

        await interaction.response.send_message(f"✅ Ticket utworzony: {channel.mention}", ephemeral=True)
        # Wyślij startowe menu w tickecie
        await channel.send("Witaj! Wybierz poniżej, czy chcesz kupić czy sprzedać:", view=TicketStartView())

@bot.event
async def on_ready():
    print(f"Zalogowano jako {bot.user} (ID: {bot.user.id})")

    bot.add_view(VerificationView(ROLE_VERIFIED_ID))
    bot.add_view(TicketStartView())
    bot.add_view(TicketCloseView())

    # Weryfikacja
    channel_ver = bot.get_channel(CHANNEL_VERIFICATION_ID)
    if channel_ver:
        async for msg in channel_ver.history(limit=100):
            if msg.author == bot.user:
                await msg.delete()
        embed = discord.Embed(
            title="🔒 Weryfikacja",
            description="Kliknij przycisk poniżej, aby otrzymać dostęp do serwera.",
            color=discord.Color.green()
        )
        await channel_ver.send(embed=embed, view=VerificationView(ROLE_VERIFIED_ID))
        print("✅ Wysłano wiadomość weryfikacyjną.")
    else:
        print("❌ Nie znaleziono kanału weryfikacji.")

    # Ticket
    channel_tick = bot.get_channel(CHANNEL_TICKET_ID)
    if channel_tick:
        async for msg in channel_tick.history(limit=100):
            if msg.author == bot.user:
                await msg.delete()
        embed = discord.Embed(
            title="🎫 System Ticketów",
            description="Kliknij przycisk poniżej, aby utworzyć ticket i otrzymać pomoc.",
            color=discord.Color.blurple()
        )
        await channel_tick.send(embed=embed, view=TicketStartView())
        print("✅ Wysłano wiadomość ticketową.")
    else:
        print("❌ Nie znaleziono kanału ticketów.")

bot.run(os.getenv("DISCORD_TOKEN"))
