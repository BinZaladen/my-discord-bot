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

# Role do zamykania ticketów
CLOSER_ROLE_IDS = {1373275898375176232, 1379538984031752212}

# Przykładowa struktura serwer->tryby->itemy, łatwa do edycji:
DATA = {
    "Serwer 1": {
        "Tryb A": ["item1", "item2", "kasa"],
        "Tryb B": ["item3", "item4", "kasa"],
    },
    "Serwer 2": {
        "Tryb C": ["item5", "item6", "kasa"],
        "Tryb D": ["item7", "item8", "kasa"],
    },
    "Serwer 3": {
        "Tryb E": ["item9", "item10", "kasa"],
        "Tryb F": ["item11", "item12", "kasa"],
    },
    "Serwer 4": {
        "Tryb G": ["item13", "item14", "kasa"],
        "Tryb H": ["item15", "item16", "kasa"],
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

# --- MODALE DO ILOŚCI ---

class AmountsModal(Modal):
    def __init__(self, items, ticket_channel, user):
        super().__init__(title="Podaj ilości dla wybranych itemów")
        self.items = items
        self.ticket_channel = ticket_channel
        self.user = user

        # Tworzymy TextInput dla każdego itemu
        for item in items:
            placeholder = "Podaj ilość"
            if item == "kasa":
                placeholder = "Podaj kwotę (np. 50k)"
            self.add_item(TextInput(label=f"Ilość dla {item}", placeholder=placeholder, required=True, max_length=20))

    async def on_submit(self, interaction: discord.Interaction):
        quantities = [child.value for child in self.children]
        summary_lines = [f"**{item}**: {qty}" for item, qty in zip(self.items, quantities)]

        # Wysyłamy podsumowanie na kanale ticketa
        await self.ticket_channel.send(
            f"📝 **Podsumowanie od {self.user.mention}:**\n" + "\n".join(summary_lines) +
            "\n\n💬 Ktoś wkrótce odpowie na Twój ticket."
        )

        # Wysyłamy podsumowanie na kanał podsumowań
        summary_channel = self.ticket_channel.guild.get_channel(CHANNEL_SUMMARY_ID)
        if summary_channel:
            await summary_channel.send(
                f"🎫 **Nowe zgłoszenie od {self.user}**\n"
                f"Kanał: {self.ticket_channel.mention}\n"
                + "\n".join(summary_lines)
            )

        await interaction.response.send_message("✅ Podsumowanie wysłane.", ephemeral=True)

# --- TICKETY z wyborami i modalem ---

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

        # Sprawdzamy czy ticket już istnieje
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

        # Pierwsza wiadomość z wyborem Sprzedaj/Kup i przyciskiem zamknięcia
        await ticket_channel.send(
            f"Witaj {interaction.user.mention}! Wybierz, czy chcesz **Sprzedaj** czy **Kup**:",
            view=SellBuyView(ticket_channel, interaction.user)
        )

        await interaction.response.send_message(f"✅ Ticket utworzony: {ticket_channel.mention}", ephemeral=True)

class SellBuyView(View):
    def __init__(self, ticket_channel, user):
        super().__init__(timeout=None)
        self.ticket_channel = ticket_channel
        self.user = user

    @discord.ui.button(label="Sprzedaj", style=discord.ButtonStyle.red, custom_id="sell")
    async def sell_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(content="Wybierz serwer:", view=ServerSelectView("sprzedaj", self.ticket_channel, self.user))

    @discord.ui.button(label="Kup", style=discord.ButtonStyle.green, custom_id="buy")
    async def buy_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(content="Wybierz serwer:", view=ServerSelectView("kup", self.ticket_channel, self.user))

    @discord.ui.button(label="Zamknij ticket", style=discord.ButtonStyle.grey, custom_id="close_ticket")
    async def close_button(self, interaction: discord.Interaction, button: Button):
        if not any(role.id in CLOSER_ROLE_IDS for role in interaction.user.roles):
            await interaction.response.send_message("🚫 Nie masz uprawnień do zamknięcia ticketu.", ephemeral=True)
            return
        await self.ticket_channel.delete()

class ServerSelectView(View):
    def __init__(self, action, ticket_channel, user):
        super().__init__(timeout=None)
        self.action = action  # 'sprzedaj' lub 'kup'
        self.ticket_channel = ticket_channel
        self.user = user

        options = [discord.SelectOption(label=server) for server in DATA.keys()]
        self.select = Select(placeholder="Wybierz serwer", options=options)
        self.select.callback = self.server_chosen
        self.add_item(self.select)

    async def server_chosen(self, interaction: discord.Interaction):
        server = self.select.values[0]
        await interaction.response.edit_message(content=f"Wybrano serwer: **{server}**\nWybierz tryb:", view=ModeSelectView(self.action, self.ticket_channel, self.user, server))

class ModeSelectView(View):
    def __init__(self, action, ticket_channel, user, server):
        super().__init__(timeout=None)
        self.action = action
        self.ticket_channel = ticket_channel
        self.user = user
        self.server = server

        modes = DATA[server].keys()
        options = [discord.SelectOption(label=mode) for mode in modes]
        self.select = Select(placeholder="Wybierz tryb", options=options)
        self.select.callback = self.mode_chosen
        self.add_item(self.select)

    async def mode_chosen(self, interaction: discord.Interaction):
        mode = self.select.values[0]
        items = DATA[self.server][mode]

        # Przekazujemy do wyboru itemów
        await interaction.response.edit_message(content=f"Wybrano tryb: **{mode}**\nWybierz itemy:", view=ItemSelectView(self.action, self.ticket_channel, self.user, self.server, mode, items))

class ItemSelectView(View):
    def __init__(self, action, ticket_channel, user, server, mode, items):
        super().__init__(timeout=None)
        self.action = action
        self.ticket_channel = ticket_channel
        self.user = user
        self.server = server
        self.mode = mode
        self.items = items

        options = [discord.SelectOption(label=item) for item in items]
        self.select = Select(placeholder="Wybierz itemy (możesz wybrać wiele)", options=options, min_values=1, max_values=len(options))
        self.select.callback = self.items_chosen
        self.add_item(self.select)

    async def items_chosen(self, interaction: discord.Interaction):
        chosen_items = self.select.values
        # Otwieramy modal do wpisania ilości
        modal = AmountsModal(chosen_items, self.ticket_channel, self.user)
        await interaction.response.send_modal(modal)

# --- GŁÓWNA KLASA BOTA ---

@bot.event
async def on_ready():
    print(f'Zalogowano jako {bot.user} (ID: {bot.user.id})')

    bot.add_view(VerificationView(ROLE_VERIFIED_ID))
    bot.add_view(TicketView())

    # Weryfikacja
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

    # Ticket
    channel_ticket = bot.get_channel(CHANNEL_TICKET_ID)
    if channel_ticket:
        async for message in channel_ticket.history(limit=100):
            if message.author == bot.user:
                await message.delete()

        embed_ticket = discord.Embed(
            title="🎫 System Ticketów",
            description="Kliknij przycisk poniżej, aby utworzyć ticket i otrzymać pomoc.",
            color=discord.Color.blurple()
        )
        await channel_ticket.send(embed=embed_ticket, view=TicketView())
        print("✅ Wysłano wiadomość ticketową (embed + przycisk).")
    else:
        print("❌ Nie znaleziono kanału ticketów.")

bot.run(os.getenv("DISCORD_TOKEN"))
