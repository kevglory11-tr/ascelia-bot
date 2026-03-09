"""cogs/coin_market.py — /market komutu."""

import discord
from discord.ext import commands
from discord import app_commands

import database
from utils.logger import setup_logger
from config.coin_settings import MARKET_URUNLER

log = setup_logger("coin_market")

M2B    = "<:m2bcoin:1480481551337783437>"
OK     = "<a:check:1478394670856933429>"
FAIL   = "<a:redx:1478394672012034088>"
SHOP   = "<a:genel:1478389856874004592>"


class MarketSelect(discord.ui.Select):
    def __init__(self, discord_id: int, bakiye: int):
        self.discord_id = discord_id
        options = []
        for urun in MARKET_URUNLER:
            durum = "✦" if bakiye >= urun["fiyat"] else "🔒"
            options.append(discord.SelectOption(
                label=urun["isim"],
                description=f"{durum}  {urun['fiyat']:,} M2B Coin",
                value=urun["id"],
                emoji="🎟️",
            ))
        super().__init__(
            placeholder="🎟️ Satın almak istediğin kuponu seç...",
            options=options,
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.discord_id:
            await interaction.response.send_message(
                f"{FAIL} Bu menü sana ait değil! `/market` yaz.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        urun_id = self.values[0]
        urun    = next((u for u in MARKET_URUNLER if u["id"] == urun_id), None)
        if not urun:
            return

        kayit = await database.ensure_user(interaction.user.id, interaction.user.display_name)
        if kayit["bakiye"] < urun["fiyat"]:
            embed = discord.Embed(
                title=f"{FAIL} Yetersiz Bakiye!",
                description=(
                    f"> Gerekli: **{urun['fiyat']:,}** {M2B}\n"
                    f"> Bakiyen: **{kayit['bakiye']:,}** {M2B}"
                ),
                color=0xE74C3C,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        basarili = await database.remove_coins(interaction.user.id, urun["fiyat"])
        if not basarili:
            embed = discord.Embed(
                title=f"{FAIL} İşlem Başarısız",
                description="Bir sorun oluştu, lütfen tekrar dene.",
                color=0xE74C3C,
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        async with database.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO market_satin_alma (discord_id, urun_id, fiyat) VALUES ($1, $2, $3)",
                interaction.user.id, urun["id"], urun["fiyat"],
            )

        kayit = await database.ensure_user(interaction.user.id, interaction.user.display_name)
        embed = discord.Embed(
            title=f"{OK} Satın Alındı!",
            description=(
                f"🎟️ **{urun['isim']}** başarıyla satın alındı!\n\n"
                f"💸 Ödenen: **{urun['fiyat']:,}** {M2B}\n"
                f"{M2B} Kalan bakiye: **{kayit['bakiye']:,}** M2B Coin"
            ),
            color=0x2ECC71,
        )
        embed.set_footer(text="🎫 Kupon aktivasyonu için ticket aç!")
        await interaction.followup.send(embed=embed, ephemeral=True)

        self.disabled = True
        try:
            await interaction.message.edit(view=self.view)
        except Exception:
            pass

        log.info(f"Market: {interaction.user} → {urun['id']} ({urun['fiyat']} coin)")


class MarketView(discord.ui.View):
    def __init__(self, discord_id: int, bakiye: int):
        super().__init__(timeout=120)
        self.add_item(MarketSelect(discord_id, bakiye))


class CoinMarketCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="market", description="M2B Mağazası — MP Kuponları satın al!")
    async def market(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            kayit  = await database.ensure_user(interaction.user.id, interaction.user.display_name)
            bakiye = kayit["bakiye"]

            embed = discord.Embed(
                title=f"{SHOP} M2B Mağazası",
                color=0xFFD700,
            )
            embed.description = (
                f"{M2B} Bakiyen: **{bakiye:,} M2B Coin**\n\n"
                "Aşağıdan satın almak istediğin kuponu seç:"
            )
            for urun in MARKET_URUNLER:
                durum = OK if bakiye >= urun["fiyat"] else "🔒"
                embed.add_field(
                    name=f"{durum} {urun['isim']}",
                    value=f"{M2B} **{urun['fiyat']:,} Coin**",
                    inline=True,
                )
            embed.set_footer(text="🎫 Kuponu aldıktan sonra ticket aç · /bakiye ile bakiyeni gör")

            view = MarketView(interaction.user.id, bakiye)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)

        except Exception as e:
            log.error(f"market hatası: {e}", exc_info=True)
            await interaction.followup.send(f"{FAIL} Bir hata oluştu.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(CoinMarketCog(bot))
