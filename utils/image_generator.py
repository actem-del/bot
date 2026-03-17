from __future__ import annotations

import io
from pathlib import Path
from typing import Iterable

import discord
from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError

from utils.helpers import fmt_dt, fmt_hours
from utils.xp_system import level_from_xp, progress_in_level


BASE_DIR = Path(__file__).resolve().parent.parent
FONT_REGULAR = BASE_DIR / "fonts" / "DejaVuSans.ttf"
FONT_BOLD = BASE_DIR / "fonts" / "DejaVuSans-Bold.ttf"
BG_PATH = BASE_DIR / "assets" / "background.png"
OVERLAY_PATH = BASE_DIR / "assets" / "overlay.png"


def _iter_font_candidates(bold: bool) -> Iterable[Path | str]:
    preferred = [FONT_BOLD, FONT_REGULAR] if bold else [FONT_REGULAR, FONT_BOLD]
    for path in preferred:
        yield path

    fonts_dir = BASE_DIR / "fonts"
    if fonts_dir.exists():
        patterns = ("*.ttf", "*.otf", "*.TTF", "*.OTF")
        for pattern in patterns:
            for path in sorted(fonts_dir.glob(pattern)):
                yield path

    system_fallbacks = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "DejaVuSans-Bold.ttf",
        "DejaVuSans.ttf",
        "Arial Bold.ttf",
        "Arial.ttf",
    ]
    for name in system_fallbacks:
        yield name


def load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    for path in _iter_font_candidates(bold):
        try:
            return ImageFont.truetype(str(path), size)
        except OSError:
            continue
    return ImageFont.load_default()


def fit_text(draw: ImageDraw.ImageDraw, text: str, max_width: int, start_size: int) -> tuple[ImageFont.ImageFont, str]:
    for size in range(start_size, 14, -1):
        font = load_font(size, bold=True)
        if draw.textlength(text, font=font) <= max_width:
            return font, text
    font = load_font(14, bold=True)
    value = text
    while len(value) > 3 and draw.textlength(value + "...", font=font) > max_width:
        value = value[:-1]
    return font, value + "..."


def _safe_open_image(path: Path, mode: str) -> Image.Image | None:
    if not path.exists():
        return None

    try:
        return Image.open(path).convert(mode)
    except (UnidentifiedImageError, OSError, ValueError):
        print(f"[WARN] Invalid image file ignored: {path}")
        return None


async def render_profile_card(member: discord.Member, profile: dict) -> io.BytesIO:
    bg = _safe_open_image(BG_PATH, "RGB")
    card = bg.resize((1366, 768)) if bg else Image.new("RGB", (1366, 768), (9, 9, 9))

    draw = ImageDraw.Draw(card)
    overlay = _safe_open_image(OVERLAY_PATH, "RGBA")
    if overlay:
        overlay = overlay.resize(card.size)
        card.paste(overlay, (0, 0), overlay)

    avatar_bytes = await member.display_avatar.replace(size=256).read()
    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGB").resize((180, 180))
    card.paste(avatar, (90, 180))
    draw.rectangle((86, 176, 274, 364), outline=(220, 35, 35), width=3)

    xp = int(profile.get("xp", 0))
    voice_seconds = int(profile.get("voice_seconds", 0))
    messages = int(profile.get("messages", 0))
    coins = int(profile.get("coins", 0))

    level = level_from_xp(xp)
    progress, total = progress_in_level(xp)

    draw.text((90, 70), "REDCORE STYLES", fill=(220, 35, 35), font=load_font(30, True))
    draw.text((1100, 70), "BLACK // RED", fill=(220, 35, 35), font=load_font(30, True))

    name_font, name_text = fit_text(draw, member.display_name.upper(), 640, 54)
    draw.text((300, 200), name_text, fill=(255, 55, 55), font=name_font)
    draw.text((300, 255), f"ID: {member.id}", fill=(185, 185, 185), font=load_font(30))

    draw.text((90, 415), f"{level}  УРОВЕНЬ", fill=(245, 245, 245), font=load_font(62, True))
    draw.text((900, 235), "$", fill=(220, 35, 35), font=load_font(60, True))
    draw.text((960, 235), f"{coins:,}".replace(",", " "), fill=(245, 245, 245), font=load_font(58, True))

    draw.text((900, 325), "XP", fill=(255, 110, 110), font=load_font(56, True))
    draw.text((995, 325), str(xp), fill=(245, 245, 245), font=load_font(52, True))

    x1, y1, width = 170, 475, 940
    draw.rectangle((x1, y1, x1 + width, y1 + 12), fill=(70, 70, 70))
    filled = int(width * (progress / max(total, 1)))
    draw.rectangle((x1, y1, x1 + filled, y1 + 12), fill=(220, 35, 35))
    draw.text((90, 520), "ПРОГРЕСС УРОВНЯ", fill=(160, 160, 160), font=load_font(38, True))
    draw.text((870, 440), f"XP {progress}/{total}", fill=(160, 160, 160), font=load_font(48, True))

    blocks = [
        ((90, 575, 670, 648), "ОНЛАЙН", fmt_hours(voice_seconds)),
        ((695, 575, 1275, 648), "ТОП РАНКЕР", str(level)),
        ((90, 662, 670, 735), "СООБЩЕНИЯ", str(messages)),
        ((695, 662, 1275, 735), "РОЛЬ", member.top_role.name if member.top_role else "Нет"),
    ]
    for x1b, y1b, x2b, y2b in [b[0] for b in blocks]:
        draw.polygon(
            [(x1b, y1b), (x2b - 16, y1b), (x2b, y1b + 16), (x2b, y2b - 16), (x2b - 16, y2b), (x1b, y2b)],
            fill=(16, 16, 16),
            outline=(110, 22, 22),
        )

    for block, label, value in blocks:
        x1b, y1b, x2b, _ = block
        draw.text((x1b + 18, y1b + 17), label, fill=(245, 245, 245), font=load_font(25, True))
        value_font, value_text = fit_text(draw, str(value), x2b - x1b - 220, 48)
        value_width = int(draw.textlength(value_text, font=value_font))
        draw.text((x2b - value_width - 18, y1b + 10), value_text, fill=(245, 245, 245), font=value_font)

    draw.text((300, 302), f"СОЗДАН: {fmt_dt(member.created_at)}", fill=(185, 185, 185), font=load_font(24))
    draw.text((300, 333), f"НА СЕРВЕРЕ: {fmt_dt(member.joined_at)}", fill=(185, 185, 185), font=load_font(24))

    output = io.BytesIO()
    card.save(output, format="PNG")
    output.seek(0)
    return output


