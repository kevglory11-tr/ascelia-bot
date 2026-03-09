"""
cogs/mini_oyun.py — /düello komutu.
İki oyuncu coin yatırır, kazanan tüm potuyu alır.
Oyun: 3 turlu taş-kağıt-makas.
"""

import asyncio
import random
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone

import database
from utils.logger import setup_logger

log = setup_logger("mini_oyun")

# Aktif düellolar: {mesaj_id: DuelloData}
aktif_duellolar: dict = {}

SECENEKLER = {
    "🪨 Taş":    "tas",
    "📄 Kağıt":  "kagit",
    "✂️ Makas":  "makas",
}
KAZANAN_MAP = {
    ("tas",   "makas"):  "tas",
    ("makas", "kagit"):  "makas",
    ("kagit", "tas"):    "kagit",
}


class DuelloData:
    def __init__(self, baslatan_id: int, rakip_id: int, bahis: int, mesaj: discord.Message):
        self.baslatan_id = baslatan_id
        self.rakip_id    = rakip_id
        self.bahis       = bahis
        self.mesaj       = mesaj
        self.secimler    = {}  # {user_id: "tas"/"kagit"/"makas"}
        self.tur         = 1
        self.skorlar     = {baslatan_id: 0, rakip_id: 0}
        self.kabul_edildi = False


