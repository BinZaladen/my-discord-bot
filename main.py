import os
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Modal, TextInput
import asyncio
import random

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# --- Ustaw ID serwera do rejestracji lokalnych komend slash ---
GUILD_ID = 1373253103176122399  # <-- wpisz tutaj ID swojego serwera

# ID kanałów, kategorii i ról
CHANNEL_VERIFICATION_ID = 1373258480382771270
ROLE_VERIFIED_ID = 1373275307150278686

CHANNEL_TICKET_START_ID = 1373305137228939416
CATEGORY_TICKET_ID = 1373277957446959135

ROLE_TICKET_CLOSE = [1373275898375176232, 1379538984031752212]

CHANNEL_SUMMARY_ID = 1374479815914291240

ROLE_CUSTOMER_ID = 1374099985288921088  # Rola 'customer' do nadania po realizacji

CHANNEL_RATINGS_ID = 1375528888586731762  # Kanał ocen

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

# --- Pamięć ocen (ticket_id: set(user_id)) ---
already_rated = {}

# --- WERYFIKACJA ---
class VerificationView(View):
    def __init__(self, role_id):
        super().__init__(timeout=None)
        self.role_id = role_id
        self.current_answer = None
        self.question = None
        self.generate_question()

    def generate_question(self):
        a = random.randint(1, 10)
        b = random.randint(1, 10)
        self.question = f"{a} + {b} = ?"
        self.current_answer = str(a + b)

    @discord.ui.button(label="Zweryfikuj się", style=discord.ButtonStyle.green, custom_id="verify_button")
    async def verify_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(VerificationModal(self, self.question))

