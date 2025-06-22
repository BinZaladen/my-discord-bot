import os
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button, Select, Modal, TextInput
import asyncio
import random
import json

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

LOG_FILE = "/mnt/data/tickets_log.json"  # Ścieżka do pliku z logami ticketa

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

# --- PAMIĘĆ OCEN: (user_id, ticket_channel_id) -> True jeśli ocenił ---
user_ratings = {}

def save_ticket_log(ticket_data):
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = []

    data.append(ticket_data)

    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def load_ticket_logs():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        return []

def get_user_unrated_ticket(user_id):
    logs = load_ticket_logs()
    # Znajdź pierwszy (najstarszy) ticket tego usera, którego jeszcze nie ocenił
    for ticket in logs:
        key = (user_id, ticket["ticket_channel_id"])
        if ticket["user_id"] == user_id and not user_ratings.get(key, False):
            return ticket
    return None


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
            view = RealizeOrderView(member, ticket_id=str(interaction.channel.id))
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


# --- Realize Order Button + logowanie ticketa ---
class RealizeOrderView(View):
    def __init__(self, user: discord.Member, ticket_id: str):
        super().__init__(timeout=None)
        self.user = user
        self.ticket_id = ticket_id

    @discord.ui.button(label="✅ Zrealizuj", style=discord.ButtonStyle.green, custom_id="realize_order_button")
    async def realize_button(self, interaction: discord.Interaction, button: Button):
        role = discord.utils.get(interaction.guild.roles, id=ROLE_CUSTOMER_ID)
        if not role:
            await interaction.response.send_message("❌ Nie znaleziono roli `customer`.", ephemeral=True)
            return

        # Pobierz embed z wiadomości (dane ticketa)
        if not interaction.message.embeds:
            await interaction.response.send_message("❌ Nie znaleziono danych ticketa.", ephemeral=True)
            return
        embed = interaction.message.embeds[0]

        # Parsuj dane z embedu (zakładam, że pola są w takiej kolejności jak wysyłasz)
        try:
            ticket_data = {
                "user_id": self.user.id,
                "username": str(self.user),
                "ticket_channel_id": self.ticket_id,
                "timestamp": str(interaction.message.created_at),
                "action": embed.fields[1].value,  # Akcja
                "server": embed.fields[2].value,  # Serwer
                "mode": embed.fields[3].value,    # Tryb
                "items": embed.fields[4].value    # Itemy (tekst)
            }
        except Exception as e:
            await interaction.response.send_message(f"❌ Błąd podczas parsowania danych: {e}", ephemeral=True)
            return

        # Zapisz ticket do logów
        save_ticket_log(ticket_data)

        # Dodaj rolę customer
        try:
            await self.user.add_roles(role)
        except discord.Forbidden:
            await interaction.response.send_message("❌ Bot nie ma uprawnień do nadania roli.", ephemeral=True)
            return

        # Usuń wiadomość z logiem
        await interaction.message.delete()
        await interaction.response.send_message(f"✅ Zamówienie użytkownika {self.user.mention} zostało oznaczone jako zrealizowane.", ephemeral=True)


