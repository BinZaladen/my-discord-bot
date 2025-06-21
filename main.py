import os
import discord
import random
from discord.ext import commands
from discord.ui import View, Button, Select, Modal, TextInput

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ID kanałów, kategorii i ról
CHANNEL_VERIFICATION_ID = 1373258480382771270
ROLE_VERIFIED_ID = 1373275307150278686

CHANNEL_TICKET_START_ID = 1373305137228939416
CATEGORY_TICKET_ID = 1373277957446959135

ROLE_TICKET_CLOSE = [1373275898375176232, 1379538984031752212]

CHANNEL_SUMMARY_ID = 1374479815914291240

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
        a = random.randint(1, 10)
        b = random.randint(1, 10)
        correct_answer = str(a + b)

        class VerificationModal(Modal, title="Weryfikacja matematyczna"):
            answer = TextInput(label=f"Ile to jest {a} + {b}?", placeholder="Wpisz wynik...", required=True)

            async def on_submit(self, modal_interaction: discord.Interaction):
                if self.answer.value.strip() == correct_answer:
                    role = discord.utils.get(modal_interaction.guild.roles, id=self.role_id)
                    if not role:
                        await modal_interaction.response.send_message("❌ Nie znaleziono roli.", ephemeral=True)
                        return
                    await modal_interaction.user.add_roles(role)
                    await modal_interaction.response.send_message("✅ Zostałeś zweryfikowany!", ephemeral=True)
                else:
                    await modal_interaction.response.send_message("❌ Niepoprawna odpowiedź. Spróbuj ponownie.", ephemeral=True)

        await interaction.response.send_modal(VerificationModal())

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
            await summary_channel.send(embed=embed)

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


# --- on_ready ---
@bot.event
async def on_ready():
    print(f'Zalogowano jako {bot.user} (ID: {bot.user.id})')
    bot.add_view(VerificationView(ROLE_VERIFIED_ID))
    bot.add_view(TicketStartView())

    channel_ver = bot.get_channel(CHANNEL_VERIFICATION_ID)
    if channel_ver:
        async for message in channel_ver.history(limit=100):
            if message.author == bot.user:
                await message.delete()
        embed_ver = discord.Embed(
            title="🔐 Weryfikacja na 𝟰𝟰𝟰 𝐒𝐇𝐎𝐏",
            description=(
                "Aby uzyskać dostęp do serwera, rozwiąż proste równanie matematyczne.\n"
                "Kliknij przycisk poniżej, aby rozpocząć weryfikację."
            ),
            color=discord.Color.green()
        )
        await channel_ver.send(embed=embed_ver, view=VerificationView(ROLE_VERIFIED_ID))

    channel_ticket_start = bot.get_channel(CHANNEL_TICKET_START_ID)
    if channel_ticket_start:
        async for message in channel_ticket_start.history(limit=100):
            if message.author == bot.user:
                await message.delete()
        embed_ticket_start = discord.Embed(
            title="🎫 Centrum Pomocy 𝟰𝟰𝟰 𝐒𝐇𝐎𝐏",
            description="Kliknij przycisk poniżej, aby utworzyć ticket i kupić/sprzedać przedmioty w grze Minecraft.",
            color=discord.Color.blurple()
        )
        await channel_ticket_start.send(embed=embed_ticket_start, view=TicketStartView())

# --- RUN ---
bot.run(os.getenv("DISCORD_TOKEN"))
