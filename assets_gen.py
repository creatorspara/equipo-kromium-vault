"""
Equipo Kromium - Brand Kit Asset Generation & Background Enhancement
=====================================================================
Generates high-resolution, perfectly corrected brand assets based on
the official 'Equipo Kromium' brand guidelines:
- Color Palette: #6C4DFF (Primary), #A78BFA (Secondary), #D1C4FF (Light), #0A0A0F (Base), #F5F5F7 (Text)
- Typography: Sora
- Tagline: Build · Open · Share
- Enhanced Background Patterns: Radiant purple volumetric glow, isometric grid lines, and angled ribbons
"""

import math
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont


ASSETS_DIR = Path("C:/Users/vaish/.gemini/antigravity/scratch/kromium_vault/assets")
ASSETS_DIR.mkdir(parents=True, exist_ok=True)


def draw_kromium_k(draw: ImageDraw.ImageDraw, offset_x: float, offset_y: float, scale: float, color: tuple):
    """
    Draws the geometric stylized 'K' monogram from Equipo Kromium:
    Consists of:
    1. Upper-left angled parallelogram stroke (slanted down-right)
    2. Lower-left angled parallelogram stroke (slanted down-right)
    3. Upper-right angled chevron stroke (slanted down-left towards center)
    4. Lower-right angled chevron stroke (slanted down-right from center)
    """
    # Coordinates normalized for a 100x100 bounding box
    # Left bar 1 (top diagonal):
    p1 = [
        (offset_x + 10 * scale, offset_y + 15 * scale),
        (offset_x + 35 * scale, offset_y + 15 * scale),
        (offset_x + 55 * scale, offset_y + 45 * scale),
        (offset_x + 30 * scale, offset_y + 45 * scale),
    ]
    # Left bar 2 (lower parallel diagonal):
    p2 = [
        (offset_x + 10 * scale, offset_y + 55 * scale),
        (offset_x + 35 * scale, offset_y + 55 * scale),
        (offset_x + 55 * scale, offset_y + 85 * scale),
        (offset_x + 30 * scale, offset_y + 85 * scale),
    ]
    # Right top bar (upper arm):
    p3 = [
        (offset_x + 65 * scale, offset_y + 15 * scale),
        (offset_x + 90 * scale, offset_y + 15 * scale),
        (offset_x + 55 * scale, offset_y + 50 * scale),
        (offset_x + 40 * scale, offset_y + 50 * scale),
    ]
    # Right bottom bar (lower arm):
    p4 = [
        (offset_x + 40 * scale, offset_y + 50 * scale),
        (offset_x + 60 * scale, offset_y + 50 * scale),
        (offset_x + 90 * scale, offset_y + 85 * scale),
        (offset_x + 65 * scale, offset_y + 85 * scale),
    ]

    for poly in [p1, p2, p3, p4]:
        draw.polygon(poly, fill=color)


