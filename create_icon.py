#!/usr/bin/env python3
"""
Creates a rounded app icon for Voice Translator.
Uses pillow if available, otherwise creates a placeholder.
"""

import subprocess
import struct
from pathlib import Path


def _render_icon(size: int):
    """Renders one icon image at the requested square size."""
    from PIL import Image, ImageDraw, ImageFilter

    scale = 4
    canvas = size * scale
    img = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    margin = int(canvas * 0.06)
    radius = int(canvas * 0.30)  # более скруглённые, "squircle"-углы
    box = [margin, margin, canvas - margin, canvas - margin]

    # Мягкая тень под иконкой.
    shadow = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        [box[0], box[1] + int(canvas * 0.035), box[2], box[3] + int(canvas * 0.035)],
        radius=radius,
        fill=(0, 0, 0, 120),
    )
    img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(max(2, canvas // 48))))

    # Один плоский тёмный фон — без доп. рамок и колец.
    draw.rounded_rectangle(box, radius=radius, fill=(24, 26, 32, 255))

    # Чистый красный круг по центру.
    center = canvas // 2
    r = int(canvas * 0.30)
    draw.ellipse([center - r, center - r, center + r, center + r], fill=(229, 50, 58, 255))

    # Мягкий глянцевый хайлайт в левом верхнем углу круга.
    highlight = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    hl_r = int(r * 0.8)
    hl_cx, hl_cy = center - int(r * 0.32), center - int(r * 0.38)
    ImageDraw.Draw(highlight).ellipse(
        [hl_cx - hl_r, hl_cy - hl_r, hl_cx + hl_r, hl_cy + hl_r],
        fill=(255, 255, 255, 140),
    )
    highlight = highlight.filter(ImageFilter.GaussianBlur(max(2, canvas // 16)))

    circle_mask = Image.new("L", (canvas, canvas), 0)
    ImageDraw.Draw(circle_mask).ellipse([center - r, center - r, center + r, center + r], fill=255)
    masked_highlight = Image.composite(highlight, Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0)), circle_mask)
    img.alpha_composite(masked_highlight)

    return img.resize((size, size), Image.Resampling.LANCZOS)


def _write_icns(iconset_path: Path, icns_path: Path) -> None:
    """Writes an ICNS file by packaging PNG chunks directly."""
    entries = [
        ("icp4", "icon_16x16.png"),
        ("ic11", "icon_16x16@2x.png"),
        ("icp5", "icon_32x32.png"),
        ("ic12", "icon_32x32@2x.png"),
        ("ic07", "icon_128x128.png"),
        ("ic13", "icon_128x128@2x.png"),
        ("ic08", "icon_256x256.png"),
        ("ic14", "icon_256x256@2x.png"),
        ("ic09", "icon_512x512.png"),
        ("ic10", "icon_512x512@2x.png"),
    ]

    chunks = []
    for icon_type, filename in entries:
        data = (iconset_path / filename).read_bytes()
        chunks.append(icon_type.encode("ascii") + struct.pack(">I", len(data) + 8) + data)

    payload = b"".join(chunks)
    icns_path.write_bytes(b"icns" + struct.pack(">I", len(payload) + 8) + payload)


def create_icon():
    """Creates an app icon."""
    resources_dir = Path(__file__).parent / "Voice Translator.app" / "Contents" / "Resources"
    resources_dir.mkdir(parents=True, exist_ok=True)

    try:
        from PIL import Image, ImageDraw, ImageFont

        iconset_path = resources_dir / "AppIcon.iconset"
        iconset_path.mkdir(exist_ok=True)

        icon_sizes = [
            (16, 1), (16, 2),
            (32, 1), (32, 2),
            (128, 1), (128, 2),
            (256, 1), (256, 2),
            (512, 1), (512, 2),
        ]

        for logical_size, scale in icon_sizes:
            pixel_size = logical_size * scale
            suffix = "@2x" if scale == 2 else ""
            _render_icon(pixel_size).save(
                iconset_path / f"icon_{logical_size}x{logical_size}{suffix}.png",
                "PNG",
            )

        # Convert iconset to icns using iconutil
        icns_path = resources_dir / "AppIcon.icns"
        result = subprocess.run(
            ["iconutil", "-c", "icns", str(iconset_path), "-o", str(icns_path)],
            capture_output=True, text=True
        )

        if result.returncode == 0:
            print(f"Icon created successfully: {icns_path}")
            # Clean up iconset
            import shutil
            shutil.rmtree(iconset_path)
        else:
            print(f"iconutil failed: {result.stderr}")
            _write_icns(iconset_path, icns_path)
            print(f"Icon created with Python fallback: {icns_path}")
            import shutil
            shutil.rmtree(iconset_path)

    except ImportError:
        print("Pillow not installed. Creating placeholder icon instructions.")
        print(f"Please add an icon file to: {resources_dir / 'AppIcon.icns'}")

if __name__ == "__main__":
    create_icon()
