@bot.event
async def on_ready():
    print(f"✅ Zalogowano jako {bot.user}")

    # Funkcja pomocnicza do pobierania emoji lub tekstu zastępczego
    def get_emoji(name, fallback="❓"):
        emoji = bot.get_emoji({
            "Klata": 1374793644246306866,
            "Buda": 1375488639496093828,
            "Buty": 1374796797222064230,
            "Elytra": 1374797373406187580,
            "Excalibur": 1374785662191927416,
            "Kilof": 1374795407493959751,
            "ANA2": 1374799017359314944,
            "KlataMeduzy": 1375487632531918875,
            "LoveSwap": 1375490111801790464,
            "Miecz": 1374791139462352906,
            "MieczZajeczy": 1375486003891929088,
            "Sakiewka": 1374799829120716892,
            "Shulker": 1374795916531335271,
            "Totem": 1374788635211206757,
        }.get(name, 0))
        return str(emoji) if emoji else fallback

    messages = [
        (1373266589310517338, f"""🛒 Oferta itemów na sprzedaż
{get_emoji("Elytra")} Elytra — 12zł
{get_emoji("Buty")} Buty flasha — 5zł
{get_emoji("Miecz")} Miecz 6 — 3zł
{get_emoji("Shulker")} Shulker s2 — 7zł
{get_emoji("Shulker")} Shulker totemów — 6zł"""),

        (1373267159576481842, f"""🛒 Oferta itemów na sprzedaż
{get_emoji("Klata")} Set 25 — 30zł
{get_emoji("Miecz")} Miecz 25 — 25zł
{get_emoji("Kilof")} Kilof 25 — 10zł
💸 1mln$ — 18zł"""),

        (1373268875407396914, f"""🛒 Oferta itemów na sprzedaż
💵 4,5k$ — 1zł
💸 50k$ — 12zł
💸 550k$ — 130zł
{get_emoji("ANA2")} Anarchiczny set 2 — 28zł
{get_emoji("Klata")} Anarchiczny set 1 — 9zł

⚔️ Miecze:
{get_emoji("Miecz")} Anarchiczny miecz — 3zł

🎉 Eventówki:
{get_emoji("MieczZajeczy")} Zajęczy miecz — 65zł
{get_emoji("Totem")} Totem ułaskawienia — 630zł
{get_emoji("Excalibur")} Excalibur — 370zł"""),

        (1373270295556788285, f"""🛒 Oferta itemów na sprzedaż
💵 50k$ — 1zł
💸 1mln$ — 33zł

🎉 Eventówki:
{get_emoji("Excalibur")} Excalibur — 111zł
{get_emoji("Totem")} Totem ułaskawienia — 270zł
{get_emoji("Sakiewka")} Sakiewka — 50zł"""),

        (1373273108093337640, f"""🛒 Oferta itemów na sprzedaż
💸 10mld$ — 2zł
{get_emoji("Miecz")} Miecz 35 — 65zł
{get_emoji("Klata")} Set 35 — 90zł"""),

        (1374380939970347019, f"""🛒 Oferta itemów na sprzedaż
💵 15k$ — 1zł
{get_emoji("Buda")} Buda — 30zł
{get_emoji("LoveSwap")} Love swap — 100zł
{get_emoji("KlataMeduzy")} Klata meduzy — 140zł"""),
    ]

    for channel_id, text in messages:
        channel = bot.get_channel(channel_id)
        if channel:
            embed = discord.Embed(description=text, color=discord.Color.orange())
            await channel.send(embed=embed)
