"""Create deterministic Android and Play Store artwork from the master icon."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = PROJECT_ROOT / "assets"
STORE_ROOT = PROJECT_ROOT / "store-assets"
MASTER_ICON = ASSET_ROOT / "app-icon-source.png"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "segoeuib.ttf" if bold else "segoeui.ttf"
    path = Path("C:/Windows/Fonts") / name
    if path.is_file():
        return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def vertical_gradient(size: tuple[int, int]) -> Image.Image:
    width, height = size
    top = (32, 31, 73)
    bottom = (17, 87, 98)
    image = Image.new("RGB", size)
    draw = ImageDraw.Draw(image)
    for y in range(height):
        factor = y / max(1, height - 1)
        color = tuple(
            round(start + (end - start) * factor) for start, end in zip(top, bottom)
        )
        draw.line((0, y, width, y), fill=color)
    return image


def contain_square(image: Image.Image, side: int) -> Image.Image:
    return image.convert("RGBA").resize((side, side), Image.Resampling.LANCZOS)


def main() -> None:
    if not MASTER_ICON.is_file():
        raise SystemExit(f"Ana ikon eksik: {MASTER_ICON}")
    STORE_ROOT.mkdir(parents=True, exist_ok=True)
    master = Image.open(MASTER_ICON)

    icon_1024 = contain_square(master, 1024)
    icon_1024.save(ASSET_ROOT / "icon-1024.png", optimize=True)
    icon_512 = contain_square(master, 512)
    icon_512.save(ASSET_ROOT / "icon.png", optimize=True)
    icon_512.save(STORE_ROOT / "app-icon-512.png", optimize=True)
    icon_512.save(
        ASSET_ROOT / "neon-hands.ico",
        format="ICO",
        sizes=((16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)),
    )

    splash = vertical_gradient((1080, 1920)).convert("RGBA")
    glow = Image.new("RGBA", splash.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse((120, 500, 960, 1340), fill=(112, 231, 218, 38))
    glow = glow.filter(ImageFilter.GaussianBlur(90))
    splash = Image.alpha_composite(splash, glow)
    splash_icon = contain_square(master, 690)
    splash.alpha_composite(splash_icon, ((1080 - 690) // 2, 545))
    splash_draw = ImageDraw.Draw(splash)
    title_font = font(76, bold=True)
    subtitle_font = font(29, bold=True)
    title = "NEON HANDS"
    subtitle = "ROCK  •  PAPER  •  SCISSORS"
    title_box = splash_draw.textbbox((0, 0), title, font=title_font)
    sub_box = splash_draw.textbbox((0, 0), subtitle, font=subtitle_font)
    splash_draw.text(
        ((1080 - (title_box[2] - title_box[0])) / 2, 1285),
        title,
        font=title_font,
        fill=(255, 249, 235, 255),
    )
    splash_draw.text(
        ((1080 - (sub_box[2] - sub_box[0])) / 2, 1380),
        subtitle,
        font=subtitle_font,
        fill=(157, 231, 218, 255),
    )
    splash.convert("RGB").save(ASSET_ROOT / "presplash.png", optimize=True, quality=95)

    feature = vertical_gradient((1024, 500)).convert("RGBA")
    feature_glow = Image.new("RGBA", feature.size, (0, 0, 0, 0))
    feature_draw = ImageDraw.Draw(feature_glow)
    feature_draw.ellipse((-120, -170, 570, 610), fill=(112, 231, 218, 42))
    feature_draw.ellipse((650, -150, 1150, 470), fill=(246, 130, 142, 34))
    feature = Image.alpha_composite(
        feature, feature_glow.filter(ImageFilter.GaussianBlur(75))
    )
    feature_icon = contain_square(master, 425)
    feature.alpha_composite(feature_icon, (38, 37))
    draw = ImageDraw.Draw(feature)
    headline_font = font(61, bold=True)
    tag_font = font(25, bold=True)
    draw.text(
        (488, 174),
        "NEON HANDS",
        font=headline_font,
        fill=(255, 249, 235, 255),
    )
    draw.text(
        (492, 255),
        "ROCK  •  PAPER  •  SCISSORS",
        font=tag_font,
        fill=(157, 231, 218, 255),
    )
    feature.convert("RGB").save(
        STORE_ROOT / "feature-graphic-1024x500.png",
        optimize=True,
        quality=95,
    )

    print("Android and Play Store artwork prepared.")


if __name__ == "__main__":
    main()
