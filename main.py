@bot.event
async def on_ready():
    print(f"✅ Zalogowano jako {bot.user}")

    # Mapa emoji
    emoji_map = {
        "Klata": bot.get_emoji(1374793644246306866),
        "Buda": bot.get_emoji(1375488639496093828),
        "Buty": bot.get_emoji(1374796797222064230),
        "Elytra": bot.get_emoji(1374797373406187580),
        "Excalibur": bot.get_emoji(1374785662191927416),
        "Kilof": bot.get_emoji(1374795407493959751),
        "ANA2": bot.get_emoji(1374799017359314944),
        "KlataMeduzy": bot.get_emoji(1375487632531918875),
        "LoveSwap": bot.get_emoji(1375490111801790464),
        "Miecz": bot.get_emoji(1374791139462352906),
        "MieczZajeczy": bot.get_emoji(1375486003891929088),
        "Sakiewka": bot.get_emoji(1374799829120716892),
        "Shulker": bot.get_emoji(1374795916531335271),
        "Totem": bot.get_emoji(1374788635211206757),
    }

    # Lista wiadomości
    messages = [
        (1373266589310517338, f"""🛒 Oferta itemów na sprzedaż
{emoji_map['Elytra']} Elytra — 12zł
{emoji_map['Buty']} Buty flasha — 5zł
{emoji_map['Miecz']} Miecz 6 — 3zł
{emoji_map['Shulker']} Shulker s2 — 7zł
{emoji_map['Shulker']} Shulker totemów — 6zł"""),

        (1373267159576481842, f"""🛒 Oferta itemów na sprzedaż
{emoji_map['Klata']} Set 25 — 30zł
{emoji_map['Miecz']} Miecz 25 — 25zł
{emoji_map['Kilof']} Kilof 25 — 10zł
💸 1mln$ — 18zł"""),

        (1373268875407396914, f"""🛒 Oferta itemów na sprzedaż
💵 4,5k$ — 1zł
💸 50k$ — 12zł
💸 550k$ — 130zł
{emoji_map['ANA2']} Anarchiczny set 2 — 28zł
{emoji_map['Klata']} Anarchiczny set 1 — 9zł

⚔️ Miecze:
{emoji_map['Miecz']} Anarchiczny miecz — 3zł

🎉 Eventówki:
{emoji_map['MieczZajeczy']} Zajęczy miecz — 65zł
{emoji_map['Totem']} Totem ułaskawienia — 630zł
{emoji_map['Excalibur']} Excalibur — 370zł"""),

        (1373270295556788285, f"""🛒 Oferta itemów na sprzedaż
💵 50k$ — 1zł
💸 1mln$ — 33zł

🎉 Eventówki:
{emoji_map['Excalibur']} Excalibur — 111zł
{emoji_map['Totem']} Totem ułaskawienia — 270zł
{emoji_map['Sakiewka']} Sakiewka — 50zł"""),

        (1373273108093337640, f"""🛒 Oferta itemów na sprzedaż
💸 10mld$ — 2zł
{emoji_map['Miecz']} Miecz 35 — 65zł
{emoji_map['Klata']} Set 35 — 90zł"""),

        (1374380939970347019, f"""🛒 Oferta itemów na sprzedaż
💵 15k$ — 1zł
{emoji_map['Buda']} Buda — 30zł
{emoji_map['LoveSwap']} Love swap — 100zł
{emoji_map['KlataMeduzy']} Klata meduzy — 140zł"""),
    ]

    for channel_id, text in messages:
        channel = bot.get_channel(channel_id)
        if channel:
            embed = discord.Embed(description=text, color=discord.Color.orange())
            await channel.send(embed=embed)
