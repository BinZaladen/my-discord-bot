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

# ID kanałów, kategorii i ról (podmień na swoje)
CHANNEL_VERIFICATION_ID = 1373258480382771270
ROLE_VERIFIED_ID = 1373275307150278686

CHANNEL_TICKET_START_ID = 1373305137228939416
CATEGORY_TICKET_ID = 1373277957446959135

ROLE_TICKET_CLOSE = [1373275898375176232, 1379538984031752212]

CHANNEL_SUMMARY_ID = 1374479815914291240
ROLE_CUSTOMER_ID = 1374099985288921088

CHANNEL_RATINGS_ID = 1375528888586731762

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

user_ratings = {}  # (user_id, ticket_id) -> bool
orders_data = {}   # ticket_channel_id -> order data (dict)

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

        # Zapisz dane zamówienia globalnie do orders_data pod ID kanału ticketu
        orders_data[str(interaction.channel.id)] = {
            "user_id": self.user.id,
            "action": self.action,
            "server": self.server,
            "mode": self.mode,
            "items": self.selected_items.copy()
        }

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
            await interaction.response.send_message("❌ Nie znaleziono roli `customer`.", ephemeral=True)
            return

        try:
            await self.user.add_roles(role)
            # Usuwamy wiadomość z kanału podsumowania (logów)
            await interaction.message.delete()

            await interaction.response.send_message(f"✅ Zamówienie użytkownika {self.user.mention} zostało oznaczone jako zrealizowane.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ Bot nie ma uprawnień do nadania roli.", ephemeral=True)

# --- Oceny ---
class RateButton(Button):
    def __init__(self, ticket_id: str):
        super().__init__(label="Wystaw ocenę", style=discord.ButtonStyle.primary, custom_id=f"rate_{ticket_id}")

    async def callback(self, interaction: discord.Interaction):
        user = interaction.user
        ticket_id = self.custom_id.split("_", 1)[1]

        # Sprawdź czy user ma rolę customer
        if not any(role.id == ROLE_CUSTOMER_ID for role in user.roles):
            await interaction.response.send_message("❌ Musisz mieć rolę klienta, aby wystawić ocenę.", ephemeral=True)
            return

        # Sprawdź, czy user już ocenił ten ticket
        if user_ratings.get((user.id, ticket_id), False):
            await interaction.response.send_message("❌ Już wystawiłeś ocenę dla tego ticketu.", ephemeral=True)
            return

        await interaction.response.send_modal(RatingModal(user, ticket_id))

class RateView(View):
    def __init__(self, ticket_id):
        super().__init__(timeout=None)
        self.add_item(RateButton(ticket_id))

class RatingModal(Modal, title="Wystaw ocenę"):
    def __init__(self, user, ticket_id):
        super().__init__()
        self.user = user
        self.ticket_id = ticket_id

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

        # Zapisz ocenę
        user_ratings[(self.user.id, self.ticket_id)] = True

        # Pobierz dane zamówienia do podsumowania
        order = orders_data.get(self.ticket_id, None)
        if order:
            user_mention = f"<@{order['user_id']}>"
            action = order['action'].capitalize()
            server = order['server']
            mode = order['mode']
            items_str = "\n".join(f"- **{it}**: {qty}" for it, qty in order['items'].items())
        else:
            user_mention = "Nieznany użytkownik"
            action = "Nieznana akcja"
            server = "Nieznany serwer"
            mode = "Nieznany tryb"
            items_str = "Brak danych"

        stars_text = "★" * rating + "☆" * (5 - rating)
        text = (
            f"**Ocena od {self.user.mention}**\n"
            f"⭐ {stars_text} ({rating}/5)\n"
            f"💬 Komentarz: {comment}\n\n"
            f"**Dane zamówienia:**\n"
            f"Użytkownik: {user_mention}\n"
            f"Akcja: {action}\n"
            f"Serwer: {server}\n"
            f"Tryb: {mode}\n"
            f"Itemy:\n{items_str}"
        )

        ratings_channel = bot.get_channel(CHANNEL_RATINGS_ID)
        if ratings_channel:
            await ratings_channel.send(text, view=RateView(self.ticket_id))

        await interaction.response.send_message("✅ Dziękujemy za wystawienie oceny!", ephemeral=True)