class VerificationModal(Modal):
    def __init__(self, parent_view: VerificationView, question: str):
        super().__init__(title="Weryfikacja - rozwiąż zadanie")
        self.parent_view = parent_view
        self.answer_input = TextInput(label=question, placeholder="Wpisz odpowiedź", max_length=5)
        self.add_item(self.answer_input)

    async def on_submit(self, interaction: discord.Interaction):
        if self.answer_input.value.strip() == self.parent_view.current_answer:
            role = discord.utils.get(interaction.guild.roles, id=self.parent_view.role_id)
            if role:
                try:
                    await interaction.user.add_roles(role)
                    await interaction.response.send_message("✅ Zostałeś zweryfikowany!", ephemeral=True)
                except discord.Forbidden:
                    await interaction.response.send_message("🚫 Bot nie ma uprawnień do nadania roli.", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Nie znaleziono roli weryfikacji.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Niepoprawna odpowiedź, spróbuj ponownie.", ephemeral=True)

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
        await ticket_channel.send(f"Witaj {interaction.user.mention}! Wybierz, czy chcesz coś sprzedać lub kupić.", view=SellBuySelectView(interaction.user))

# --- Sell or Buy Select ---
class SellBuySelectView(View):
    def __init__(self, user):
        super().__init__(timeout=300)
        self.user = user

        select = discord.ui.Select(
            placeholder="Wybierz Sprzedaj lub Kup",
            options=[
                discord.SelectOption(label="Sprzedaj", description="Sprzedaj coś", value="sprzedaj"),
                discord.SelectOption(label="Kup", description="Kup coś", value="kup")
            ],
            custom_id="sellbuy_select"
        )

        async def callback(interaction: discord.Interaction):
            if interaction.user != self.user:
                await interaction.response.send_message("❌ Nie możesz korzystać z czyjegoś ticketa.", ephemeral=True)
                return

            action = interaction.data['values'][0]
            view = ServerSelectView(self.user, action)
            await interaction.response.edit_message(content=f"Wybrałeś: **{action.capitalize()}**. Teraz wybierz serwer.", view=view)

        select.callback = callback
        self.add_item(select)

# --- Server Select ---
class ServerSelectView(View):
    def __init__(self, user, action):
        super().__init__(timeout=300)
        self.user = user
        self.action = action

        options = [discord.SelectOption(label=s) for s in DATA.keys()]
        select = discord.ui.Select(
            placeholder="Wybierz serwer",
            options=options,
            custom_id="server_select"
        )

        async def callback(interaction: discord.Interaction):
            if interaction.user != self.user:
                await interaction.response.send_message("❌ Nie możesz korzystać z czyjegoś ticketa.", ephemeral=True)
                return

            server = interaction.data['values'][0]
            view = ModeSelectView(self.user, self.action, server)
            await interaction.response.edit_message(content=f"Wybrałeś serwer: **{server}**. Teraz wybierz tryb.", view=view)

        select.callback = callback
        self.add_item(select)

# --- Mode Select ---
class ModeSelectView(View):
    def __init__(self, user, action, server):
        super().__init__(timeout=300)
        self.user = user
        self.action = action
        self.server = server

        modes = DATA[server].keys()
        select = discord.ui.Select(
            placeholder="Wybierz tryb",
            options=[discord.SelectOption(label=m) for m in modes],
            custom_id="mode_select"
        )

        async def callback(interaction: discord.Interaction):
            if interaction.user != self.user:
                await interaction.response.send_message("❌ Nie możesz korzystać z czyjegoś ticketa.", ephemeral=True)
                return

            mode = interaction.data['values'][0]
            view = ItemSelectView(self.user, self.action, self.server, mode)
            await interaction.response.edit_message(content=f"Wybrałeś tryb: **{mode}**. Teraz wybierz itemy.", view=view)

        select.callback = callback
        self.add_item(select)

# --- Item Select ---
class ItemSelectView(View):
    def __init__(self, user, action, server, mode):
        super().__init__(timeout=300)
        self.user = user
        self.action = action
        self.server = server
        self.mode = mode

        self.selected_items = {}  # {item_name: amount}

        self.select = discord.ui.Select(
            placeholder="Wybierz item do dodania",
            options=[discord.SelectOption(label=i) for i in DATA[server][mode]],
            custom_id="item_select"
        )
        self.select.callback = self.item_select_callback
        self.add_item(self.select)

        self.finish_button = Button(label="Zakończ wybór", style=discord.ButtonStyle.green, custom_id="finish_selection")
        self.finish_button.callback = self.finish_selection_callback
        self.add_item(self.finish_button)

    async def item_select_callback(self, interaction: discord.Interaction):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ Nie możesz korzystać z czyjegoś ticketa.", ephemeral=True)
            return

        item = interaction.data['values'][0]
        modal = AmountModal(self, item, is_money=(item == "kasa"))
        await interaction.response.send_modal(modal)

    async def finish_selection_callback(self, interaction: discord.Interaction):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ Nie możesz korzystać z czyjegoś ticketa.", ephemeral=True)
            return

        if not self.selected_items:
            await interaction.response.send_message("❗ Nie wybrałeś żadnych itemów.", ephemeral=True)
            return

        embed = discord.Embed(title="Podsumowanie ticketa", color=discord.Color.blue())
        embed.add_field(name="Użytkownik", value=self.user.mention, inline=False)
        embed.add_field(name="Akcja", value=self.action.capitalize(), inline=True)
        embed.add_field(name="Serwer", value=self.server, inline=True)
        embed.add_field(name="Tryb", value=self.mode, inline=True)

        items_str = "\n".join(f"- **{it}**: {qty}" for it, qty in self.selected_items.items())
        embed.add_field(name="Wybrane itemy", value=items_str, inline=False)
        embed.set_footer(text="Ktoś wkrótce odpowie na Twojego ticketa.")

        await interaction.response.edit_message(content=None, embed=embed, view=None)

        summary_channel = bot.get_channel(CHANNEL_SUMMARY_ID)
        if summary_channel:
            member = interaction.guild.get_member(self.user.id)
            view = RealizeOrderView(member)
            await summary_channel.send(embed=embed, view=view)

        await interaction.followup.send("✅ Jeśli wszystko się zgadza, możesz zamknąć ticketa:", view=CloseTicketView(self.user.id))


class AmountModal(Modal):
    def __init__(self, parent_view: ItemSelectView, item_name: str, is_money: bool):
        super().__init__(title=f"Wpisz {'kwotę' if is_money else 'ilość'} dla: {item_name}")
        self.parent_view = parent_view
        self.item_name = item_name
        self.is_money = is_money
        self.amount_input = TextInput(
            label="Wpisz tutaj:",
            placeholder="Np. 100k" if is_money else "Np. 5",
            required=True,
            max_length=20
        )
        self.add_item(self.amount_input)

    async def on_submit(self, interaction: discord.Interaction):
        amount_raw = self.amount_input.value.strip()

        try:
            amount_num = float(amount_raw.lower().replace("k", "000").replace(" ", ""))
        except ValueError:
            await interaction.response.send_message("❌ Podano niepoprawną liczbę.", ephemeral=True)
            return

        # Dodaj lub sumuj
        if self.item_name in self.parent_view.selected_items:
            prev = self.parent_view.selected_items[self.item_name]
            try:
                prev_num = float(str(prev).lower().replace("k", "000").replace(" ", ""))
                total = prev_num + amount_num
                self.parent_view.selected_items[self.item_name] = str(total)
            except:
                self.parent_view.selected_items[self.item_name] = amount_raw
        else:
            self.parent_view.selected_items[self.item_name] = amount_raw

        await interaction.response.send_message(
            f"Dodano **{self.item_name}** z wartością: **{amount_raw}**.\n\n"
            "Możesz wybrać kolejny item lub zakończyć wybór.",
            ephemeral=True
        )

        # Po modalu wróć do wyboru itemów
        await interaction.message.edit(view=self.parent_view)


# --- Close Ticket ---
class CloseTicketView(View):
    def __init__(self, author_id):
        super().__init__(timeout=None)
        self.author_id = author_id

    @discord.ui.button(label="Zamknij ticket", style=discord.ButtonStyle.red, custom_id="close_ticket_button")
    async def close_ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not any(role.id in ROLE_TICKET_CLOSE for role in interaction.user.roles):
            await interaction.response.send_message("❌ Nie masz uprawnień do zamknięcia tego ticketa.", ephemeral=True)
            return
        await interaction.channel.delete(reason=f"Ticket zamknięty przez {interaction.user}")

# --- Realize Order Button ---
class RealizeOrderView(View):
    def __init__(self, user: discord.Member):
        super().__init__(timeout=None)
        self.user = user

    @discord.ui.button(label="✅ Zrealizuj", style=discord.ButtonStyle.green, custom_id="realize_order_button")
    async def realize_button(self, interaction: discord.Interaction, button: Button):
        role = discord.utils.get(interaction.guild.roles, id=ROLE_CUSTOMER_ID)
        if not role:
            await interaction.response.send_message("❌ Nie znaleziono roli `customer`.", ephemeral=True)
            return

        try:
            await self.user.add_roles(role)
            await interaction.message.delete()
            await interaction.response.send_message(f"✅ Zamówienie użytkownika {self.user.mention} zostało oznaczone jako zrealizowane.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ Bot nie ma uprawnień do nadania roli.", ephemeral=True)

# --- OCENY ---

# Panel startowy z embedem i przyciskiem do wystawiania oceny
class RatingsPanelView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Wystaw ocenę ⭐", style=discord.ButtonStyle.primary, custom_id="panel_rate_button")
    async def panel_rate_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(RateModal())

# Modal do wystawienia oceny
class RateModal(Modal, title="Wystaw ocenę (1-5 gwiazdek)"):
    ticket_id_input = TextInput(label="ID ticketa (kanału)", placeholder="Np. 123456789012345678", required=True)
    rating_input = TextInput(label="Ile gwiazdek? (1-5)", placeholder="Np. 5", max_length=1)

    def __init__(self):
        super().__init__()
        self.add_item(self.ticket_id_input)
        self.add_item(self.rating_input)

    async def on_submit(self, interaction: discord.Interaction):
        ticket_id_str = self.ticket_id_input.value.strip()
        try:
            ticket_id = int(ticket_id_str)
        except:
            await interaction.response.send_message("❌ Podaj poprawne ID ticketa (kanału).", ephemeral=True)
            return

        try:
            rating = int(self.rating_input.value)
            if rating < 1 or rating > 5:
                raise ValueError
        except ValueError:
            await interaction.response.send_message("❌ Podaj liczbę od 1 do 5.", ephemeral=True)
            return

        # Sprawdzenie czy użytkownik już ocenił ten ticket
        if ticket_id in already_rated and interaction.user.id in already_rated[ticket_id]:
            await interaction.response.send_message("❌ Oceniłeś już to zamówienie.", ephemeral=True)
            return

        if ticket_id not in already_rated:
            already_rated[ticket_id] = set()
        already_rated[ticket_id].add(interaction.user.id)

        guild = interaction.guild
        channel_ratings = guild.get_channel(CHANNEL_RATINGS_ID)
        member = guild.get_member(interaction.user.id)

        if not channel_ratings:
            await interaction.response.send_message("❌ Kanał do ocen nie został znaleziony.", ephemeral=True)
            return

        ticket_channel = guild.get_channel(ticket_id)

        embed = discord.Embed(
            title="Nowa ocena zamówienia",
            color=discord.Color.gold(),
            timestamp=interaction.created_at
        )
        embed.add_field(name="Klient", value=member.mention if member else f"<@{interaction.user.id}>", inline=False)
        embed.add_field(name="Ticket", value=ticket_channel.mention if ticket_channel else "Nieznany", inline=False)
        embed.add_field(name="Ocena", value=f"{'⭐' * rating} ({rating}/5)", inline=False)
        embed.set_footer(text="Dziękujemy za Twoją opinię!")

        # Pod embedem informacja i przycisk do wystawienia kolejnej oceny
        await channel_ratings.send(embed=embed, view=RatingsInfoView())

        await interaction.response.send_message("✅ Dziękujemy za wystawienie oceny!", ephemeral=True)

# View z informacją i przyciskiem pod oceną
class RatingsInfoView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Jak wystawić ocenę? Kliknij tutaj", style=discord.ButtonStyle.secondary, custom_id="info_rate_button")
    async def info_rate_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(RateModal())

# --- Event on_ready - wysyła wiadomość startową na kanał ocen jeśli jej nie ma ---
@bot.event
async def on_ready():
    print(f'Zalogowano jako {bot.user} (ID: {bot.user.id})')

    guild = bot.get_guild(GUILD_ID)
    if not guild:
        print("Nie znaleziono guilda.")
        return

    channel_ratings = guild.get_channel(CHANNEL_RATINGS_ID)
    if not channel_ratings:
        print("Nie znaleziono kanału ocen.")
        return

    # Sprawdź, czy jest już wiadomość startowa z panelem
    found = False
    async for message in channel_ratings.history(limit=50):
        if message.author == bot.user:
            for comp in message.components:
                for item in comp.children:
                    if getattr(item, "custom_id", None) == "panel_rate_button":
                        found = True
                        break
                if found:
                    break
        if found:
            break

    if not found:
        embed = discord.Embed(
            title="Panel ocen zamówień",
            description="Kliknij przycisk poniżej, aby wystawić ocenę za swoje zamówienie.",
            color=discord.Color.gold()
        )
        await channel_ratings.send(embed=embed, view=RatingsPanelView())

bot.run(os.getenv("DISCORD_TOKEN"))
