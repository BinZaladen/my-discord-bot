import os
import discord
from discord.ext import commands
from discord.ui import View, Button

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ID kanałów i ról
CHANNEL_VERIFICATION_ID = 1373258480382771270
ROLE_VERIFIED_ID = 1373275307150278686

CHANNEL_TICKET_ID = 1373305137228939416
CATEGORY_TICKET_ID = 1373277957446959135

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

        # Sprawdź, czy użytkownik już ma otwarty ticket (kanał z nazwą ticket-<user_id>)
        existing_channel = discord.utils.get(guild.channels, name=f"ticket-{interaction.user.id}")
        if existing_channel:
            await interaction.response.send_message(f"❗ Masz już otwarty ticket: {existing_channel.mention}", ephemeral=True)
            return

        # Tworzymy kanał ticketowy w kategorii
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            # Możesz dodać tutaj role moderatorów/adminów z pełnym dostępem np:
            # guild.get_role(ROLE_ADMIN_ID): discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        ticket_channel = await guild.create_text_channel(
            name=f"ticket-{interaction.user.id}",
            category=category,
            overwrites=overwrites,
            reason=f"Ticket utworzony przez {interaction.user}"
        )

        await interaction.response.send_message(f"✅ Ticket utworzony: {ticket_channel.mention}", ephemeral=True)
        await ticket_channel.send(f"Witaj {interaction.user.mention}! To jest twój ticket. Opisz swój problem, a ktoś z zespołu wkrótce pomoże.")

@bot.event
async def on_ready():
    print(f'Zalogowano jako {bot.user} (ID: {bot.user.id})')

    # Dodajemy widoki persistent (przyciski działają po restarcie bota)
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
