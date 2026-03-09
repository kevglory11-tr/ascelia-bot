"""
config/settings.py — Tüm ayarlar tek yerden yönetilir.
Burası dışında hiçbir dosyada sabit değer yoktur.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Tuple
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:

    # ── Temel ─────────────────────────────────────────────────────────────────
    discord_token:    str   = field(default_factory=lambda: os.getenv("DISCORD_TOKEN", ""))
    sss_url:           str   = field(default_factory=lambda: os.getenv("SSS_URL",          "https://tanitim.m2-board.com/sss"))
    site_url:          str   = field(default_factory=lambda: os.getenv("SITE_URL",         "https://tanitim.m2-board.com"))
    gif_url:           str   = field(default_factory=lambda: os.getenv("GIF_URL",          "https://i.imgur.com/XXXX.gif"))
    discord_davet_url: str   = field(default_factory=lambda: os.getenv("DISCORD_DAVET_URL","https://discord.gg/awgames"))
    admin_rol_adi:    str   = field(default_factory=lambda: os.getenv("ADMIN_ROL_ADI", "Yönetici"))

    # ── Embed renkleri ────────────────────────────────────────────────────────
    renkler: Dict[str, int] = field(default_factory=lambda: {
        "altin":   0xC9A84C,
        "yesil":   0x2ECC71,
        "kirmizi": 0xE74C3C,
        "mavi":    0x3498DB,
        "turuncu": 0xFF6B35,
        "pembe":   0xE91E8C,
        "mor":     0x9B59B6,
    })

    # ── DM rate-limit ─────────────────────────────────────────────────────────
    dm_bekleme: float = 0.5

    # ══════════════════════════════════════════════════════════════════════════
    # STATUS SİSTEMİ
    # ══════════════════════════════════════════════════════════════════════════

    status_aralik_dakika: int = 3

    status_listesi: List[Tuple[str, str]] = field(default_factory=lambda: [
        ("playing",   "M2Board | AWGames Efsanesi"),
        ("watching",  "6 Mart 21:00'da açılıyor!"),
        ("competing", "/sss ile sıkça sorulan soruları öğren"),
        ("watching",  "tanitim.m2-board.com"),
        ("listening", "/ticket ile bizimle hızlıca iletişime geç"),
        ("playing",   "/öneri veya /şikayet ile bize bildirim sağla"),
        ("competing", "Liderlik tablosu seni bekliyor"),
        ("watching",  "/yardım ile bot menüsünü açabilirsin"),
    ])

    # Rol verilince N saniye boyunca özel status gösterilir
    rol_status_sure: int = 300

    rol_status_map: Dict[str, Tuple[str, str]] = field(default_factory=lambda: {
        "efsane":      ("competing", "⚔️ Yeni bir Efsane aramıza katıldı!"),
        "moderatör":   ("watching",  "🛡️ Yeni moderatör göreve başladı!"),
        "beta oyuncu": ("playing",   "🎮 Beta oyuncusu sunucuya katıldı!"),
        "vip":         ("listening", "👑 VIP üyemiz hoş geldi!"),
        "partner":     ("watching",  "🤝 Yeni partnerimizi karşılayalım!"),
    })

    # ══════════════════════════════════════════════════════════════════════════
    # TİCKET SİSTEMİ
    # ══════════════════════════════════════════════════════════════════════════

    ticket_kanal_id: int = field(default_factory=lambda: int(os.getenv("TICKET_KANAL_ID", "0")))

    ticket_kategori_idleri: Dict[str, int] = field(default_factory=lambda: {
        "teknik_destek":         int(os.getenv("KATEGORI_TEKNIK",   "0")),
        "sikayet":               int(os.getenv("KATEGORI_SIKAYET",  "0")),
        "oneri":                 int(os.getenv("KATEGORI_ONERI",    "0")),
        "nesne_market":          int(os.getenv("KATEGORI_MARKET",   "0")),
        "zindan_iade":           int(os.getenv("KATEGORI_ZINDAN",   "0")),
    })

    ticket_log_kanal_id: int = field(default_factory=lambda: int(os.getenv("TICKET_LOG_KANAL_ID", "0")))
    ticket_transcript_kanal_id: int = field(default_factory=lambda: int(os.getenv("TICKET_TRANSCRIPT_KANAL_ID", "0")))

    ticket_support_rol_idleri: List[int] = field(default_factory=lambda: [
        int(x) for x in os.getenv("TICKET_SUPPORT_ROL_IDLERI", "0").split(",") if x.strip().isdigit()
    ])

    max_ticket_per_user: int = 1

    ticket_secenekleri: List[Dict] = field(default_factory=lambda: [
        {
            "label":       "Teknik Destek",
            "description": "Oyun içi teknik sorunlar için",
            "value":       "teknik_destek",
            "emoji":       "<:teknik:1478527729329639485>",
        },
        {
            "label":       "Nesne Market Sorunları",
            "description": "Market ile ilgili sorunlar için",
            "value":       "nesne_market",
            "emoji":       "<a:nesnemarket:1478390167310958734>",
        },
        {
            "label":       "Zindan İade",
            "description": "Zindan iade talepleri için",
            "value":       "zindan_iade",
            "emoji":       "<:dungeon:1478527882765533374>",
        },
    ])

    # ══════════════════════════════════════════════════════════════════════════
    # BAŞVURU SİSTEMİ
    # ══════════════════════════════════════════════════════════════════════════

    oneri_kanal_id:  int = field(default_factory=lambda: int(os.getenv("ONERI_KANAL_ID",  "0")))
    sikayet_kanal_id: int = field(default_factory=lambda: int(os.getenv("SIKAYET_KANAL_ID", "0")))
    etkinlik_storage_kanal_id: int = field(default_factory=lambda: int(os.getenv("ETKINLIK_STORAGE_KANAL_ID", "0")))
    basvuru_kanal_id: int = field(default_factory=lambda: int(os.getenv("BASVURU_KANAL_ID", "0")))

    basvuru_inceleme_kanallar: Dict[str, int] = field(default_factory=lambda: {
        "staff":      int(os.getenv("BASVURU_INCELEME_STAFF",     "0")),
        "moderator":  int(os.getenv("BASVURU_INCELEME_MODERATOR", "0")),
        "partner":    int(os.getenv("BASVURU_INCELEME_PARTNER",   "0")),
    })

    basvuru_inceleme_rol_idleri: Dict[str, int] = field(default_factory=lambda: {
        "staff":      int(os.getenv("BASVURU_ROL_STAFF",     "0")),
        "moderator":  int(os.getenv("BASVURU_ROL_MODERATOR", "0")),
        "partner":    int(os.getenv("BASVURU_ROL_PARTNER",   "0")),
    })

    basvuru_sorulari: Dict[str, List[str]] = field(default_factory=lambda: {
        "staff": [
            "Adın ve yaşın nedir?",
            "Günde kaç saat zaman ayırabilirsin?",
            "Daha önce staff deneyimin var mı? Açıkla.",
            "Neden M2Board Staff ekibine katılmak istiyorsun?",
            "Kendini kısaca tanıt.",
        ],
        "moderator": [
            "<a:whitearrow:1478394670856933429> Discord adınız?",
            "<a:whitearrow:1478394670856933429> Hangi saat dilimlerinde aktif olabilirsiniz? (Örnek: 15:00–22:00)",
            "<a:whitearrow:1478394670856933429> Kendinizden kısaca bahseder misiniz? Yaşınız, okul/iş durumunuz ve ilgi alanlarınız nelerdir?",
            "<a:whitearrow:1478394670856933429> Stres yönetimi konusunda kendinizi nasıl değerlendiriyorsunuz? Zorlu bir durumla karşılaştığınızda nasıl yaklaşırsınız?",
            "<a:whitearrow:1478394670856933429> Sinirli veya agresif bir oyuncuyla karşılaştığınızda nasıl bir tutum sergilersiniz?",
            "<a:whitearrow:1478394670856933429> Daha önce herhangi bir toplulukta görev aldınız mı? Hangi platformlardaydı ve ayrılma nedeniniz neydi?",
            "<a:whitearrow:1478394670856933429> Sizi diğer adaylardan ayıran özellikleriniz nelerdir?",
            "<a:whitearrow:1478394670856933429> Bir oyuncu size 'Bu oyunu bırakıyorum, çok zor.' dedi. Yetkili olarak bu duruma nasıl yaklaşırsınız?",
        ],
        "partner": [
            "Kanal adınız nedir?",
            "Hangi platformdasınız? (Kick, Twitch, YouTube, TikTok)",
            "Kanal istatistiğinizi önizlemeye açık bir bağlantı ile bizimle paylaşın.",
            "Çalışma beklentiniz nedir? (Ücretli / Ücretsiz / Bağlı EP karşılığında)",
            "Neden bizi tercih ediyorsunuz?",
        ],
    })

    # ══════════════════════════════════════════════════════════════════════════
    # VERİFİCATİON SİSTEMİ
    # ══════════════════════════════════════════════════════════════════════════

    verify_kanal_id:         int = field(default_factory=lambda: int(os.getenv("VERIFY_KANAL_ID",         "0")))
    verify_log_kanal_id:     int = field(default_factory=lambda: int(os.getenv("VERIFY_LOG_KANAL_ID",     "0")))
    verify_edilmemis_rol_id: int = field(default_factory=lambda: int(os.getenv("VERIFY_EDILMEMIS_ROL_ID", "0")))
    verify_edilmis_rol_id:   int = field(default_factory=lambda: int(os.getenv("VERIFY_EDILMIS_ROL_ID",   "0")))

    # ══════════════════════════════════════════════════════════════════════════
    # AUTORESPONDER
    # ══════════════════════════════════════════════════════════════════════════

    # Format: {"anahtar_kelime": "cevap"}
    # Büyük/küçük harf önemsiz. Mesaj bu kelimeyi içeriyorsa cevap verilir.
    autoresponder: Dict[str, str] = field(default_factory=lambda: {})

    # Autoresponder'ın görmezden geleceği kanal ID'leri
    autoresponder_ignore_kanal_idleri: List[int] = field(default_factory=lambda: [
        int(x) for x in os.getenv("AR_IGNORE_KANAL_IDLERI", "0").split(",") if x.strip().isdigit()
    ])
