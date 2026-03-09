# ⚔️ Metin2Board Bot — v3

AWGames Metin2Board sunucusu için geliştirilmiş tam özellikli Discord botu.
Harici hiçbir servise ihtiyaç duymaz — her şey kendi içinde çalışır.

---

## 📦 Özellikler

| Modül | Açıklama |
|---|---|
| 🎫 **Ticket** | Dropdown menü, 5 kategori, transcript, log kanalı |
| 📝 **Başvuru** | Staff / Mod / Partner — DM formu, kabul/red butonları |
| ✅ **Doğrulama** | Butona tıkla, rol al — yeni üyeye otomatik rol |
| 🤖 **Autoresponder** | Anahtar kelimeye otomatik yanıt |
| 🎮 **Status** | Otomatik dönen status, rol tetikleyicili status |
| 📣 **Duyuru** | Tüm üyelere DM — duyuru / etkinlik / çekiliş / güncelleme |
| 📜 **SSS** | SSS sayfasına yönlendirme |

---

## 🚀 Kurulum

### 1. Depoyu klonla
```bash
git clone <repo-url>
cd m2board-v3
```

### 2. Bağımlılıkları yükle
```bash
pip install -r requirements.txt
```

### 3. Ortam değişkenlerini ayarla
```bash
cp .env.example .env
# .env dosyasını düzenle, değerleri doldur
```

### 4. Botu başlat
```bash
python main.py
```

---

## ⚙️ Yapılandırma

### .env Dosyası — Zorunlu Ayarlar

```env
DISCORD_TOKEN=bot_tokenin
ADMIN_ROL_ADI=Yönetici

# Ticket kategorileri (Discord kategori ID'leri)
KATEGORI_TEKNIK=123456789
KATEGORI_SIKAYET=123456789
KATEGORI_ONERI=123456789
KATEGORI_MARKET=123456789
KATEGORI_ZINDAN=123456789

# Log kanalları
TICKET_LOG_KANAL_ID=123456789
TICKET_TRANSCRIPT_KANAL_ID=123456789

# Doğrulama
VERIFY_EDILMEMIS_ROL_ID=123456789
VERIFY_EDILMIS_ROL_ID=123456789

# Başvuru inceleme kanalları
BASVURU_INCELEME_STAFF=123456789
BASVURU_INCELEME_MODERATOR=123456789
BASVURU_INCELEME_PARTNER=123456789
```

### config/settings.py — Metin Ayarları

| Değişken | Açıklama |
|---|---|
| `status_listesi` | Dönen statuslar listesi |
| `rol_status_map` | Hangi rol → hangi status |
| `ticket_secenekleri` | Dropdown seçenekleri |
| `basvuru_sorulari` | Her başvuru türü için sorular |
| `autoresponder` | Kelime → cevap eşleşmeleri |

---

## 🎯 Komutlar

### Genel
| Komut | Açıklama |
|---|---|
| `/yardım` | Tüm komutları göster |
| `/sss` | SSS sayfasına yönlendir |

### Ticket
| Komut | Açıklama |
|---|---|
| `/ticket` | Yeni ticket aç |
| `/ticket-panel-gonder` | Kalıcı panel gönder *(Admin)* |
| `/ticket-kapat` | Ticketi kapat *(ticket içinde)* |
| `/ticket-ekle @kullanici` | Tickete kullanıcı ekle |
| `/ticket-cikar @kullanici` | Ticketten kullanıcı çıkar |

### Başvuru
| Komut | Açıklama |
|---|---|
| `/başvuru` | Başvuru formu aç |
| `/başvuru-panel-gonder` | Kalıcı panel gönder *(Admin)* |

### Doğrulama
| Komut | Açıklama |
|---|---|
| `/doğrula-panel` | Doğrulama paneli gönder *(Admin)* |

### Admin — Duyurular
| Komut | Açıklama |
|---|---|
| `/duyuru` | Tüm üyelere duyuru DM'i |
| `/etkinlik` | Etkinlik duyurusu |
| `/çekiliş` | Çekiliş duyurusu |
| `/güncelleme` | Güncelleme notu |

### Admin — Status
| Komut | Açıklama |
|---|---|
| `/status` | Manuel status ayarla |
| `/status-oto` | Otomatik rotasyona dön |
| `/status-listesi` | Tüm statusları göster |

---

## 🏗️ Proje Yapısı

```
m2board-v3/
├── main.py                 # Giriş noktası
├── requirements.txt
├── Procfile               # Railway için
├── .env.example
├── config/
│   └── settings.py        # ← Tüm ayarlar buradan
├── utils/
│   ├── logger.py          # Loglama sistemi
│   ├── permissions.py     # Yetki kontrolleri
│   ├── embeds.py          # Embed şablonları
│   ├── dm_sender.py       # Toplu DM motoru
│   └── transcript.py      # HTML transcript üretici
└── cogs/
    ├── yardim.py
    ├── sss.py
    ├── duyuru.py
    ├── status.py
    ├── ticket.py          # Tam ticket sistemi
    ├── basvuru.py         # Başvuru sistemi
    ├── dogrulama.py       # Verification
    └── autoresponder.py
```

---

## 🚂 Railway Deployment

1. Railway'de yeni proje oluştur
2. GitHub reposunu bağla
3. Environment Variables kısmına `.env` içeriğini gir
4. Deploy et — `Procfile` otomatik algılanır

---

## ➕ Yeni Başvuru Türü Eklemek

`config/settings.py` dosyasında iki yere ekle:

```python
# basvuru_sorulari içine:
"yeni_tur": [
    "Soru 1?",
    "Soru 2?",
],

# basvuru_inceleme_kanallar içine:
"yeni_tur": int(os.getenv("BASVURU_INCELEME_YENI_TUR", "0")),
```

`cogs/basvuru.py` içinde `BASVURU_ETIKETLER` ve `BasvuruDropdown`'a da ekle:
```python
BASVURU_ETIKETLER["yeni_tur"] = ("🆕", "Yeni Başvuru", 0xFF6B35)
```

---

## ➕ Yeni Autoresponder Kelimesi Eklemek

`config/settings.py` → `autoresponder` sözlüğüne ekle:

```python
"aranacak kelime": "verilecek cevap",
```

Yeniden başlatmaya gerek yok — bir sonraki mesajda aktif olur.

---

*Metin2Board • AWGames*