class DuelloKabulView(discord.ui.View):
    def __init__(self, data: DuelloData):
        super().__init__(timeout=60)
        self.data = data

    @discord.ui.button(label="✅ Kabul Et", style=discord.ButtonStyle.success)
    async def kabul(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.data.rakip_id:
            await interaction.response.send_message("Bu düello sana yönlendirilmedi!", ephemeral=True)
            return
        await interaction.response.defer()

        # Rakip bakiyesi kontrol
        kayit = await database.ensure_user(interaction.user.id, interaction.user.display_name)
        if kayit["bakiye"] < self.data.bahis:
            await interaction.followup.send(
                f"❌ Yetersiz bakiye! **{self.data.bahis:,} Coin** gerekli.", ephemeral=True
            )
            return

        # İkisinden de coin çek
        ok1 = await database.remove_coins(self.data.baslatan_id, self.data.bahis)
        ok2 = await database.remove_coins(self.data.rakip_id,    self.data.bahis)
        if not ok1 or not ok2:
            await interaction.followup.send("❌ Coin çekilemedi, düello iptal.", ephemeral=True)
            del aktif_duellolar[self.data.mesaj.id]
            return

        self.data.kabul_edildi = True
        for item in self.children:
            item.disabled = True
        await self.data.mesaj.edit(view=self)

        # Tur başlat
        await _tur_baslat(self.data, interaction.channel)

    @discord.ui.button(label="❌ Reddet", style=discord.ButtonStyle.danger)
    async def reddet(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in (self.data.rakip_id, self.data.baslatan_id):
            await interaction.response.send_message("Bu düello sana ait değil!", ephemeral=True)
            return
        await interaction.response.defer()
        del aktif_duellolar[self.data.mesaj.id]
        await self.data.mesaj.edit(
            embed=discord.Embed(title="❌ Düello Reddedildi", color=0xE74C3C),
            view=None,
        )

    async def on_timeout(self):
        if not self.data.kabul_edildi:
            try:
                del aktif_duellolar[self.data.mesaj.id]
                await self.data.mesaj.edit(
                    embed=discord.Embed(title="⏰ Düello Süresi Doldu", color=0x95A5A6),
                    view=None,
                )
            except Exception:
                pass


class TurSecimView(discord.ui.View):
    def __init__(self, data: DuelloData, tur: int):
        super().__init__(timeout=30)
        self.data = data
        self.tur  = tur
        for emoji_label in SECENEKLER:
            self.add_item(TurSecimButon(emoji_label, data))


class TurSecimButon(discord.ui.Button):
    def __init__(self, label: str, data: DuelloData):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.data       = data
        self.secim_kodu = SECENEKLER[label]

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id not in (self.data.baslatan_id, self.data.rakip_id):
            await interaction.response.send_message("Bu düello sana ait değil!", ephemeral=True)
            return
        if interaction.user.id in self.data.secimler:
            await interaction.response.send_message("Zaten seçim yaptın!", ephemeral=True)
            return

        self.data.secimler[interaction.user.id] = self.secim_kodu
        await interaction.response.send_message(
            f"✅ **{self.label}** seçtin! Rakibin seçmesini bekliyor...", ephemeral=True
        )

        # İkisi de seçtiyse turu hesapla
        if len(self.data.secimler) == 2:
            for item in self.view.children:
                item.disabled = True
            try:
                await self.view.message.edit(view=self.view)
            except Exception:
                pass
            await asyncio.sleep(0.5)
            await _tur_hesapla(self.data, interaction.channel)


async def _tur_baslat(data: DuelloData, kanal: discord.TextChannel):
    data.secimler = {}
    baslatan = kanal.guild.get_member(data.baslatan_id)
    rakip    = kanal.guild.get_member(data.rakip_id)

    embed = discord.Embed(
        title=f"<a:sword:1478527729329639485> Düello — Tur {data.tur}/3",
        description=(
            f"⚔️ **{baslatan.display_name if baslatan else '???'}** vs **{rakip.display_name if rakip else '???'}**\n\n"
            f"💰 Pot: **{data.bahis * 2:,} Coin**\n\n"
            f"Skor: {data.skorlar[data.baslatan_id]} — {data.skorlar[data.rakip_id]}\n\n"
            "Aşağıdan seçimini yap! **30 saniye** süren var."
        ),
        color=0xFF6B35,
    )

    view = TurSecimView(data, data.tur)
    mesaj = await kanal.send(
        content=f"{baslatan.mention} {rakip.mention}",
        embed=embed,
        view=view,
    )
    view.message = mesaj

    # 30sn timeout — seçmeyeni kaybettir
    await asyncio.sleep(31)
    if len(data.secimler) < 2:
        # Seçmeyen kaybetti
        kazanan_id = None
        for uid in (data.baslatan_id, data.rakip_id):
            if uid not in data.secimler:
                kaybeden_id = uid
                kazanan_id  = data.baslatan_id if uid == data.rakip_id else data.rakip_id
                break
        if kazanan_id:
            await _duello_bitis(data, kazanan_id, kanal, sebep="süre doldu")


async def _tur_hesapla(data: DuelloData, kanal: discord.TextChannel):
    b_sec = data.secimler.get(data.baslatan_id)
    r_sec = data.secimler.get(data.rakip_id)

    b_label = next(k for k,v in SECENEKLER.items() if v == b_sec)
    r_label = next(k for k,v in SECENEKLER.items() if v == r_sec)

    baslatan = kanal.guild.get_member(data.baslatan_id)
    rakip    = kanal.guild.get_member(data.rakip_id)
    b_isim   = baslatan.display_name if baslatan else "Oyuncu 1"
    r_isim   = rakip.display_name    if rakip    else "Oyuncu 2"

    # Kazanan
    tur_kazanan = None
    if (b_sec, r_sec) in KAZANAN_MAP:
        tur_kazanan = data.baslatan_id
    elif (r_sec, b_sec) in KAZANAN_MAP:
        tur_kazanan = data.rakip_id
    # else: berabere

    sonuc_txt = ""
    if tur_kazanan == data.baslatan_id:
        data.skorlar[data.baslatan_id] += 1
        sonuc_txt = f"🏅 **{b_isim}** bu turu kazandı!"
    elif tur_kazanan == data.rakip_id:
        data.skorlar[data.rakip_id] += 1
        sonuc_txt = f"🏅 **{r_isim}** bu turu kazandı!"
    else:
        sonuc_txt = "🤝 Bu tur **berabere**!"

    embed = discord.Embed(
        title=f"Tur {data.tur} Sonucu",
        description=(
            f"{b_isim}: **{b_label}**\n"
            f"{r_isim}: **{r_label}**\n\n"
            f"{sonuc_txt}\n\n"
            f"📊 Skor: **{data.skorlar[data.baslatan_id]}** — **{data.skorlar[data.rakip_id]}**"
        ),
        color=0xFFD700,
    )
    await kanal.send(embed=embed)

    # 3 tur bitti mi ya da biri 2 tur aldı mı?
    data.tur += 1
    b_skor = data.skorlar[data.baslatan_id]
    r_skor = data.skorlar[data.rakip_id]

    if b_skor == 2:
        await _duello_bitis(data, data.baslatan_id, kanal)
    elif r_skor == 2:
        await _duello_bitis(data, data.rakip_id, kanal)
    elif data.tur > 3:
        # Berabere — coinler iade
        if b_skor == r_skor:
            await database.add_coins(data.baslatan_id, b_isim, data.bahis)
            await database.add_coins(data.rakip_id,    r_isim, data.bahis)
            embed = discord.Embed(
                title="🤝 Düello Berabere!",
                description=f"Herkes **{data.bahis:,} Coin** iade aldı.",
                color=0x95A5A6,
            )
            await kanal.send(embed=embed)
        elif b_skor > r_skor:
            await _duello_bitis(data, data.baslatan_id, kanal)
        else:
            await _duello_bitis(data, data.rakip_id, kanal)
    else:
        await asyncio.sleep(2)
        await _tur_baslat(data, kanal)


async def _duello_bitis(data: DuelloData, kazanan_id: int, kanal: discord.TextChannel, sebep: str = None):
    kazanan  = kanal.guild.get_member(kazanan_id)
    k_isim   = kazanan.display_name if kazanan else "???"
    pot      = data.bahis * 2
    yeni_bak = await database.add_coins(kazanan_id, k_isim, pot)

    aciklama = f"⏰ Rakip süre içinde seçim yapmadı!" if sebep == "süre doldu" else ""

    embed = discord.Embed(
        title="🏆 Düello Bitti!",
        description=(
            f"🥇 Kazanan: **{kazanan.mention if kazanan else k_isim}**\n"
            f"<a:coin:1478390167310958734> Kazanılan: **{pot:,} Coin**\n"
            f"💰 Yeni bakiye: **{yeni_bak:,} Coin**\n"
            + (f"\n{aciklama}" if aciklama else "")
        ),
        color=0xFFD700,
    )
    await kanal.send(embed=embed)

    if data.mesaj.id in aktif_duellolar:
        del aktif_duellolar[data.mesaj.id]

    log.info(f"Düello bitti: {k_isim} → +{pot} coin")


class MiniOyunCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="düello", description="Başka bir oyuncuyla coin bahisli düello yap!")
    @app_commands.describe(
        rakip="Düello yapmak istediğin kullanıcı",
        bahis="Kaç M2B Coin ile gireceksin?"
    )
    async def duello(self, interaction: discord.Interaction, rakip: discord.Member, bahis: int):
        await interaction.response.defer()

        if rakip.bot:
            await interaction.followup.send("❌ Botla düello yapamazsın!", ephemeral=True)
            return
        if rakip.id == interaction.user.id:
            await interaction.followup.send("❌ Kendinle düello yapamazsın!", ephemeral=True)
            return
        if bahis < 10:
            await interaction.followup.send("❌ Minimum bahis **10 Coin**!", ephemeral=True)
            return

        # Başlatanın bakiyesi
        kayit = await database.ensure_user(interaction.user.id, interaction.user.display_name)
        if kayit["bakiye"] < bahis:
            await interaction.followup.send(
                f"❌ Yetersiz bakiye! **{bahis:,} Coin** gerekli, bakiyen: **{kayit['bakiye']:,} Coin**",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title="⚔️ Düello Daveti!",
            description=(
                f"{interaction.user.mention} → {rakip.mention}\n\n"
                f"💰 Bahis: **{bahis:,} M2B Coin** kişi başı\n"
                f"🏆 Pot: **{bahis*2:,} M2B Coin**\n\n"
                "🎮 Oyun: **Taş - Kağıt - Makas** (3 tur)\n\n"
                f"{rakip.mention} **60 saniye** içinde kabul etmeli!"
            ),
            color=0xFF6B35,
        )

        mesaj = await interaction.followup.send(embed=embed)

        # Mesaj objesini al
        mesaj_obj = await interaction.original_response()
        data      = DuelloData(interaction.user.id, rakip.id, bahis, mesaj_obj)
        aktif_duellolar[mesaj_obj.id] = data

        view = DuelloKabulView(data)
        await mesaj_obj.edit(view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(MiniOyunCog(bot))
