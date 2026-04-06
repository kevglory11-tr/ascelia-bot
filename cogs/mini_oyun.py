"""cogs/mini_oyun.py — /düello komutu. Taş-Kağıt-Makas, coin bahisli."""

import asyncio, random
import discord
from discord.ext import commands
from discord import app_commands

import database
from utils.logger import setup_logger

log        = setup_logger("mini_oyun")
M2B        = "<:m2bcoin:1480481551337783437>"
OK         = "<a:check:1478394670856933429>"
FAIL       = "❌"
COIN_ANIM  = "<a:coin:1478390167310958734>"
SWORD_ANIM = "<a:ticket1:1478391380635287725>"

aktif_duellolar: dict = {}

SECENEKLER = {
    "🪨 Taş":   "tas",
    "📄 Kağıt": "kagit",
    "✂️ Makas": "makas",
}
KAZANAN_MAP = {
    ("tas",   "makas"): "tas",
    ("makas", "kagit"): "makas",
    ("kagit", "tas"):   "kagit",
}


class DuelloData:
    def __init__(self, baslatan_id, rakip_id, bahis, mesaj):
        self.baslatan_id  = baslatan_id
        self.rakip_id     = rakip_id
        self.bahis        = bahis
        self.mesaj        = mesaj
        self.secimler     = {}
        self.tur          = 1
        self.skorlar      = {baslatan_id: 0, rakip_id: 0}
        self.kabul_edildi = False
        self.bitti        = False   # çift bitişi önler


