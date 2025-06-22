import os
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Select, Modal, TextInput
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

CHANNEL_RATINGS_ID = 1375528888586731762  # Kanał gdzie będą pokazywane oceny

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

# --- PAMIĘĆ OCEN: (user_id, ticket_id) -> True jeśli ocenił ---
user_ratings = {}
# --- PAMIĘĆ ZAMÓWIEŃ (ticket_id -> dane zamówienia) ---
orders_data = {}

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
                    embed = discord.Embed(
                        title="✅ Weryfikacja zakończona!",
                        description=f"Gratulacje {interaction.user.mention}, pomyślnie zweryfikowano Cię i nadano rolę.",
                        color=discord.Color.green()
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                except discord.Forbidden:
                    await interaction.response.send_message("🚫 Bot nie ma uprawnień do nadania roli.", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Nie znaleziono roli weryfikacji.", ephemeral=True)
        else:
            embed = discord.Embed(
                title="❌ Niepoprawna odpowiedź!",
                description="Spróbuj jeszcze raz rozwiązać zadanie matematyczne.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

# --- Ticket Start View ---
class TicketStartView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Utwórz ticket", style=discord.ButtonStyle.blurple, custom_id="create_ticket_button")
    async def create_ticket(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        category = guild.get_channel(CATEGORY_TICKET_ID)
        if category is None or not isinstance(category, discord.CategoryChannel):
            embed = discord.Embed(
                title="❌ Błąd",
                description="Nie znaleziono kategorii ticketów. Skontaktuj się z administratorem.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        existing_channel = discord.utils.get(guild.channels, name=f"ticket-{interaction.user.id}")
        if existing_channel:
            embed = discord.Embed(
                title="❗ Masz już otwarty ticket",
                description=f"Przejdź do swojego ticketa: {existing_channel.mention}",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
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

        embed = discord.Embed(
            title="🎫 Ticket utworzony!",
            description=f"Witaj {interaction.user.mention}!\nWybierz, czy chcesz coś **sprzedać** lub **kupić**.",
            color=discord.Color.blurple()
        )
        await ticket_channel.send(embed=embed, view=SellBuySelectView(interaction.user))
        embed_resp = discord.Embed(
            title="✅ Ticket utworzony",
            description=f"Twój ticket został utworzony: {ticket_channel.mention}\nW nim wybierz dalsze opcje.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed_resp, ephemeral=True)

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
                embed = discord.Embed(
                    title="❌ Błąd",
                    description="Nie możesz korzystać z czyjegoś ticketa.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            action = interaction.data['values'][0]
            view = ServerSelectView(self.user, action)
            embed = discord.Embed(
                title=f"Wybrałeś: {action.capitalize()}",
                description="Teraz wybierz serwer.",
                color=discord.Color.blue()
            )
            await interaction.response.edit_message(embed=embed, view=view)

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
                embed = discord.Embed(
                    title="❌ Błąd",
                    description="Nie możesz korzystać z czyjegoś ticketa.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            server = interaction.data['values'][0]
            view = ModeSelectView(self.user, self.action, server)
            embed = discord.Embed(
                title=f"Wybrałeś serwer: {server}",
                description="Teraz wybierz tryb.",
                color=discord.Color.blue()
            )
            await interaction.response.edit_message(embed=embed, view=view)

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
                embed = discord.Embed(
                    title="❌ Błąd",
                    description="Nie możesz korzystać z czyjegoś ticketa.",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            mode = interaction.data['values'][0]
            view = ItemSelectView(self.user, self.action, self.server, mode)
            embed = discord.Embed(
                title=f"Wybrałeś tryb: {mode}",
                description="Teraz wybierz itemy.",
                color=discord.Color.blue()
            )
            await interaction.response.edit_message(embed=embed, view=view)

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
            embed = discord.Embed(
                title="❌ Błąd",
                description="Nie możesz korzystać z czyjegoś ticketa.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        item = interaction.data['values'][0]
        modal = AmountModal(self, item, is_money=(item == "kasa"))
        await interaction.response.send_modal(modal)

    async def finish_selection_callback(self, interaction: discord.Interaction):
        if interaction.user != self.user:
            embed = discord.Embed(
                title="❌ Błąd",
                description="Nie możesz korzystać z czyjegoś ticketa.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if not self.selected_items:
            embed = discord.Embed(
                title="❗ Brak wybranych itemów",
                description="Nie wybrałeś żadnych itemów.",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Zapisz dane zamówienia do globalnej pamięci
        orders_data[str(interaction.channel.id)] = {
            "user_id": self.user.id,
            "action": self.action,
            "server": self.server,
            "mode": self.mode,
            "items": self.selected_items.copy()
        }

        embed = discord.Embed(title="📋 Podsumowanie ticketa", color=discord.Color.blue())
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
            view = RealizeOrderView(member, ticket_id=str(interaction.channel.id))
            await summary_channel.send(embed=embed, view=view)

        embed_close = discord.Embed(
            title="✅ Jeśli wszystko się zgadza, możesz zamknąć ticketa:",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed_close, view=CloseTicketView(self.user.id))


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
            embed = discord.Embed(
                title="❌ Błąd",
                description="Podano niepoprawną liczbę.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
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

        embed = discord.Embed(
            title="✅ Dodano item",
            description=f"Dodano **{self.item_name}** z wartością: **{amount_raw}**.\n\nMożesz wybrać kolejny item lub zakończyć wybór.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

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
            embed = discord.Embed(
                title="❌ Brak uprawnień",
                description="Nie masz uprawnień do zamknięcia tego ticketa.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        await interaction.channel.delete(reason=f"Ticket zamknięty przez {interaction.user}")

# --- Realize Order Button ---
class RealizeOrderView(View):
    def __init__(self, user: discord.Member, ticket_id: str):
        super().__init__(timeout=None)
        self.user = user
        self.ticket_id = ticket_id

    @discord.ui.button(label="✅ Zrealizuj", style=discord.ButtonStyle.green, custom_id="realize_order_button")
    async def realize_button(self, interaction: discord.Interaction, button: Button):
        role = discord.utils.get(interaction.guild.roles, id=ROLE_CUSTOMER_ID)
        if not role:
            embed = discord.Embed(
                title="❌ Błąd",
                description="Nie znaleziono roli `customer`.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            await self.user.add_roles(role)
            # Usuwamy wiadomość z realizacją (przycisk znika)
            await interaction.message.delete()
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="✅ Zamówienie zrealizowane!",
                    description=f"Zamówienie użytkownika {self.user.mention} zostało oznaczone jako zrealizowane.",
                    color=discord.Color.green()
                ),
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="❌ Błąd",
                    description="Bot nie ma uprawnień do nadania roli.",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )

# --- Rating (Oceny) ---

class RatingModal(Modal):
    def __init__(self, user: discord.Member, ticket_id: str, order_info: dict):
        super().__init__(title="Wystaw ocenę i komentarz")
        self.user = user
        self.ticket_id = ticket_id
        self.order_info = order_info

        self.rating_select = Select(
            placeholder="Wybierz ocenę",
            options=[
                discord.SelectOption(label="⭐️", description="1 - Słabo", value="1"),
                discord.SelectOption(label="⭐⭐️", description="2 - Można lepiej", value="2"),
                discord.SelectOption(label="⭐⭐⭐️", description="3 - OK", value="3"),
                discord.SelectOption(label="⭐⭐⭐⭐️", description="4 - Dobrze", value="4"),
                discord.SelectOption(label="⭐⭐⭐⭐⭐️", description="5 - Świetnie", value="5"),
            ],
            custom_id="rating_select"
        )
        self.add_item(self.rating_select)

        self.comment = TextInput(
            label="Komentarz (opcjonalny)",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=300,
            placeholder="Napisz coś o transakcji..."
        )
        self.add_item(self.comment)

    async def on_submit(self, interaction: discord.Interaction):
        rating = self.rating_select.values[0]
        comment = self.comment.value.strip()

        # Zapamiętanie oceny, aby nie oceniać wielokrotnie
        key = (self.user.id, self.ticket_id)
        if key in user_ratings:
            await interaction.response.send_message(
                "❗ Już wystawiłeś ocenę dla tego zamówienia.",
                ephemeral=True
            )
            return

        user_ratings[key] = True

        # Przyszykowanie embedu z oceną do kanału z ocenami
        embed = discord.Embed(
            title=f"Ocena od {self.user.display_name} - {rating}⭐",
            description=f"**Użytkownik:** {self.user.mention}\n"
                        f"**Zamówienie:**\n"
                        f"```yaml\n"
                        f"Akcja: {self.order_info.get('action', '?')}\n"
                        f"Serwer: {self.order_info.get('server', '?')}\n"
                        f"Tryb: {self.order_info.get('mode', '?')}\n"
                        f"Itemy:\n" +
                        "\n".join(f"- {k}: {v}" for k, v in self.order_info.get('items', {}).items()) +
                        "\n```",
            color=discord.Color.gold()
        )
        if comment:
            embed.add_field(name="Komentarz", value=comment, inline=False)

        # Przy tym embedzie info jak ocenić jeszcze raz (też przycisk)
        view = RatingStartView()

        rating_channel = bot.get_channel(CHANNEL_RATINGS_ID)
        if rating_channel:
            await rating_channel.send(embed=embed, view=view)

        await interaction.response.send_message("✅ Dziękujemy za wystawienie oceny!", ephemeral=True)

class RatingStartView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Wystaw ocenę", style=discord.ButtonStyle.primary, custom_id="start_rating_button")
    async def start_rating(self, interaction: discord.Interaction, button: Button):
        # Pobranie danych zamówienia po ID kanału ticketu
        ticket_id = str(interaction.message.reference.channel_id) if interaction.message.reference else None
        if ticket_id is None or ticket_id not in orders_data:
            # Jeśli brak danych, to przypomnij info
            await interaction.response.send_message("❌ Nie znaleziono danych zamówienia do oceny.", ephemeral=True)
            return

        order_info = orders_data[ticket_id]
        modal = RatingModal(interaction.user, ticket_id, order_info)
        await interaction.response.send_modal(modal)

# --- Startowanie bota i komendy ---

@bot.event
async def on_ready():
    print(f"Bot zalogowany jako {bot.user}!")
    guild = bot.get_guild(GUILD_ID)

    # Rejestracja lokalnych komend slash
    try:
        synced = await bot.tree.sync(guild=guild)
        print(f"Zsynchronizowano {len(synced)} komend slash.")
    except Exception as e:
        print(f"Błąd synchronizacji komend: {e}")

    # Wysyłamy wiadomość startową z weryfikacją, jeśli jeszcze nie ma
    channel = bot.get_channel(CHANNEL_VERIFICATION_ID)
    messages = await channel.history(limit=10).flatten()
    if not any(m.author == bot.user and m.embeds for m in messages):
        view = VerificationView(ROLE_VERIFIED_ID)
        embed = discord.Embed(
            title="🔐 Weryfikacja użytkownika",
            description="Aby uzyskać dostęp do serwera, kliknij przycisk i rozwiąż krótkie zadanie matematyczne.",
            color=discord.Color.green()
        )
        await channel.send(embed=embed, view=view)

    # Wysyłamy wiadomość startową do tworzenia ticketów, jeśli jeszcze nie ma
    ticket_start_channel = bot.get_channel(CHANNEL_TICKET_START_ID)
    messages = await ticket_start_channel.history(limit=10).flatten()
    if not any(m.author == bot.user and m.content is None and m.embeds for m in messages):
        embed = discord.Embed(
            title="🎫 System ticketów",
            description="Kliknij przycisk, aby utworzyć ticket i rozpocząć proces kupna/sprzedaży.",
            color=discord.Color.blurple()
        )
        view = TicketStartView()
        await ticket_start_channel.send(embed=embed, view=view)

    # Wysyłamy startową wiadomość z ocenami na kanale ocen jeśli brak
    rating_channel = bot.get_channel(CHANNEL_RATINGS_ID)
    messages = await rating_channel.history(limit=10).flatten()
    if not any(m.author == bot.user and m.embeds for m in messages):
        embed = discord.Embed(
            title="⭐ Wystaw ocenę",
            description="Kliknij przycisk poniżej, aby wystawić ocenę dla zamówienia.",
            color=discord.Color.gold()
        )
        view = RatingStartView()
        await rating_channel.send(embed=embed, view=view)


# Slash command do wysyłania embedów (przykład z Twoich wcześniejszych prośb)
@bot.tree.command(name="wyslij", description="Wyślij wiadomość na kanał.")
@app_commands.guilds(discord.Object(id=GUILD_ID))
async def wyslij(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Przykładowa wiadomość",
        description="To jest wiadomość wysłana przez komendę slash.",
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=embed)

bot.run(os.getenv("TOKEN"))