# --- Slash command do wysłania wiadomości weryfikacji lub ticket start ---
class SendMessageModal(Modal, title="Wiadomość do wysłania"):
    def __init__(self, channel_id: int):
        super().__init__()
        self.channel_id = channel_id
        self.message_input = TextInput(label="Treść wiadomości", style=discord.TextStyle.paragraph)
        self.add_item(self.message_input)

    async def on_submit(self, interaction: discord.Interaction):
        channel = bot.get_channel(self.channel_id)
        if not channel:
            await interaction.response.send_message("❌ Nie znaleziono kanału.", ephemeral=True)
            return
        try:
            await channel.send(self.message_input.value)
            await interaction.response.send_message("✅ Wiadomość wysłana.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Błąd: {e}", ephemeral=True)

@bot.tree.command(name="wyslij", description="Wyślij wiadomość na wybrany kanał")
@app_commands.describe(channel="Kanał, do którego wyślesz wiadomość")
async def wyslij(interaction: discord.Interaction, channel: discord.TextChannel):
    modal = SendMessageModal(channel.id)
    await interaction.response.send_modal(modal)

# --- ON READY ---
@bot.event
async def on_ready():
    print(f"Zalogowano jako {bot.user} (ID: {bot.user.id})")

    # Wysyłamy wiadomość weryfikacyjną na kanał weryfikacji
    channel_ver = bot.get_channel(CHANNEL_VERIFICATION_ID)
    if channel_ver:
        try:
            # Czy jest już taka wiadomość (usuń własne wiadomości bota, żeby nie spamować)
            async for msg in channel_ver.history(limit=50):
                if msg.author == bot.user and msg.embeds:
                    await msg.delete()
            embed_ver = discord.Embed(
                title="🔒 𝟰𝟰𝟰 𝐒𝐇𝐎𝐏 - Weryfikacja",
                description="Kliknij przycisk poniżej i rozwiąż proste zadanie matematyczne, aby uzyskać dostęp do serwera.",
                color=discord.Color.green()
            )
            await channel_ver.send(embed=embed_ver, view=VerificationView(ROLE_VERIFIED_ID))
            print("Wiadomość weryfikacyjna wysłana.")
        except Exception as e:
            print(f"Błąd przy wysyłaniu weryfikacji: {e}")
    else:
        print("Nie znaleziono kanału weryfikacji.")

    # Wysyłamy wiadomość startową ticketów
    channel_ticket = bot.get_channel(CHANNEL_TICKET_START_ID)
    if channel_ticket:
        try:
            async for msg in channel_ticket.history(limit=50):
                if msg.author == bot.user and msg.embeds:
                    await msg.delete()
            embed_ticket = discord.Embed(
                title="🎫 𝟰𝟰𝟰 𝐒𝐇𝐎𝐏 - Ticket System",
                description="Kliknij przycisk poniżej, aby utworzyć nowy ticket.",
                color=discord.Color.blue()
            )
            await channel_ticket.send(embed=embed_ticket, view=TicketStartView())
            print("Wiadomość ticketów wysłana.")
        except Exception as e:
            print(f"Błąd przy wysyłaniu ticketów: {e}")
    else:
        print("Nie znaleziono kanału ticketów.")

    # Synchronizacja slash komend
    try:
        synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        print(f"Slash commands zsynchronizowane: {len(synced)}")
    except Exception as e:
        print(f"Błąd synchronizacji slash commands: {e}")

# --- RUN ---
if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        print("❌ Nie znaleziono tokena w zmiennej środowiskowej DISCORD_TOKEN.")
    else:
        bot.run(TOKEN)
