import os
import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.ui import View, Button, Select, Modal, TextInput
from datetime import datetime, timedelta

# ——— KONFIG —————————————————————————————
TOKEN = os.environ["DISCORD_TOKEN"]

CHANNEL_VERIFICATION_ID = 1373258480382771270
ROLE_VERIFIED_ID = 1373275307150278686
CHANNEL_TICKET_START_ID = 1373305137228939416
CATEGORY_TICKET_ID = 1373277957446959135
ROLE_TICKET_CLOSE = [1373275898375176232, 1379538984031752212]
CHANNEL_SUMMARY_ID = 1374479815914291240
CHANNEL_ARCHIVE_ID = 1374479815914291241

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

# ——— BOT I INTENTY ——————————————————————
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)
tree = bot.tree

def valid_amount(amount: str) -> bool:
    amt = amount.lower().replace("k", "")
    return amt.replace(",", "").replace(".", "").isdigit()

# ——— WIDOKI I MODALE —————————————————————————————
class VerificationView(View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="Zweryfikuj się", style=discord.ButtonStyle.green, custom_id="verify_button")
    async def verify_button(self, interaction: discord.Interaction, button: Button):
        role = interaction.guild.get_role(ROLE_VERIFIED_ID)
        if not role:
            return await interaction.response.send_message("❌ Nie znaleziono roli.", ephemeral=True)
        try:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("✅ Zostałeś zweryfikowany!", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("🚫 Bot nie ma uprawnień.", ephemeral=True)

class TicketStartView(View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="Utwórz ticket", style=discord.ButtonStyle.blurple, custom_id="create_ticket_button")
    async def create_ticket(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        category = guild.get_channel(CATEGORY_TICKET_ID)
        if not isinstance(category, discord.CategoryChannel):
            return await interaction.response.send_message("❌ Brak kategorii ticketów.", ephemeral=True)
        existing = discord.utils.get(guild.channels, name=f"ticket-{interaction.user.id}")
        if existing:
            return await interaction.response.send_message(f"❗Masz już ticket: {existing.mention}", ephemeral=True)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }
        for rid in ROLE_TICKET_CLOSE:
            role = guild.get_role(rid)
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
        channel = await guild.create_text_channel(
            name=f"ticket-{interaction.user.id}",
            category=category,
            overwrites=overwrites,
            reason=f"Ticket od {interaction.user}"
        )
        await interaction.response.send_message(f"✅ Stworzono ticket: {channel.mention}", ephemeral=True)
        await channel.send(f"Witaj {interaction.user.mention}! Wybierz sprzedajesz czy kupujesz.",
                           view=SellBuySelectView(interaction.user))

class SellBuySelectView(View):
    def __init__(self, user): super().__init__(timeout=300); self.user = user
    @discord.ui.select(placeholder="Sprzedaj / Kup", custom_id="sellbuy_select",
                       options=[discord.SelectOption(label="Sprzedaj", value="sprzedaj"),
                                discord.SelectOption(label="Kup", value="kup")])
    async def cb(self, select, interaction: discord.Interaction):
        if interaction.user != self.user:
            return await interaction.response.send_message("❌ To nie Twój ticket.", ephemeral=True)
        view = ServerSelectView(self.user, select.values[0])
        await interaction.response.edit_message(content=f"**{select.values[0].capitalize()}** – teraz wybierz serwer:", view=view)

class ServerSelectView(View):
    def __init__(self, user, action):
        super().__init__(timeout=300)
        self.user, self.action = user, action
        self.add_item(Select(placeholder="Wybierz serwer", custom_id="server_select",
                             options=[discord.SelectOption(label=s) for s in DATA]))
        self.add_item(Button(label="Cofnij", style=discord.ButtonStyle.gray, custom_id="back_to_start"))
    async def interaction_check(self, interaction): return interaction.user == self.user
    @discord.ui.button(label="Cofnij", style=discord.ButtonStyle.gray, custom_id="back_to_start")
    async def back(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(content="Sprzedaj lub Kup:", view=SellBuySelectView(self.user))

class ModeSelectView(View):
    def __init__(self, user, action, server):
        super().__init__(timeout=300)
        self.user, self.action, self.server = user, action, server
        self.add_item(Select(placeholder="Wybierz tryb", custom_id="mode_select",
                             options=[discord.SelectOption(label=m) for m in DATA[server]]))
        self.add_item(Button(label="Cofnij", style=discord.ButtonStyle.gray, custom_id="back_to_server"))
    async def interaction_check(self, interaction): return interaction.user == self.user
    @discord.ui.button(label="Cofnij", style=discord.ButtonStyle.gray, custom_id="back_to_server")
    async def back(self, interaction, button: Button):
        await interaction.response.edit_message(content="Wybierz serwer:", view=ServerSelectView(self.user, self.action))

class ItemSelectView(View):
    def __init__(self, user, action, server, mode):
        super().__init__(timeout=300)
        self.user, self.action, self.server, self.mode = user, action, server, mode
        self.selected_items = {}
        self.add_item(Select(placeholder="Wybierz item", custom_id="item_select",
                             options=[discord.SelectOption(label=i) for i in DATA[server][mode]]))
        self.add_item(Button(label="Zakończ", style=discord.ButtonStyle.green, custom_id="finish"))
        self.add_item(Button(label="Cofnij", style=discord.ButtonStyle.gray, custom_id="back_to_mode"))
    async def interaction_check(self, interaction): return interaction.user == self.user
    @discord.ui.button(label="Zakończ", style=discord.ButtonStyle.green, custom_id="finish")
    async def finish(self, interaction: discord.Interaction, button: Button):
        if not self.selected_items:
            return await interaction.response.send_message("❗Nic nie wybrałeś.", ephemeral=True)
        embed = discord.Embed(title="Podsumowanie ticketa", color=discord.Color.blue())
        embed.add_field(name="Użytkownik", value=self.user.mention, inline=False)
        embed.add_field(name="Akcja", value=self.action.capitalize(), inline=True)
        embed.add_field(name="Serwer", value=self.server, inline=True)
        embed.add_field(name="Tryb", value=self.mode, inline=True)
        embed.add_field(name="Itemy", value="\n".join(f"- **{k}**: {v}" for k,v in self.selected_items.items()), inline=False)
        await interaction.message.delete()
        await interaction.response.send_message(embed=embed, view=None)
        ch = bot.get_channel(CHANNEL_SUMMARY_ID)
        if ch: await ch.send(embed=embed)
    @discord.ui.button(label="Cofnij", style=discord.ButtonStyle.gray, custom_id="back_to_mode")
    async def back(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(content=f"Tryb **{self.mode}** – wybierz item:", view=ModeSelectView(self.user, self.action, self.server))
    @discord.ui.select(custom_id="item_select")
    async def select_item(self, select: Select, interaction: discord.Interaction):
        modal = AmountModal(self, select.values[0], select.values[0]=="kasa")
        await interaction.response.send_modal(modal)

class AmountModal(Modal):
    def __init__(self, parent, item, is_money):
        super().__init__(title=f"Wpisz {'kwotę' if is_money else 'ilość'} dla {item}")
        self.parent, self.item = parent, item
        self.add_item(TextInput(label="Wartość:", placeholder="Np. 50 lub 100k", max_length=20))
    async def on_submit(self, interaction: discord.Interaction):
        amt = self.children[0].value.strip()
        if not valid_amount(amt):
            return await interaction.response.send_message("❗Błędna wartość.", ephemeral=True)
        self.parent.selected_items[self.item] = amt
        await interaction.response.send_message(f"Dodano **{self.item}**: **{amt}**", ephemeral=True)

class CloseTicketView(View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="Zamknij ticket", style=discord.ButtonStyle.red, custom_id="close_ticket_button")
    async def close(self, interaction: discord.Interaction, button: Button):
        if not any(r.id in ROLE_TICKET_CLOSE for r in interaction.user.roles):
            return await interaction.response.send_message("❌Brak uprawnień.", ephemeral=True)
        now = datetime.utcnow().isoformat()
        ch = interaction.channel
        arc = bot.get_channel(CHANNEL_ARCHIVE_ID)
        if arc:
            await arc.send(f"🎫 `{ch.name}` zamknięty przez {interaction.user.mention} o {now} UTC")
        await ch.delete(reason=f"Zamknięty przez {interaction.user}")

# ——— AUTO‑ZAMYKANIE —————————————————
@tasks.loop(hours=1)
async def auto_close():
    now = datetime.utcnow()
    for g in bot.guilds:
        cat = g.get_channel(CATEGORY_TICKET_ID)
        if not isinstance(cat, discord.CategoryChannel): continue
        for ch in cat.text_channels:
            if now - ch.created_at > timedelta(hours=24):
                await ch.delete(reason="Automatycznie (24h nieaktywne)")
                arc = bot.get_channel(CHANNEL_ARCHIVE_ID)
                if arc:
                    await arc.send(f"🎫 Auto‑zamknięto `{ch.name}` UTC {now.isoformat()}")

@auto_close.before_loop
async def before_auto(): await bot.wait_until_ready()

# ——— SLASH COMMANDS —————————————————
@tree.command(name="verify", description="Wyślij przycisk weryfikacji")
async def slash_verify(interaction: discord.Interaction):
    ch = bot.get_channel(CHANNEL_VERIFICATION_ID)
    if ch:
        await ch.send("🔒 Weryfikacja", view=VerificationView())
        await interaction.response.send_message("✅ Wysłano przycisk weryfikacji.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Kanał weryfikacji nie znaleziony.", ephemeral=True)

@tree.command(name="ticketbutton", description="Wyślij przycisk tworzenia ticketu")
async def slash_ticket(interaction: discord.Interaction):
    ch = bot.get_channel(CHANNEL_TICKET_START_ID)
    if ch:
        await ch.send("🎫 Utwórz ticket", view=TicketStartView())
        await interaction.response.send_message("✅ Wysłano przycisk ticketu.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Kanał startu ticketu nie znaleziony.", ephemeral=True)

# ——— READY I START —————————————————
@bot.event
async def on_ready():
    print(f"✅ Zalogowano jako {bot.user} (ID: {bot.user.id})")
    bot.add_view(VerificationView())
    bot.add_view(TicketStartView())
    auto_close.start()
    await tree.sync()
    # Automatyczne wysłanie przycisków
    chv = bot.get_channel(CHANNEL_VERIFICATION_ID)
    if chv: await chv.send("🔒 Weryfikacja", view=VerificationView())
    cht = bot.get_channel(CHANNEL_TICKET_START_ID)
    if cht: await cht.send("🎫 Utwórz ticket", view=TicketStartView())

bot.run(TOKEN)
