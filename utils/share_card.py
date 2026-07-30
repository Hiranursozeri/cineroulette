"""
Paylaşılabilir Sonuç Kartı
---------------------------
Çarktan/kart destesinden çıkan filmi, poster + başlık + puan + CineRoulette
markası içeren indirilebilir bir görsele (PNG) dönüştürür.
"""

import io
import os
from typing import Optional

import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps

CARD_WIDTH = 720
CARD_HEIGHT = 1080
ACCENT_COLOR = (229, 9, 20)       # #e50914 (uygulamanın kırmızı vurgusu)
BG_COLOR = (20, 20, 20)           # #141414
RATING_COLOR = (245, 197, 24)     # #f5c518

_ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "fonts")

# ÖNEMLİ: Sunucu ortamı (ör. Streamlit Community Cloud, Linux) hangi
# fontların kurulu olduğunu garanti etmez. Windows'a özel yollar (arialbd.ttf
# vb.) sadece yerel geliştirmede işe yarar; canlıda hiçbiri bulunamazsa
# Pillow'un çok temel yedek fontuna düşülür — bu da ğ, ş, ı, ö, ü, ç gibi
# Türkçe karakterleri düzgün çizemez. Bunu kesin olarak çözmek için, projeye
# gömülü bir font (DejaVu Sans — Türkçe karakterleri tam destekler) İLK
# sırada deneniyor; sistem fontları sadece onun da bulunamadığı (ör. dosya
# eksikse) durumlarda yedek olarak kalıyor.
_FONT_CANDIDATES_BOLD = [
    os.path.join(_ASSETS_DIR, "DejaVuSans-Bold.ttf"),
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/segoeuib.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]
_FONT_CANDIDATES_REGULAR = [
    os.path.join(_ASSETS_DIR, "DejaVuSans.ttf"),
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]


def _load_font(candidates: list[str], size: int) -> ImageFont.FreeTypeFont:
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        # Eski Pillow sürümlerinde load_default() bir 'size' parametresi almaz.
        return ImageFont.load_default()


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), trial, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def generate_share_card(winner: dict, cta_text: str = "Çarkı sen de çevir!") -> Optional[bytes]:
    """
    Çarktan/kart destesinden çıkan içeriği paylaşılabilir bir PNG görsele
    dönüştürür. Poster indirilemezse düz koyu bir arka planla devam eder
    (tamamen başarısız olursa None döner, çağıran taraf bunu ele almalı).

    `cta_text`: alt kısımdaki kısa çağrı metni — hangi seçim modundan
    (çark/kart) geldiğine göre çağıran taraf farklı bir metin geçebilir.
    """
    try:
        canvas = Image.new("RGB", (CARD_WIDTH, CARD_HEIGHT), BG_COLOR)

        poster_url = winner.get("poster_url")
        if poster_url:
            try:
                resp = requests.get(poster_url, timeout=8)
                resp.raise_for_status()
                poster = Image.open(io.BytesIO(resp.content)).convert("RGB")
                poster = ImageOps.fit(poster, (CARD_WIDTH, CARD_HEIGHT), method=Image.LANCZOS)
                canvas.paste(poster, (0, 0))
            except Exception:
                pass  # Poster gelmezse düz koyu arka planla devam ediyoruz

        # Alt kısımda yazının okunabilmesi için koyulaşan bir gradyan katmanı
        overlay = Image.new("RGBA", (CARD_WIDTH, CARD_HEIGHT), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        gradient_start = int(CARD_HEIGHT * 0.45)
        for y in range(gradient_start, CARD_HEIGHT):
            progress = (y - gradient_start) / (CARD_HEIGHT - gradient_start)
            alpha = int(min(255, progress * 235))
            overlay_draw.line([(0, y), (CARD_WIDTH, y)], fill=(10, 10, 10, alpha))
        canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")

        draw = ImageDraw.Draw(canvas)

        # Üstte küçük marka etiketi
        brand_font = _load_font(_FONT_CANDIDATES_BOLD, 28)
        draw.text((40, 40), "CINEROULETTE", font=brand_font, fill=ACCENT_COLOR)

        # Alt kısımda başlık (uzunsa otomatik satır kaydırma)
        title = winner.get("title", "Bilinmiyor")
        title_font = _load_font(_FONT_CANDIDATES_BOLD, 52)
        lines = _wrap_text(draw, title, title_font, CARD_WIDTH - 80)
        y = CARD_HEIGHT - 220 - (len(lines) - 1) * 60
        for line in lines:
            draw.text((40, y), line, font=title_font, fill=(255, 255, 255))
            y += 60

        # Puan
        rating_font = _load_font(_FONT_CANDIDATES_REGULAR, 34)
        vote = winner.get("vote_average", 0) or 0
        draw.text((40, CARD_HEIGHT - 90), f"Puan: {vote:.1f} / 10", font=rating_font, fill=RATING_COLOR)

        # Alt slogan
        caption_font = _load_font(_FONT_CANDIDATES_REGULAR, 24)
        draw.text((40, CARD_HEIGHT - 45), cta_text, font=caption_font, fill=(210, 210, 210))

        buf = io.BytesIO()
        canvas.save(buf, format="PNG")
        return buf.getvalue()

    except Exception as e:
        print(f"[ShareCard] Görsel oluşturma hatası: {e}")
        return None