def generate_app_icon():
    """Generates 512x512 app icon with rounded squircle and multi-size Windows .ico"""
    size = 512
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Rounded rectangle background #0A0A0F with subtle purple border #6C4DFF
    radius = 110
    draw.rounded_rectangle([(16, 16), (size - 16, size - 16)], radius=radius, fill=(10, 10, 15, 255), outline=(108, 77, 255, 180), width=4)

    # Ambient radial glow inside squircle
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    for r in range(180, 0, -10):
        alpha = int(45 * (1 - r / 180))
        glow_draw.ellipse([(size // 2 - r, size // 2 - r), (size // 2 + r, size // 2 + r)], fill=(108, 77, 255, alpha))
    glow = glow.filter(ImageFilter.GaussianBlur(25))
    img = Image.alpha_composite(img, glow)

    # Draw Kromium K logo centered
    draw = ImageDraw.Draw(img)
    # Centered at scale ~3.8
    scale = 3.6
    draw_kromium_k(draw, offset_x=85, offset_y=85, scale=scale, color=(108, 77, 255, 255))
    # Soft lavender highlight overlay on edges
    draw_kromium_k(draw, offset_x=86, offset_y=84, scale=scale * 0.98, color=(167, 139, 250, 120))

    # Save PNG
    icon_png_path = ASSETS_DIR / "app_icon.png"
    img.save(icon_png_path, "PNG")

    # Generate multi-size .ico file for Windows executable
    icon_ico_path = ASSETS_DIR / "app_icon.ico"
    ico_sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    img.save(icon_ico_path, format="ICO", sizes=ico_sizes)
    print(f"[✔] Generated {icon_png_path} and {icon_ico_path}")


def generate_enhanced_background():
    """
    Creates an enhanced, high-definition 1920x1080 background pattern:
    - Base #0A0A0F pitch black
    - Atmospheric radial glow in Equipo Kromium purple (#6C4DFF)
    - Isometric fine cybernetic lines
    - Large 3D angled geometric Kromium ribbon watermark
    """
    width, height = 1920, 1080
    bg = Image.new("RGBA", (width, height), (10, 10, 15, 255))

    # 1. Radial glow layers
    glow_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)

    # Primary glow center-right
    cx1, cy1 = 1400, 400
    for r in range(700, 0, -25):
        alpha = int(70 * (1 - r / 700))
        glow_draw.ellipse([(cx1 - r, cy1 - r), (cx1 + r, cy1 + r)], fill=(108, 77, 255, alpha))

    # Secondary glow bottom-left
    cx2, cy2 = 300, 800
    for r in range(500, 0, -25):
        alpha = int(45 * (1 - r / 500))
        glow_draw.ellipse([(cx2 - r, cy2 - r), (cx2 + r, cy2 + r)], fill=(167, 139, 250, alpha))

    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(60))
    bg = Image.alpha_composite(bg, glow_layer)

    # 2. Isometric fine cybernetic grid lines
    grid_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    grid_draw = ImageDraw.Draw(grid_layer)

    line_color = (108, 77, 255, 30)
    step = 80
    # Diagonal lines (45 degrees)
    for x in range(-height, width + height, step):
        grid_draw.line([(x, 0), (x + height, height)], fill=line_color, width=1)
        grid_draw.line([(x, height), (x + height, 0)], fill=(167, 139, 250, 18), width=1)

    # Horizontal subtle lines
    for y in range(0, height, step):
        grid_draw.line([(0, y), (width, y)], fill=(108, 77, 255, 14), width=1)

    bg = Image.alpha_composite(bg, grid_layer)

    # 3. Large stylized Kromium ribbon geometry (watermark on right)
    ribbon_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ribbon_draw = ImageDraw.Draw(ribbon_layer)
    draw_kromium_k(ribbon_draw, offset_x=1050, offset_y=150, scale=8.5, color=(108, 77, 255, 55))
    draw_kromium_k(ribbon_draw, offset_x=1060, offset_y=160, scale=8.4, color=(167, 139, 250, 35))
    ribbon_layer = ribbon_layer.filter(ImageFilter.GaussianBlur(8))
    bg = Image.alpha_composite(bg, ribbon_layer)

    # Save wallpaper
    bg_path = ASSETS_DIR / "enhanced_background.png"
    bg.save(bg_path, "PNG")
    print(f"[✔] Generated {bg_path}")


def generate_brand_banner():
    """Generates transparent logo banner for the UI and Web Header."""
    w, h = 900, 220
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw logo symbol on left
    draw_kromium_k(draw, offset_x=30, offset_y=25, scale=1.7, color=(108, 77, 255, 255))
    draw_kromium_k(draw, offset_x=31, offset_y=24, scale=1.68, color=(167, 139, 250, 160))

    # Save
    banner_path = ASSETS_DIR / "kromium_brand_mark.png"
    img.save(banner_path, "PNG")
    print(f"[✔] Generated {banner_path}")


if __name__ == "__main__":
    generate_app_icon()
    generate_enhanced_background()
    generate_brand_banner()