# --- Ocena bez wyboru ticketu, bot bierze najstarszy nieoceniony ---
class RatingModal(Modal, title="Wystaw ocenę"):
    def __init__(self, user):
        super().__init__()
        self.user = user

        self.stars = Select(
            placeholder="Wybierz ilość gwiazdek",
            options=[discord.SelectOption(label=f"{i} ★", value=str(i)) for i in range(1, 6)],
            custom_id="stars_select"
        )
        self.add_item(self.stars)

        self.comment = TextInput(label="Komentarz (opcjonalny)", required=False, max_length=200)
        self.add_item(self.comment)

    async def on_submit(self, interaction: discord.Interaction):
        rating = int(self.stars.values[0])
        comment = self.comment.value or "Brak komentarza"

        ticket = get_user_unrated_ticket(self.user.id)
        if ticket is None:
            await interaction.response.send_message("❌ Nie masz żadnych zamówień do oceny.", ephemeral=True)
            return

        key = (self.user.id, ticket["ticket_channel_id"])
        if user_ratings.get(key, False):
            await interaction.response.send_message("❌ Już oceniłeś to zamówienie.", ephemeral=True)
            return

        # Zapisz ocenę (flaga)
        user_ratings[key] = True

        stars_text = "★" * rating + "☆" * (5 - rating)
        embed = discord.Embed(title=f"Ocena zamówienia od {self.user}", color=discord.Color.gold())
        embed.add_field(name="Użytkownik", value=self.user.mention, inline=True)
        embed.add_field(name="Ocena", value=stars_text, inline=True)
        embed.add_field(name="Komentarz", value=comment, inline=False)

        # Podkreślenie kto i co kupił - używamy danych z ticketa
        embed.add_field(name="Akcja", value=ticket["action"], inline=True)
        embed.add_field(name="Serwer", value=ticket["server"], inline=True)
        embed.add_field(name="Tryb", value=ticket["mode"], inline=True)
        embed.add_field(name="Itemy", value=ticket["items"], inline=False)

        embed.set_footer(text=f"Ticket ID: {ticket['ticket_channel_id']} | Zamówienie z: {ticket['timestamp']}")

        channel = bot.get_channel(CHANNEL_RATINGS_ID)
        if channel:
            # Po wysłaniu embedu dodaj przycisk do ponownej oceny (opcjonalnie)
            view = RatingView()
            await channel.send(embed=embed, view=view)

        await interaction.response.send_message("✅ Dziękujemy za wystawienie oceny!", ephemeral=True)


class RatingView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Wystaw kolejną ocenę", style=discord.ButtonStyle.primary, custom_id="rate_again_button")
    async def rate_again(self, interaction: discord.Interaction, button: Button):
        modal = RatingModal(interaction.user)
        await interaction.response.send_modal(modal)


class RatingButtonView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Wystaw ocenę", style=discord.ButtonStyle.success, custom_id="rate_button")
    async def rate_button(self, interaction: discord.Interaction, button: Button):
        modal = RatingModal(interaction.user)
        await interaction.response.send_modal(modal)


# --- Komenda do wysłania wiadomości ocen z przyciskiem ---
@bot.tree.command(name="wyslij_oceny", description="Wyślij wiadomość startową do ocen (tylko admin).")
@app_commands.checks.has_permissions(administrator=True)
async def wyslij_oceny(interaction: discord.Interaction):
    channel = bot.get_channel(CHANNEL_RATINGS_ID)
    if not channel:
        await interaction.response.send_message("❌ Nie znaleziono kanału ocen.", ephemeral=True)
        return

    embed = discord.Embed(
        title="Wystaw ocenę swoim zamówieniom",
        description="Kliknij przycisk poniżej, aby wystawić ocenę zamówienia. Możesz ocenić swoje ostatnie zamówienia.",
        color=discord.Color.green()
    )
    view = RatingButtonView()
    await channel.send(embed=embed, view=view)
    await interaction.response.send_message("✅ Wiadomość startowa do ocen wysłana.", ephemeral=True)


# --- Event on_ready ---
@bot.event
async def on_ready():
    print(f"Zalogowano jako {bot.user} (ID: {bot.user.id})")
    try:
        guild = bot.get_guild(GUILD_ID)
        await bot.tree.sync(guild=guild)
        print("Slash commands synced.")
    except Exception as e:
        print(f"Błąd podczas syncu komend slash: {e}")

    # Wyślij wiadomość startową do ocen jeśli nie ma (można odkomentować, jeśli chcesz wysłać automatycznie)
    # channel = bot.get_channel(CHANNEL_RATINGS_ID)
    # if channel:
    #     embed = discord.Embed(
    #         title="Wystaw ocenę swoim zamówieniom",
    #         description="Kliknij przycisk poniżej, aby wystawić ocenę zamówienia. Możesz ocenić swoje ostatnie zamówienia.",
    #         color=discord.Color.green()
    #     )
    #     view = RatingButtonView()
    #     await channel.send(embed=embed, view=view)


# --- Tutaj dodaj resztę Twojego kodu z ticketami, weryfikacją itd.
# Poniżej dodajemy widoki i funkcje tworzenia ticketów itp. - tak jak wyżej

# --- Uruchomienie bota ---
bot.run(os.getenv("DISCORD_TOKEN"))
