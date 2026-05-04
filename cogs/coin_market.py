"""cogs/coin_market.py — /market komutu (MP Kuponları + Rozet Mağazası)."""

import discord
import os
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone, timedelta

import database
from utils.logger import setup_logger
from config.coin_settings import MARKET_URUNLER, ROZET_MAGAZA

MARKET_LOG_KANAL_ID = int(os.getenv("MARKET_LOG_KANAL_ID", "0"))

GEM  = "💎"
M2B  = "<:m2bcoin:1480481551337783437>"
OK   = "<a:check:1478394670856933429>"
FAIL = "❌"
SHOP = "<a:genel:1478389856874004592>"

log = setup_logger("coin_market")

TR_OFFSET = timedelta(hours=3)


def _bugun_tr() -> str:
    return (datetime.now(timezone.utc) + TR_OFFSET).strftime("%Y-%m-%d")


# ── MP Kupon Market ────────────────────────────────────────────────────────────

class MarketSelect(discord.ui.Select):
    def __init__(self, discord_id: int, bakiye: int, bugun_alindi: bool):
        self.discord_id = discord_id
        options = []
        for urun in MARKET_URUNLER:
            gem_bonus = urun.get("gem", 0)
            gem_txt   = f" + {gem_bonus} 💎" if gem_bonus > 0 else ""
            if bugun_alindi:
                durum = "⛔"
                desc  = "Bugün satın alma hakkın doldu"
            elif bakiye >= urun["fiyat"]:
                durum = "✦"
                desc  = f"{urun['fiyat']:,} M2B Coin{gem_txt}"
            else:
                durum = "🔒"
                desc  = f"{urun['fiyat']:,} M2B Coin{gem_txt} — Yetersiz bakiye"
            options.append(discord.SelectOption(
                label=urun["isim"],
                description=f"{durum}  {desc}",
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

        async with database.pool.acquire() as conn:
            gunluk = await conn.fetchval(
                "SELECT 1 FROM market_gunluk WHERE discord_id=$1 AND tarih=$2",
                interaction.user.id, _bugun_tr()
            )
        if gunluk:
            await interaction.followup.send(
                "❌ Bugün zaten bir ürün satın aldın! Her gün **1 alım** hakkın var, yarın tekrar gel.",
                ephemeral=True
            )
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
            await interaction.followup.send(
                discord.Embed(
                    title=f"{FAIL} İşlem Başarısız",
                    description="Bir sorun oluştu, lütfen tekrar dene.",
                    color=0xE74C3C,
                ),
                ephemeral=True,
            )
            return

        async with database.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO market_satin_alma (discord_id, urun_id, fiyat) VALUES ($1, $2, $3)",
                interaction.user.id, urun["id"], urun["fiyat"],
            )
            await conn.execute(
                "INSERT INTO market_gunluk (discord_id, tarih) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                interaction.user.id, _bugun_tr(),
            )

        gem_bonus = urun.get("gem", 0)
        gem_satir = ""
        if gem_bonus > 0:
            await database.add_gem(interaction.user.id, gem_bonus,
                                   tip="market_bonus", aciklama=f"{urun['isim']} alım bonusu")
            gem_satir = f"\n{GEM} **+{gem_bonus} Gem** bonus olarak eklendi!"

        kayit     = await database.ensure_user(interaction.user.id, interaction.user.display_name)
        simdi_tr  = datetime.now(timezone.utc) + TR_OFFSET
        tarih_str = simdi_tr.strftime("%d.%m.%Y %H:%M")

        embed = discord.Embed(
            title=f"{OK} Satın Alındı!",
            description=(
                f"🎟️ **{urun['isim']}** başarıyla satın alındı!\n\n"
                f"💸 Ödenen: **{urun['fiyat']:,}** {M2B}\n"
                f"{M2B} Kalan bakiye: **{kayit['bakiye']:,}** M2B Coin"
                f"{gem_satir}\n\n"
                f"⏰ **Satın alma saati:** {tarih_str}\n"
                f"🔄 **Günlük limit:** Bugün 1 alım hakkın vardı, kullandın.\n"
                f"📅 Bir sonraki alım hakkın **yarın 00:00 TR** saatinde açılır."
            ),
            color=0x2ECC71,
        )
        embed.set_footer(text="🎫 Kupon aktivasyonu için ticket aç!")
        await interaction.followup.send(embed=embed, ephemeral=True)

        if MARKET_LOG_KANAL_ID:
            try:
                log_kanal = (
                    interaction.client.get_channel(MARKET_LOG_KANAL_ID)
                    or await interaction.client.fetch_channel(MARKET_LOG_KANAL_ID)
                )
                log_embed = discord.Embed(title="🛒 Market Alışverişi", color=0x3498DB)
                log_embed.add_field(name="👤 Kullanıcı", value=f"{interaction.user.mention}\n`{interaction.user.id}`", inline=True)
                log_embed.add_field(name="🎟️ Ürün",     value=urun["isim"],                          inline=True)
                log_embed.add_field(name="💸 Ödenen",   value=f"**{urun['fiyat']:,}** {M2B}",        inline=True)
                log_embed.add_field(name=f"{M2B} Kalan", value=f"**{kayit['bakiye']:,}** M2B Coin",   inline=True)
                log_embed.add_field(name="📅 Tarih",    value=tarih_str,                             inline=True)
                log_embed.set_thumbnail(url=interaction.user.display_avatar.url)
                log_embed.set_footer(text=f"Market Log • {tarih_str}")
                await log_kanal.send(embed=log_embed)
            except Exception as e:
                log.error(f"Market log kanalına gönderilemedi: {e}")

        self.disabled = True
        try:
            await interaction.message.edit(view=self.view)
        except Exception:
            pass

        log.info(f"MP Market: {interaction.user} → {urun['id']} ({urun['fiyat']} coin)")


class MarketView(discord.ui.View):
    def __init__(self, discord_id: int, bakiye: int, bugun_alindi: bool):
        super().__init__(timeout=120)
        self.add_item(MarketSelect(discord_id, bakiye, bugun_alindi))


# ── Rozet Mağazası ─────────────────────────────────────────────────────────────

class RozetMarketSelect(discord.ui.Select):
    def __init__(self, discord_id: int, bakiye: int, sahip_ids: list):
        self.discord_id = discord_id
        options = []
        for rozet in ROZET_MAGAZA:
            sahip = rozet["id"] in sahip_ids
            if sahip:
                durum = "✅"
                desc  = "Zaten sahipsin"
            elif bakiye >= rozet["fiyat"]:
                durum = "✦"
                desc  = f"{rozet['fiyat']:,} M2B Coin"
            else:
                durum = "🔒"
                desc  = f"{rozet['fiyat']:,} M2B Coin — Yetersiz bakiye"
            label = f"{'✅ ' if sahip else ''}{rozet['isim']}"
            options.append(discord.SelectOption(
                label=label[:100],
                description=f"{durum} {desc}"[:100],
                value=rozet["id"],
                emoji=rozet.get("emoji"),
            ))
        super().__init__(
            placeholder="🏅 Satın almak istediğin rozeti seç...",
            options=options[:25],
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.discord_id:
            await interaction.response.send_message("Bu menü sana ait değil!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)

        rozet_id = self.values[0]
        rozet    = next((r for r in ROZET_MAGAZA if r["id"] == rozet_id), None)
        if not rozet:
            return

        sahip_ids = await database.get_rozet_listesi(interaction.user.id)
        if rozet_id in sahip_ids:
            await interaction.followup.send(f"{FAIL} Bu rozete zaten sahipsin!", ephemeral=True)
            return

        kayit = await database.ensure_user(interaction.user.id, interaction.user.display_name)
        if kayit["bakiye"] < rozet["fiyat"]:
            await interaction.followup.send(
                f"{FAIL} Yetersiz bakiye!\nGerekli: **{rozet['fiyat']:,}** — Bakiyen: **{kayit['bakiye']:,}**",
                ephemeral=True,
            )
            return

        ok = await database.remove_coins(
            interaction.user.id, rozet["fiyat"], aciklama=f"Rozet: {rozet['isim']}"
        )
        if not ok:
            await interaction.followup.send(f"{FAIL} İşlem başarısız.", ephemeral=True)
            return

        await database.add_rozet(interaction.user.id, rozet_id)
        kayit = await database.ensure_user(interaction.user.id, interaction.user.display_name)

        embed = discord.Embed(
            title=f"{OK} Rozet Satın Alındı!",
            description=(
                f"{rozet.get('emoji', '🏅')} **{rozet['isim']}** koleksiyonuna eklendi!\n\n"
                f"💸 Ödenen: **{rozet['fiyat']:,}** {M2B}\n"
                f"{M2B} Kalan bakiye: **{kayit['bakiye']:,}** M2B Coin\n\n"
                f"`/rozet-sec` ile profil kartında aktif hale getirebilirsin."
            ),
            color=0x9B59B6,
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        log.info(f"Rozet alındı: {interaction.user} → {rozet_id} ({rozet['fiyat']} coin)")


class RozetMarketView(discord.ui.View):
    def __init__(self, discord_id: int, bakiye: int, sahip_ids: list):
        super().__init__(timeout=120)
        self.add_item(RozetMarketSelect(discord_id, bakiye, sahip_ids))


# ── Kategori Seçim ─────────────────────────────────────────────────────────────

class MarketKategoriView(discord.ui.View):
    def __init__(self, discord_id: int, bakiye: int):
        super().__init__(timeout=120)
        self.discord_id = discord_id
        self.bakiye     = bakiye

    @discord.ui.button(label="🎟️ MP Kuponları", style=discord.ButtonStyle.primary)
    async def mp_kuponlari(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.discord_id:
            await interaction.response.send_message("Bu menü sana ait değil!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)

        async with database.pool.acquire() as conn:
            bugun_alindi = bool(await conn.fetchval(
                "SELECT 1 FROM market_gunluk WHERE discord_id=$1 AND tarih=$2",
                interaction.user.id, _bugun_tr()
            ))

        embed = discord.Embed(
            title=f"{SHOP} MP Kuponları",
            description=(
                f"{M2B} Bakiyen: **{self.bakiye:,} M2B Coin**\n\n"
                "Aşağıdan satın almak istediğin kuponu seç:"
            ),
            color=0xFFD700,
        )
        for urun in MARKET_URUNLER:
            if bugun_alindi:
                durum = "⛔"
            elif self.bakiye >= urun["fiyat"]:
                durum = OK
            else:
                durum = "🔒"
            gem_bonus = urun.get("gem", 0)
            gem_txt   = f"\n{GEM} **+{gem_bonus} Gem** bonus!" if gem_bonus > 0 else ""
            embed.add_field(
                name=f"{durum} {urun['isim']}",
                value=f"{M2B} **{urun['fiyat']:,} Coin**{gem_txt}",
                inline=True,
            )
        if bugun_alindi:
            embed.set_footer(text="⛔ Bugünkü alım hakkın doldu · Yarın 00:00'da sıfırlanır")
        else:
            embed.set_footer(text="🎫 Günde 1 alım hakkın var · Kuponu aldıktan sonra ticket aç")

        view = MarketView(interaction.user.id, self.bakiye, bugun_alindi)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="🏅 Rozet Mağazası", style=discord.ButtonStyle.secondary)
    async def rozet_magazasi(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.discord_id:
            await interaction.response.send_message("Bu menü sana ait değil!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)

        sahip_ids = await database.get_rozet_listesi(interaction.user.id)

        embed = discord.Embed(
            title="🏅 Rozet Mağazası",
            description=(
                f"{M2B} Bakiyen: **{self.bakiye:,} M2B Coin**\n\n"
                "Satın aldığın rozetleri `/rozet-sec` ile profil kartında aktif edebilirsin."
            ),
            color=0x9B59B6,
        )
        for rozet in ROZET_MAGAZA:
            sahip = rozet["id"] in sahip_ids
            if sahip:
                durum = "✅"
            elif self.bakiye >= rozet["fiyat"]:
                durum = "✦"
            else:
                durum = "🔒"
            embed.add_field(
                name=f"{rozet.get('emoji', '🏅')} {rozet['isim']}",
                value=f"{durum} **{rozet['fiyat']:,} Coin**" + (" *(sahipsin)*" if sahip else ""),
                inline=True,
            )

        view = RozetMarketView(interaction.user.id, self.bakiye, sahip_ids)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)


# ── Cog ────────────────────────────────────────────────────────────────────────

class CoinMarketCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="market", description="M2B Mağazası — MP Kuponları ve Rozetler!")
    async def market(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            kayit  = await database.ensure_user(interaction.user.id, interaction.user.display_name)
            bakiye = kayit["bakiye"]

            embed = discord.Embed(
                title=f"{SHOP} M2B Mağazası",
                description=(
                    f"{M2B} Bakiyen: **{bakiye:,} M2B Coin**\n\n"
                    "Kategori seçerek alışverişe başla:"
                ),
                color=0xFFD700,
            )
            embed.add_field(
                name="🎟️ MP Kuponları",
                value="Günde 1 alım hakkı · 100–500 MP aralığı",
                inline=True,
            )
            embed.add_field(
                name="🏅 Rozet Mağazası",
                value=f"Profil rozeti koleksiyonu · {len(ROZET_MAGAZA)} rozet",
                inline=True,
            )
            view = MarketKategoriView(interaction.user.id, bakiye)
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)

        except Exception as e:
            log.error(f"market hatası: {e}", exc_info=True)
            await interaction.followup.send(f"{FAIL} Bir hata oluştu.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(CoinMarketCog(bot))
