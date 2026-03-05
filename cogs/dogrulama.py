"""cogs/dogrulama.py — Modern doğrulama sistemi."""

import asyncio
import logging
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from config.settings import Settings
from utils.permissions import is_admin, yetki_yok_mesaji

log = logging.getLogger("cog.dogrulama")


class DogrulamaView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Doğrulamak için tıkla",
        style=discord.ButtonStyle.success,
        custom_id="dogrulama_butonu",
        emoji="⚔️",
    )
    async def dogrula(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        settings = Settings()
        guild = interaction.guild
        uye = interaction.user

        dogrulanmis_rol = guild.get_role(settings.verify_edilmis_rol_id)
        if dogrulanmis_rol and dogrulanmis_rol in uye.roles:
            await interaction.response.send_message(
                "✅ Zaten doğrulanmışsın!",
                ephemeral=True
            )
            return

        try:
            if dogrulanmis_rol:
                await uye.add_roles(dogrulanmis_rol, reason="Doğrulama tamamlandı")
            dogrulanmamis_rol = guild.get_role(settings.verify_edilmemis_rol_id)
            if dogrulanmamis_rol and dogrulanmamis_rol in uye.roles:
                await uye.remove_roles(dogrulanmamis_rol, reason="Doğrulama tamamlandı")
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Rol verme yetkim yok. Lütfen yöneticilere bildirin.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title="✅  Doğrulama Başarılı!",
            description=(
                f"Hoş geldin, **{uye.display_name}**!\n\n"
                f"**{guild.name}** sunucusuna erişimin açıldı.\n\n"
                "```\n"
                "⚔️  Sıradaki adımlar:\n"
                "  • Kanalları keşfet\n"
                "  • /sss ile sunucu hakkında bilgi edin\n"
                "  • Yardım için /ticket kullan\n"
                "```"
            ),
            color=0x2ECC71,
            timestamp=datetime.now(timezone.utc),
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.set_footer(text="Ascelia Bot • AWGames")
        await interaction.response.send_message(embed=embed, ephemeral=True)

        log_kanal = guild.get_channel(settings.verify_log_kanal_id)
        if log_kanal:
            log_emb = discord.Embed(
                title="✅  Yeni Doğrulama",
                color=0x2ECC71,
                timestamp=datetime.now(timezone.utc),
            )
            log_emb.add_field(name="👤  Kullanıcı", value=f"{uye.mention}\n`{uye.name}`", inline=True)
            log_emb.add_field(name="🆔  ID", value=f"`{uye.id}`", inline=True)
            log_emb.add_field(name="📅  Hesap Yaşı", value=f"<t:{int(uye.created_at.timestamp())}:R>", inline=True)
            log_emb.set_thumbnail(url=str(uye.display_avatar.url))
            log_emb.set_footer(text="Ascelia Bot • AWGames")
            await log_kanal.send(embed=log_emb)

        log.info(f"Doğrulama → {uye} ({uye.id})")

    @discord.ui.button(
        label="Neden doğrulamalıyım?",
        style=discord.ButtonStyle.secondary,
        custom_id="dogrulama_bilgi",
        emoji="❓",
    )
    async def bilgi(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        embed = discord.Embed(
            title="❓  Doğrulama Hakkında",
            description=(
                "Sunucumuzu bot ve spam hesaplardan korumak için\n"
                "doğrulama sistemi kullanıyoruz.\n\n"
                "```\n"
                "✅  Doğruladıktan sonra:\n"
                "  • Tüm kanallara erişim kazanırsın\n"
                "  • Etkinliklere katılabilirsin\n"
                "  • Destek alabilirsin\n"
                "```\n\n"
                "Sorun yaşarsan yöneticilere bildir."
            ),
            color=Settings().renkler["altin"],
        )
        embed.set_footer(text="Ascelia Bot • AWGames")
        await interaction.response.send_message(embed=embed, ephemeral=True)


class DogrulamaCog(commands.Cog, name="Doğrulama"):

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.settings = Settings()
        self._dm_queue: asyncio.Queue = asyncio.Queue()
        self._dm_worker_task: asyncio.Task | None = None

    async def cog_load(self) -> None:
        self.bot.add_view(DogrulamaView())
        self._dm_worker_task = asyncio.create_task(self._dm_worker())
        log.info("Doğrulama view'ı ve DM kuyruğu yüklendi")

    async def cog_unload(self) -> None:
        if self._dm_worker_task:
            self._dm_worker_task.cancel()

    async def _dm_worker(self) -> None:
        """DM'leri sırayla ve rate limit'e takılmadan gönderir."""
        while True:
            uye, embed = await self._dm_queue.get()
            try:
                await uye.send(embed=embed)
                log.debug(f"Hoşgeldin DM'i gönderildi → {uye} ({uye.id})")
            except discord.Forbidden as e:
                hata_kodu = getattr(e, 'code', 0)
                if hata_kodu == 50007:
                    log.debug(f"DM gönderilemedi (DM kapalı / 50007) → {uye} ({uye.id})")
                else:
                    log.warning(f"DM Forbidden (kod={hata_kodu}) → {uye} ({uye.id}), 30sn sonra tekrar denenecek")
                    await asyncio.sleep(30)
                    try:
                        await uye.send(embed=embed)
                        log.info(f"DM retry başarılı → {uye} ({uye.id})")
                    except Exception as retry_e:
                        log.warning(f"DM retry de başarısız → {uye} ({uye.id}): {type(retry_e).__name__}")
            except discord.HTTPException as e:
                if e.code == 40003:
                    log.warning(f"DM rate limit (40003), 10sn bekleniyor → {uye} ({uye.id})")
                    await self._dm_queue.put((uye, embed))
                    await asyncio.sleep(10)
                else:
                    log.error(f"DM HTTPException ({e.code}) → {uye}: {e}")
            except Exception as e:
                log.error(f"DM beklenmeyen hata → {uye}: {e}")
            finally:
                self._dm_queue.task_done()
                # DM'ler arası 1.5sn bekleme — rate limit'i önler
                await asyncio.sleep(1.5)

    @commands.Cog.listener()
    async def on_member_join(self, uye: discord.Member) -> None:
        # Doğrulanmamış rolü ver
        rol = uye.guild.get_role(self.settings.verify_edilmemis_rol_id)
        if rol:
            try:
                await uye.add_roles(rol, reason="Yeni üye — doğrulama bekleniyor")
            except discord.Forbidden:
                log.warning(f"Yeni üyeye rol verilemedi: {uye}")

        # Hoşgeldin DM'ini kuyruğa ekle (direkt göndermiyoruz)
        embed = discord.Embed(
            color=self.settings.renkler["altin"],
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_author(
            name=f"{uye.guild.name} sunucusuna hoş geldin!",
            icon_url=uye.guild.icon.url if uye.guild.icon else None,
        )
        embed.description = (
            f"Merhaba **{uye.display_name}**! 👋\n\n"
            f"**{uye.guild.name}** sunucusuna katıldığın için teşekkürler.\n\n"
            "```\n"
            "🚀  Başlamak için:\n"
            "  1. Doğrulama kanalına git\n"
            "  2. Butona tıkla ve erişim kazan\n"
            "  3. Kanalları keşfetmeye başla!\n"
            "```"
        )
        if uye.guild.icon:
            embed.set_thumbnail(url=uye.guild.icon.url)
        embed.set_footer(text="Ascelia Bot • AWGames")

        await self._dm_queue.put((uye, embed))
        log.debug(f"DM kuyruğa eklendi → {uye} ({uye.id}) | Kuyruk: {self._dm_queue.qsize()}")

    @app_commands.command(name="doğrula-panel", description="[ADMIN] Doğrulama panelini gönder")
    async def dogrula_panel(self, interaction: discord.Interaction) -> None:
        if not is_admin(interaction, self.settings):
            await yetki_yok_mesaji(interaction); return

        embed = discord.Embed(
            title="🔐  Kimlik Doğrulama",
            color=self.settings.renkler["altin"],
        )

        if interaction.guild and interaction.guild.icon:
            embed.set_author(
                name=interaction.guild.name,
                icon_url=interaction.guild.icon.url,
            )
            embed.set_thumbnail(url=interaction.guild.icon.url)

        embed.description = (
            "Sunucumuza hoş geldin!\n\n"
            "Kanallara erişmek ve topluluğumuza katılmak için\n"
            "aşağıdaki butona tıklaman yeterli.\n\n"
            "```\n"
            "🔒  Bu işlem sunucumuzu botlardan korur\n"
            "⚔️  Doğruladıktan sonra tüm kanallara erişirsin\n"
            "⏱️  Sadece birkaç saniye sürer\n"
            "```"
        )
        embed.set_footer(
            text="Ascelia Bot • AWGames | Sorun yaşarsan yöneticilere bildir",
            icon_url=interaction.guild.icon.url if interaction.guild and interaction.guild.icon else None,
        )

        await interaction.channel.send(embed=embed, view=DogrulamaView())
        await interaction.response.send_message("✅ Doğrulama paneli gönderildi.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(DogrulamaCog(bot))
