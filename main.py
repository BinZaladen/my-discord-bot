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
CHANNEL_SUMMARY_ID = 1374479815914291240

ROLE_CAN_CLOSE_1 = 1373275898375176232
ROLE_CAN_CLOSE_2 = 1379538984031752212

# --- Dane serwerów, trybów i itemów (przykład, możesz zmienić) ---
DATA = {
    "Serwer 1": {
        "Tryb A": ["item1", "item2", "kasa"],
        "Tryb B": ["item3", "item4", "kasa"]
    },
    "Serwer 2": {
        "Tryb C": ["item5", "item6", "kasa"],
        "Tryb D": ["item7", "item8", "kasa"]
    },
    "Serwer 3": {
        "Tryb E": ["item9", "item10", "kasa"],
        "Tryb F": ["item11", "item12", "kasa"]
    },
    "Serwer 4": {
        "Tryb G": ["item13", "item14", "kasa"],
        "Tryb H": ["item15", "item16", "kasa"]
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

# --- Modal do wpisania kwoty kasy ---
class AmountModal(Modal, title="Podaj kwotę kasy"):
    def __init__(self, parent_view):
        super().__init__()
        self.parent_view = parent_view
        self.amount = TextInput(label="Kwota", placeholder="Np. 50k, 100000", max_length=20)
        self.add_item(self.amount)

    async def on_submit(self, interaction: discord.Interaction):
        value = self.amount.value.strip()
        if not value:
            await interaction.response.send_message("❌ Musisz podać kwotę.", ephemeral=True)
            return
        self.parent_view.selected_items["kasa"] = value
        await interaction.response.edit_message(content=self.parent_view.get_summary_text(), view=self.parent_view)

# --- View do wyboru ilości itemu (1-15) ---
class AmountSelectView(View):
    def __init__(self, parent_view, item_name):
        super().__init__(timeout=120)
        self.parent_view = parent_view
        self.item_name = item_name

        options = [discord.SelectOption(label=str(i), description=f"Ilość: {i}", value=str(i)) for i in range(1, 16)]
        self.select = Select(
            placeholder="Wybierz ilość (1-15)",
            options=options,
            custom_id="amount_select"
        )
        self.select.callback = self.amount_select_callback
        self.add_item(self.select)

    async def amount_select_callback(self, select: Select, interaction: discord.Interaction):
        if interaction.user != self.parent_view.user:
            await interaction.response.send_message("❌ Nie możesz korzystać z czyjegoś ticketa.", ephemeral=True)
            return

        amount = select.values[0]
        self.parent_view.selected_items[self.item_name] = amount
        await interaction.response.edit_message(content=self.parent_view.get_summary_text(), view=self.parent_view)

# --- View wyboru itemów ---
class ItemSelectView(View):
    def __init__(self, user, action, server, mode):
        super().__init__(timeout=300)
        self.user = user
        self.action = action  # "Sprzedaj" lub "Kup"
        self.server = server
        self.mode = mode
        self.selected_items = {}  # {item: ilość/kwota}

        items = DATA[server][mode]
        options = [discord.SelectOption(label=i) for i in items]
        self.item_select = Select(
            placeholder="Wybierz item do dodania",
            options=options,
            custom_id="item_select"
        )
        self.item_select.callback = self.item_select_callback
        self.add_item(self.item_select)

        self.finish_btn = Button(label="Zakończ wybór", style=discord.ButtonStyle.green, custom_id="finish_selection")
        self.finish_btn.callback = self.finish_callback
        self.add_item(self.finish_btn)

    def get_summary_text(self):
        lines = [f"**{self.action} na serwerze:** {self.server}", f"**Tryb:** {self.mode}", "\n**Wybrane przedmioty:**"]
        if not self.selected_items:
            lines.append("_Brak wybranych itemów._")
        else:
            for item, amount in self.selected_items.items():
                lines.append(f"- {item} x {amount}")
        lines.append("\n*Ktoś wkrótce odpowie na twój ticket, prosimy o cierpliwość.*")
        return "\n".join(lines)

    async def item_select_callback(self, select: Select, interaction: discord.Interaction):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ Nie możesz korzystać z czyjegoś ticketa.", ephemeral=True)
            return

        item = select.values[0]
        if item == "kasa":
            modal = AmountModal(self)
            await interaction.response.send_modal(modal)
        else:
            view = AmountSelectView(self, item)
            await interaction.response.edit_message(content=f"Wybierz ilość dla **{item}**", view=view)

    async def finish_callback(self, button: Button, interaction: discord.Interaction):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ Nie możesz korzystać z czyjegoś ticketa.", ephemeral=True)
            return

        # Wyślij podsumowanie embedem na kanał ticketa i kanał podsumowań
        embed = discord.Embed(title="Podsumowanie ticketa", color=discord.Color.blue())
        embed.add_field(name="Użytkownik", value=interaction.user.mention, inline=False)
        embed.add_field(name="Akcja", value=self.action, inline=True)
        embed.add_field(name="Serwer", value=self.server, inline=True)
        embed.add_field(name="Tryb", value=self.mode, inline=True)

        if self.selected_items:
            items_text = "\n".join(f"{item} × {amount}" for item, amount in self.selected_items.items())
        else:
            items_text = "_Brak itemów_"
        embed.add_field(name="Wybrane itemy", value=items_text, inline=False)
        embed.set_footer(text="Ktoś wkrótce odpowie na twój ticket. Prosimy o cierpliwość.")

        # Wyślij na kanał ticketa
        await interaction.message.edit(embed=embed, view=None)
        # Wyślij na kanał podsumowań
        channel_summary = bot.get_channel(CHANNEL_SUMMARY_ID)
        if channel_summary:
            await channel_summary.send(embed=embed)

        await interaction.response.send_message("✅ Podsumowanie wysłane.", ephemeral=True)

# --- Select wybierania serwera ---
class ServerSelectView(View):
    def __init__(self, user, action):
        super().__init__(timeout=300)
        self.user = user
        self.action = action
        options = [discord.SelectOption(label=server) for server in DATA.keys()]
        self.select = Select(placeholder="Wybierz serwer", options=options, custom_id="server_select")
        self.select.callback = self.server_select_callback
        self.add_item(self.select)

    async def server_select_callback(self, select: Select, interaction: discord.Interaction):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ Nie możesz korzystać z czyjegoś ticketa.", ephemeral=True)
            return

        server = select.values[0]
        # Idziemy do wyboru trybu
        view = ModeSelectView(self.user, self.action, server)
        await interaction.response.edit_message(content=f"Wybrałeś serwer: **{server}**\nWybierz tryb:", view=view)

# --- Select wybierania trybu ---
class ModeSelectView(View):
    def __init__(self, user, action, server):
        super().__init__(timeout=300)
        self.user = user
        self.action = action
        self.server = server
        options = [discord.SelectOption(label=mode) for mode in DATA[server].keys()]
        self.select = Select(placeholder="Wybierz tryb", options=options, custom_id="mode_select")
        self.select.callback = self.mode_select_callback
        self.add_item(self.select)

    async def mode_select_callback(self, select: Select, interaction: discord.Interaction):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ Nie możesz korzystać z czyjegoś ticketa.", ephemeral=True)
            return

        mode = select.values[0]
        view = ItemSelectView(self.user, self.action, self.server, mode)
        await interaction.response.edit_message(content=f"Wybrałeś tryb: **{mode}**\nWybierz itemy:", view=view)

# --- Komenda tworzenia ticketa ---
@bot.command()
async def ticket(ctx):
    # Stwórz kanał ticket
    overwrites = {
        ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        ctx.guild.me: discord.PermissionOverwrite(read_messages=True)
    }
    category = bot.get_channel(CATEGORY_TICKET_ID)
    channel = await ctx.guild.create_text_channel(f"ticket-{ctx.author.name}", overwrites=overwrites, category=category)

    view = ActionSelectView(ctx.author)
    await channel.send(f"Witaj {ctx.author.mention}! Co chcesz zrobić?", view=view)
    await ctx.message.reply(f"Ticket utworzony: {channel.mention}", ephemeral=True)

class ActionSelectView(View):
    def __init__(self, user):
        super().__init__(timeout=300)
        self.user = user
        options = [
            discord.SelectOption(label="Sprzedaj"),
            discord.SelectOption(label="Kup")
        ]
        self.select = Select(placeholder="Wybierz akcję", options=options, custom_id="action_select")
        self.select.callback = self.action_select_callback
        self.add_item(self.select)

    async def action_select_callback(self, select: Select, interaction: discord.Interaction):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ Nie możesz korzystać z czyjegoś ticketa.", ephemeral=True)
            return

        action = select.values[0]
        view = ServerSelectView(self.user, action)
        await interaction.response.edit_message(content=f"Wybrałeś: **{action}**\nWybierz serwer:", view=view)

# --- Przycisk zamknięcia ticketa ---
class CloseTicketView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.close_button = Button(label="Zamknij ticket", style=discord.ButtonStyle.red, custom_id="close_ticket")
        self.close_button.callback = self.close_callback
        self.add_item(self.close_button)

    async def close_callback(self, button: Button, interaction: discord.Interaction):
        roles = [r.id for r in interaction.user.roles]
        if ROLE_CAN_CLOSE_1 not in roles and ROLE_CAN_CLOSE_2 not in roles:
            await interaction.response.send_message("❌ Nie masz uprawnień, aby zamknąć ticket.", ephemeral=True)
            return
        await interaction.response.send_message("Ticket zostanie zamknięty za 5 sekund...", ephemeral=True)
        await interaction.channel.delete(delay=5)

# --- Eventy ---
@bot.event
async def on_ready():
    print(f"Bot zalogowany jako {bot.user}!")
    # Wstaw widok do kanału weryfikacji na stałe (opcjonalnie)
    channel = bot.get_channel(CHANNEL_VERIFICATION_ID)
    if channel:
        view = VerificationView(ROLE_VERIFIED_ID)
        try:
            # Usuń stare wiadomości z tym widokiem i wyślij nową (opcjonalnie)
            await channel.purge(limit=5)
            await channel.send("Kliknij przycisk, aby się zweryfikować:", view=view)
        except Exception:
            pass

# --- Komenda startowa do weryfikacji ---
@bot.command()
async def verify(ctx):
    view = VerificationView(ROLE_VERIFIED_ID)
    await ctx.send("Kliknij przycisk, aby się zweryfikować:", view=view)

# --- Uruchomienie bota ---
bot.run(os.getenv("TOKEN"))