class DuelloKabulView(discord.ui.View):
    def __init__(self, data: DuelloData):
        super().__init__(timeout=60)
        self.data = data

    @discord.ui.button(label="Kabul Et", style=discord.ButtonStyle.success, emoji="⚔️")
    async def kabul(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.data.rakip_id:
            await interaction.response.send_message(f"{FAIL} Bu düello sana yönlendirilmedi!", ephemeral=True)
            return
        await interaction.response.defer()

        kayit = await database.ensure_user(interaction.user.id, interaction.user.display_name)
        if kayit["bakiye"] < self.data.bahis:
            await interaction.followup.send(
                f"{FAIL} Yetersiz bakiye! **{self.data.bahis:,}** {M2B} gerekli.", ephemeral=True
            )
            return

        ok1 = await database.remove_coins(self.data.baslatan_id, self.data.bahis)
        ok2 = await database.remove_coins(self.data.rakip_id,    self.data.bahis)
        if not ok1 or not ok2:
            # Başarılı olan çekimi iade et — coin kaybı olmasın
            if ok1:
                bas_uye = interaction.guild.get_member(self.data.baslatan_id)
                bas_isim = bas_uye.display_name if bas_uye else "Oyuncu"
                await database.add_coins(self.data.baslatan_id, bas_isim, self.data.bahis,
                                         aciklama="Düello iade — karşı taraf yetersiz bakiye")
            if ok2:
                rak_uye = interaction.guild.get_member(self.data.rakip_id)
                rak_isim = rak_uye.display_name if rak_uye else "Oyuncu"
                await database.add_coins(self.data.rakip_id, rak_isim, self.data.bahis,
                                         aciklama="Düello iade — karşı taraf yetersiz bakiye")
            await interaction.followup.send(f"{FAIL} Coin çekilemedi, düello iptal.", ephemeral=True)
            aktif_duellolar.pop(self.data.mesaj.id, None)
            return

        self.data.kabul_edildi = True
        for item in self.children:
            item.disabled = True
        await self.data.mesaj.edit(view=self)
        await _tur_baslat(self.data, interaction.channel)

    @discord.ui.button(label="Reddet", style=discord.ButtonStyle.danger, emoji="🚫")
    async def reddet(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in (self.data.rakip_id, self.data.baslatan_id):
            await interaction.response.send_message(f"{FAIL} Bu düello sana ait değil!", ephemeral=True)
            return
        await interaction.response.defer()
        aktif_duellolar.pop(self.data.mesaj.id, None)
        await self.data.mesaj.edit(
            embed=discord.Embed(title=f"{FAIL} Düello Reddedildi", color=0xE74C3C),
            view=None,
        )

    async def on_timeout(self):
        if not self.data.kabul_edildi:
            try:
                aktif_duellolar.pop(self.data.mesaj.id, None)
                await self.data.mesaj.edit(
                    embed=discord.Embed(title="⏰ Düello Süresi Doldu", color=0x95A5A6),
                    view=None,
                )
            except Exception:
                pass


class TurSecimView(discord.ui.View):
    def __init__(self, data: DuelloData, tur_no: int):
        super().__init__(timeout=30)
        self.data   = data
        self.tur_no = tur_no  # hangi tura ait olduğunu takip et
        for label in SECENEKLER:
            self.add_item(TurSecimButon(label, data, tur_no))


class TurSecimButon(discord.ui.Button):
    def __init__(self, label: str, data: DuelloData, tur_no: int):
        super().__init__(label=label, style=discord.ButtonStyle.primary)
        self.data       = data
        self.secim_kodu = SECENEKLER[label]
        self.tur_no     = tur_no

    async def callback(self, interaction: discord.Interaction):
        # Eski tura ait buton tıklamasını yoksay
        if self.tur_no != self.data.tur:
            await interaction.response.send_message("Bu tur zaten bitti!", ephemeral=True)
            return
        if interaction.user.id not in (self.data.baslatan_id, self.data.rakip_id):
            await interaction.response.send_message(f"{FAIL} Bu düello sana ait değil!", ephemeral=True)
            return
        if interaction.user.id in self.data.secimler:
            await interaction.response.send_message("Zaten seçim yaptın!", ephemeral=True)
            return

        self.data.secimler[interaction.user.id] = self.secim_kodu
        await interaction.response.send_message(
            f"{OK} **{self.label}** seçtin! Rakibin seçmesini bekliyorum...", ephemeral=True
        )

        if len(self.data.secimler) == 2:
            for item in self.view.children:
                item.disabled = True
            try:
                await self.view.message.edit(view=self.view)
            except Exception:
                pass
            await asyncio.sleep(0.5)
            await _tur_hesapla(self.data, interaction.channel)


async def _tur_baslat(data: DuelloData, kanal):
    if data.bitti:
        return

    data.secimler = {}
    tur_no        = data.tur   # bu turun numarasını kaydet
    baslatan      = kanal.guild.get_member(data.baslatan_id)
    rakip         = kanal.guild.get_member(data.rakip_id)
    b_isim        = baslatan.display_name if baslatan else "Oyuncu 1"
    r_isim        = rakip.display_name    if rakip    else "Oyuncu 2"

    embed = discord.Embed(
        title=f"{SWORD_ANIM} Düello — Tur {tur_no}/3",
        description=(
            f"⚔️ **{b_isim}** vs **{r_isim}**\n\n"
            f"{COIN_ANIM} Pot: **{data.bahis * 2:,}** {M2B}\n"
            f"📊 Skor: **{data.skorlar[data.baslatan_id]}** — **{data.skorlar[data.rakip_id]}**\n\n"
            "Aşağıdan seçimini yap! **30 saniye** süren var."
        ),
        color=0xFF6B35,
    )
    view  = TurSecimView(data, tur_no)
    mesaj = await kanal.send(
        content=f"{baslatan.mention if baslatan else ''} {rakip.mention if rakip else ''}",
        embed=embed,
        view=view,
    )
    view.message = mesaj

    # 31sn bekle — sadece bu turun timeout'u
    await asyncio.sleep(31)

    # Sadece hâlâ aynı turdaysak ve bitmemişse timeout uygula
    if data.bitti or data.tur != tur_no:
        return
    if len(data.secimler) < 2:
        for uid in (data.baslatan_id, data.rakip_id):
            if uid not in data.secimler:
                kazanan_id = data.baslatan_id if uid == data.rakip_id else data.rakip_id
                await _duello_bitis(data, kazanan_id, kanal, sebep="süre doldu")
                return


async def _tur_hesapla(data: DuelloData, kanal):
    if data.bitti:
        return

    b_sec  = data.secimler.get(data.baslatan_id)
    r_sec  = data.secimler.get(data.rakip_id)
    b_lbl  = next(k for k,v in SECENEKLER.items() if v == b_sec)
    r_lbl  = next(k for k,v in SECENEKLER.items() if v == r_sec)

    def isim(uid):
        m = kanal.guild.get_member(uid)
        return m.display_name if m else "Oyuncu"

    b_isim = isim(data.baslatan_id)
    r_isim = isim(data.rakip_id)

    if (b_sec, r_sec) in KAZANAN_MAP:
        data.skorlar[data.baslatan_id] += 1
        sonuc = f"{OK} **{b_isim}** bu turu kazandı!"
    elif (r_sec, b_sec) in KAZANAN_MAP:
        data.skorlar[data.rakip_id] += 1
        sonuc = f"{OK} **{r_isim}** bu turu kazandı!"
    else:
        sonuc = "🤝 Bu tur **berabere**!"

    embed = discord.Embed(
        title=f"Tur {data.tur} Sonucu",
        description=(
            f"{b_isim}: **{b_lbl}**\n"
            f"{r_isim}: **{r_lbl}**\n\n"
            f"{sonuc}\n\n"
            f"📊 Skor: **{data.skorlar[data.baslatan_id]}** — **{data.skorlar[data.rakip_id]}**"
        ),
        color=0xFFD700,
    )
    await kanal.send(embed=embed)

    b_s = data.skorlar[data.baslatan_id]
    r_s = data.skorlar[data.rakip_id]

    # Kazanan belli mi?
    if b_s == 2:
        await _duello_bitis(data, data.baslatan_id, kanal)
    elif r_s == 2:
        await _duello_bitis(data, data.rakip_id, kanal)
    elif data.tur >= 3:
        # 3 tur bitti
        if b_s == r_s:
            await database.add_coins(data.baslatan_id, b_isim, data.bahis)
            await database.add_coins(data.rakip_id,    r_isim, data.bahis)
            data.bitti = True
            aktif_duellolar.pop(data.mesaj.id, None)
            await kanal.send(embed=discord.Embed(
                title="🤝 Düello Berabere!",
                description=f"Herkes **{data.bahis:,}** {M2B} iade aldı.",
                color=0x95A5A6,
            ))
        elif b_s > r_s:
            await _duello_bitis(data, data.baslatan_id, kanal)
        else:
            await _duello_bitis(data, data.rakip_id, kanal)
    else:
        data.tur += 1
        await asyncio.sleep(2)
        await _tur_baslat(data, kanal)


async def _duello_bitis(data: DuelloData, kazanan_id: int, kanal, sebep: str = None):
    if data.bitti:
        return
    data.bitti = True
    aktif_duellolar.pop(data.mesaj.id, None)

    kazanan  = kanal.guild.get_member(kazanan_id)
    k_isim   = kazanan.display_name if kazanan else "???"
    pot      = data.bahis * 2
    yeni_bak = await database.add_coins(kazanan_id, k_isim, pot)

    embed = discord.Embed(
        title="🏆 Düello Bitti!",
        description=(
            f"{OK} Kazanan: **{kazanan.mention if kazanan else k_isim}**\n"
            f"{COIN_ANIM} Kazanılan: **{pot:,}** {M2B}\n"
            f"{M2B} Yeni bakiye: **{yeni_bak:,} M2B Coin**"
            + (f"\n\n⏰ Rakip süre içinde seçim yapmadı!" if sebep == "süre doldu" else "")
        ),
        color=0xFFD700,
    )
    await kanal.send(embed=embed)
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
            await interaction.followup.send(f"{FAIL} Botla düello yapamazsın!", ephemeral=True)
            return
        if rakip.id == interaction.user.id:
            await interaction.followup.send(f"{FAIL} Kendinle düello yapamazsın!", ephemeral=True)
            return
        if bahis < 10:
            await interaction.followup.send(f"{FAIL} Minimum bahis **10 Coin**!", ephemeral=True)
            return

        kayit = await database.ensure_user(interaction.user.id, interaction.user.display_name)
        if kayit["bakiye"] < bahis:
            await interaction.followup.send(
                f"{FAIL} Yetersiz bakiye! **{bahis:,}** {M2B} gerekli, bakiyen: **{kayit['bakiye']:,}**",
                ephemeral=True,
            )
            return

        embed = discord.Embed(
            title=f"{SWORD_ANIM} Düello Daveti!",
            description=(
                f"{interaction.user.mention} → {rakip.mention}\n\n"
                f"{M2B} Bahis: **{bahis:,} M2B Coin** kişi başı\n"
                f"{COIN_ANIM} Pot: **{bahis*2:,} M2B Coin**\n\n"
                f"🎮 Oyun: **Taş - Kağıt - Makas** (3 tur)\n\n"
                f"{rakip.mention} **60 saniye** içinde kabul etmeli!"
            ),
            color=0xFF6B35,
        )
        await interaction.followup.send(embed=embed)
        mesaj_obj = await interaction.original_response()

        data = DuelloData(interaction.user.id, rakip.id, bahis, mesaj_obj)
        aktif_duellolar[mesaj_obj.id] = data

        view = DuelloKabulView(data)
        await mesaj_obj.edit(view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(MiniOyunCog(bot))