async def render_love_profile_card(
    user_a: discord.abc.User,
    user_b: discord.abc.User,
    profile_a: dict,
    profile_b: dict,
) -> io.BytesIO:
    card = Image.new("RGB", (980, 520), (12, 12, 12))
    draw = ImageDraw.Draw(card)

    draw.rounded_rectangle((16, 16, 964, 504), radius=18, fill=(20, 20, 20), outline=(120, 20, 20), width=3)
    draw.rectangle((16, 90, 964, 94), fill=(120, 20, 20))
    draw.text((36, 36), "LOVE PROFILE // RED BLACK", fill=(230, 45, 45), font=load_font(34, True))

    a_bytes = await user_a.display_avatar.replace(size=256).read()
    b_bytes = await user_b.display_avatar.replace(size=256).read()
    avatar_a = Image.open(io.BytesIO(a_bytes)).convert("RGB").resize((110, 110))
    avatar_b = Image.open(io.BytesIO(b_bytes)).convert("RGB").resize((110, 110))
    card.paste(avatar_a, (44, 148))
    card.paste(avatar_b, (826, 148))
    draw.rectangle((40, 144, 158, 262), outline=(220, 40, 40), width=2)
    draw.rectangle((822, 144, 940, 262), outline=(220, 40, 40), width=2)

    draw.text((176, 150), f"{user_a.display_name} ❤️ {user_b.display_name}", fill=(245, 245, 245), font=load_font(36, True))

    total_voice = int(profile_a.get("voice_seconds", 0)) + int(profile_b.get("voice_seconds", 0))
    total_messages = int(profile_a.get("messages", 0)) + int(profile_b.get("messages", 0))
    total_xp = int(profile_a.get("xp", 0)) + int(profile_b.get("xp", 0))

    draw.text((176, 220), f"Совместный онлайн: {fmt_hours(total_voice)}", fill=(205, 205, 205), font=load_font(28, True))
    draw.text((176, 262), f"Сообщения пары: {total_messages}", fill=(205, 205, 205), font=load_font(28, True))
    draw.text((176, 304), f"XP пары: {total_xp}", fill=(255, 105, 105), font=load_font(30, True))

    draw.rounded_rectangle((44, 360, 936, 470), radius=12, fill=(15, 15, 15), outline=(95, 20, 20), width=2)
    draw.text((66, 390), "LoveRoom: доступ только для вашей пары (2 места)", fill=(240, 240, 240), font=load_font(28, True))

    out = io.BytesIO()
    card.save(out, format="PNG")
    out.seek(0)
    return out
