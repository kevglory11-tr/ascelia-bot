"""utils/transcript.py — Ticket kapandığında HTML transcript üretir ve online link oluşturur."""

import html
import logging
from datetime import datetime, timezone

import discord

log = logging.getLogger("transcript")


def _avatar(user: discord.Member | discord.User) -> str:
    return str(user.display_avatar.url) if user.display_avatar else ""


async def online_yukle(html_icerik: str) -> str | None:
    """Online yükleme devre dışı — Discord CDN kullanılıyor."""
    return None


async def html_olustur(kanal: discord.TextChannel, ticket_no: str, acilma_tarihi: datetime) -> str:
    """
    Kanalın tüm mesajlarını okuyup profesyonel bir HTML dosyası döndürür.
    """
    mesajlar = []
    async for msg in kanal.history(limit=None, oldest_first=True):
        mesajlar.append(msg)

    sure = datetime.now(timezone.utc) - acilma_tarihi
    sure_str = f"{sure.days}g {sure.seconds // 3600}s {(sure.seconds % 3600) // 60}d"

    satirlar = []
    for msg in mesajlar:
        if msg.author.bot and not msg.embeds:
            continue
        zaman = msg.created_at.strftime("%d.%m.%Y %H:%M")
        icerik = html.escape(msg.content) if msg.content else ""

        embed_html = ""
        for emb in msg.embeds:
            parts = []
            if emb.title:
                parts.append(f'<div class="embed-title">{html.escape(emb.title)}</div>')
            if emb.description:
                parts.append(f'<div class="embed-desc">{html.escape(emb.description)}</div>')
            for field in emb.fields:
                parts.append(
                    f'<div class="embed-field"><span class="field-name">{html.escape(field.name)}</span>'
                    f'<span class="field-value">{html.escape(field.value)}</span></div>'
                )
            renk = f"#{emb.color.value:06x}" if emb.color else "#C9A84C"
            embed_html += f'<div class="embed" style="border-left:4px solid {renk}">{"".join(parts)}</div>'

        ek_html = ""
        for ek in msg.attachments:
            if ek.content_type and ek.content_type.startswith("image/"):
                ek_html += f'<img src="{ek.url}" class="attachment" alt="ek">'
            else:
                ek_html += f'<a href="{ek.url}" class="attachment-link" target="_blank">📎 {html.escape(ek.filename)}</a>'

        rol_rengi = "#C9A84C"
        if hasattr(msg.author, "roles"):
            for rol in reversed(msg.author.roles):
                if rol.color.value:
                    rol_rengi = f"#{rol.color.value:06x}"
                    break

        avatar_url = _avatar(msg.author)
        satirlar.append(f"""
        <div class="message">
            <img class="avatar" src="{avatar_url}" alt="" onerror="this.style.display='none'">
            <div class="msg-content">
                <div class="msg-header">
                    <span class="username" style="color:{rol_rengi}">{html.escape(msg.author.display_name)}</span>
                    <span class="timestamp">{zaman}</span>
                </div>
                {"<p class='text'>" + icerik + "</p>" if icerik else ""}
                {embed_html}
                {ek_html}
            </div>
        </div>""")

    mesaj_html = "\n".join(satirlar) if satirlar else "<p style='color:#888;text-align:center'>Mesaj bulunamadı.</p>"

    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Transcript — {html.escape(ticket_no)}</title>
<style>
  :root {{
    --bg: #1a1a2e; --surface: #16213e; --surface2: #0f3460;
    --gold: #C9A84C; --text: #e0e0e0; --muted: #8888aa;
    --border: #2a2a4a;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--bg); color: var(--text); font-family: 'Segoe UI', sans-serif; min-height: 100vh; }}

  header {{
    background: linear-gradient(135deg, #0f3460, #1a1a2e);
    border-bottom: 2px solid var(--gold);
    padding: 24px 32px;
    display: flex;
    align-items: center;
    gap: 20px;
  }}
  .header-icon {{ font-size: 2.5rem; }}
  .header-info h1 {{ font-size: 1.4rem; color: var(--gold); letter-spacing: 1px; }}
  .header-info p {{ color: var(--muted); font-size: 0.85rem; margin-top: 4px; }}

  .meta-bar {{
    display: flex; gap: 16px; flex-wrap: wrap;
    background: var(--surface); border-bottom: 1px solid var(--border);
    padding: 12px 32px;
  }}
  .meta-item {{
    background: var(--surface2); border-radius: 6px;
    padding: 6px 14px; font-size: 0.8rem; color: var(--muted);
  }}
  .meta-item span {{ color: var(--gold); font-weight: 600; }}

  .messages {{ max-width: 900px; margin: 0 auto; padding: 24px 16px; }}

  .message {{
    display: flex; gap: 14px;
    padding: 10px 14px; border-radius: 8px;
    margin-bottom: 4px; transition: background .15s;
  }}
  .message:hover {{ background: var(--surface); }}

  .avatar {{
    width: 40px; height: 40px; border-radius: 50%;
    object-fit: cover; flex-shrink: 0; margin-top: 2px;
    border: 2px solid var(--border);
  }}
  .msg-content {{ flex: 1; min-width: 0; }}
  .msg-header {{ display: flex; align-items: baseline; gap: 10px; margin-bottom: 4px; }}
  .username {{ font-weight: 700; font-size: 0.95rem; }}
  .timestamp {{ color: var(--muted); font-size: 0.75rem; }}
  .text {{ font-size: 0.9rem; line-height: 1.5; word-break: break-word; white-space: pre-wrap; }}

  .embed {{
    background: var(--surface); border-radius: 4px;
    padding: 10px 14px; margin-top: 6px; max-width: 520px;
  }}
  .embed-title {{ font-weight: 700; color: var(--gold); margin-bottom: 6px; }}
  .embed-desc {{ font-size: 0.88rem; line-height: 1.5; color: var(--text); }}
  .embed-field {{ margin-top: 8px; }}
  .field-name {{ display: block; font-weight: 600; font-size: 0.8rem; color: var(--muted); }}
  .field-value {{ display: block; font-size: 0.88rem; }}

  .attachment {{ max-width: 300px; max-height: 200px; border-radius: 6px; margin-top: 6px; display: block; }}
  .attachment-link {{ color: var(--gold); font-size: 0.85rem; display: block; margin-top: 4px; }}

  footer {{
    text-align: center; padding: 20px;
    color: var(--muted); font-size: 0.78rem;
    border-top: 1px solid var(--border);
    margin-top: 32px;
  }}
</style>
</head>
<body>
<header>
  <div class="header-icon">⚔️</div>
  <div class="header-info">
    <h1>Ascelia Bot — Ticket Transkripti</h1>
    <p>#{html.escape(ticket_no)} • {html.escape(kanal.name)}</p>
  </div>
</header>
<div class="meta-bar">
  <div class="meta-item">📅 Açılış: <span>{html.escape(acilma_tarihi.strftime('%d.%m.%Y %H:%M'))}</span></div>
  <div class="meta-item">🔒 Kapanış: <span>{datetime.now(timezone.utc).strftime('%d.%m.%Y %H:%M')}</span></div>
  <div class="meta-item">⏱️ Süre: <span>{html.escape(sure_str)}</span></div>
  <div class="meta-item">💬 Mesaj: <span>{len(mesajlar)}</span></div>
  <div class="meta-item">📁 Kanal: <span>{html.escape(kanal.name)}</span></div>
</div>
<div class="messages">
{mesaj_html}
</div>
<footer>Ascelia Bot • AWGames — Bu transkript otomatik olarak oluşturulmuştur.</footer>
</body>
</html>"""
