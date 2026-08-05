"""Reproducible generator for the theme-factory `theme-showcase.pdf`.

Run it whenever the theme list in ``theme_factory.py`` changes:

    uv run python vibe/core/skills/builtins/assets/build_theme_showcase.py

It writes ``theme-showcase.pdf`` next to this file. The theme data below is the
single source for the *visual* showcase; ``tests/core/test_theme_showcase.py``
asserts it stays consistent with the theme definitions embedded in the skill
prompt, so the two cannot silently drift apart.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# (name, description, [(color-name, hex), ...], headers, body, best-for)
THEMES: list[tuple[str, str, list[tuple[str, str]], str, str, str]] = [
    (
        "Ocean Depths",
        "Professional and calming maritime theme",
        [
            ("Deep Navy", "#1a2332"),
            ("Teal", "#2d8b8b"),
            ("Seafoam", "#a8dadc"),
            ("Cream", "#f1faee"),
        ],
        "DejaVu Sans Bold",
        "DejaVu Sans",
        "Corporate decks, financial reports, consulting, trust-building",
    ),
    (
        "Sunset Boulevard",
        "Warm, vibrant golden-hour energy",
        [
            ("Burnt Orange", "#e76f51"),
            ("Coral", "#f4a261"),
            ("Warm Sand", "#e9c46a"),
            ("Deep Purple", "#264653"),
        ],
        "DejaVu Serif Bold",
        "DejaVu Sans",
        "Creative pitches, marketing, lifestyle brands, events",
    ),
    (
        "Forest Canopy",
        "Natural, grounded earth tones",
        [
            ("Forest Green", "#2d4a2b"),
            ("Sage", "#7d8471"),
            ("Olive", "#a4ac86"),
            ("Ivory", "#faf9f6"),
        ],
        "FreeSerif Bold",
        "FreeSans",
        "Sustainability reports, outdoor brands, wellness, organic",
    ),
    (
        "Modern Minimalist",
        "Clean, contemporary grayscale",
        [
            ("Charcoal", "#36454f"),
            ("Slate Gray", "#708090"),
            ("Light Gray", "#d3d3d3"),
            ("White", "#ffffff"),
        ],
        "DejaVu Sans Bold",
        "DejaVu Sans",
        "Tech decks, architecture, business proposals, data viz",
    ),
    (
        "Golden Hour",
        "Rich, warm autumnal palette",
        [
            ("Mustard Yellow", "#f4a900"),
            ("Terracotta", "#c1666b"),
            ("Warm Beige", "#d4b896"),
            ("Chocolate", "#4a403a"),
        ],
        "FreeSans Bold",
        "FreeSans",
        "Restaurants, hospitality, fall campaigns, artisan products",
    ),
    (
        "Arctic Frost",
        "Cool, crisp, winter-inspired clarity",
        [
            ("Ice Blue", "#d4e4f7"),
            ("Steel Blue", "#4a6fa5"),
            ("Silver", "#c0c0c0"),
            ("Crisp White", "#fafafa"),
        ],
        "DejaVu Sans Bold",
        "DejaVu Sans",
        "Healthcare, technology solutions, clean tech, pharma",
    ),
    (
        "Desert Rose",
        "Soft, sophisticated dusty tones",
        [
            ("Dusty Rose", "#d4a5a5"),
            ("Clay", "#b87d6d"),
            ("Sand", "#e8d5c4"),
            ("Deep Burgundy", "#5d2e46"),
        ],
        "FreeSans Bold",
        "FreeSans",
        "Fashion, beauty brands, wedding planning, interior design",
    ),
    (
        "Tech Innovation",
        "Bold, high-contrast, modern tech",
        [
            ("Electric Blue", "#0066ff"),
            ("Neon Cyan", "#00ffff"),
            ("Dark Gray", "#1e1e1e"),
            ("White", "#ffffff"),
        ],
        "DejaVu Sans Bold",
        "DejaVu Sans",
        "Tech startups, software launches, AI/ML, digital transformation",
    ),
    (
        "Botanical Garden",
        "Fresh, organic, garden-inspired",
        [
            ("Fern Green", "#4a7c59"),
            ("Marigold", "#f9a620"),
            ("Terracotta", "#b7472a"),
            ("Cream", "#f5f3ed"),
        ],
        "DejaVu Serif Bold",
        "DejaVu Sans",
        "Garden centers, food, farm-to-table, botanical brands",
    ),
    (
        "Midnight Galaxy",
        "Dramatic, cosmic deep tones",
        [
            ("Deep Purple", "#2b1e3e"),
            ("Cosmic Blue", "#4a4e8f"),
            ("Lavender", "#a490c2"),
            ("Silver", "#e6e6fa"),
        ],
        "DejaVu Sans Bold",
        "DejaVu Sans",
        "Entertainment, gaming, nightlife, luxury, creative agencies",
    ),
]

OUTPUT_PATH = Path(__file__).with_name("theme-showcase.pdf")

# Perceived-luminance threshold: brighter swatches get black label text.
_LUMINANCE_THRESHOLD = 140


def _text_color_for(hex_code: str) -> colors.Color:
    r, g, b = (int(hex_code[i : i + 2], 16) for i in (1, 3, 5))
    luminance = 0.299 * r + 0.587 * g + 0.114 * b
    return colors.black if luminance > _LUMINANCE_THRESHOLD else colors.white


def build(output_path: Path = OUTPUT_PATH) -> Path:
    sheet = getSampleStyleSheet()
    title = ParagraphStyle("title", parent=sheet["Title"], fontSize=26, spaceAfter=6)
    subtitle = ParagraphStyle(
        "subtitle",
        parent=sheet["Normal"],
        fontSize=11,
        textColor=colors.grey,
        alignment=TA_CENTER,
    )
    name_style = ParagraphStyle(
        "name", parent=sheet["Heading2"], fontSize=15, spaceBefore=6, spaceAfter=1
    )
    desc_style = ParagraphStyle(
        "desc",
        parent=sheet["Italic"],
        fontSize=9.5,
        textColor=colors.HexColor("#555555"),
        spaceAfter=5,
    )
    meta_style = ParagraphStyle(
        "meta",
        parent=sheet["Normal"],
        fontSize=8.5,
        textColor=colors.HexColor("#333333"),
        spaceBefore=4,
    )

    def block(theme: tuple) -> KeepTogether:
        name, desc, palette, headers, body, best = theme
        swatches = [
            Paragraph(
                f"<b>{color_name}</b><br/>{hex_code}",
                ParagraphStyle(
                    f"sw-{hex_code}",
                    parent=sheet["Normal"],
                    fontSize=8,
                    alignment=TA_CENTER,
                    leading=11,
                    textColor=_text_color_for(hex_code),
                ),
            )
            for color_name, hex_code in palette
        ]
        table = Table([swatches], colWidths=[4.1 * cm] * 4, rowHeights=[1.7 * cm])
        style = [
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.white),
        ]
        for i, (_, hex_code) in enumerate(palette):
            style.append(("BACKGROUND", (i, 0), (i, 0), colors.HexColor(hex_code)))
        table.setStyle(TableStyle(style))
        return KeepTogether([
            Paragraph(name, name_style),
            Paragraph(desc, desc_style),
            table,
            Paragraph(
                f"<b>Headers:</b> {headers} &nbsp;·&nbsp; <b>Body:</b> {body}",
                meta_style,
            ),
            Paragraph(f"<b>Best for:</b> {best}", meta_style),
            Spacer(1, 14),
        ])

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        topMargin=1.8 * cm,
        bottomMargin=1.6 * cm,
        leftMargin=1.6 * cm,
        rightMargin=1.6 * cm,
        title="Theme Showcase",
    )
    story = [
        Paragraph("Theme Showcase", title),
        Paragraph(
            "10 kuratierte Farb- &amp; Schrift-Themes · Workplace CLI · theme-factory",
            subtitle,
        ),
        Spacer(1, 16),
    ]
    story.extend(block(theme) for theme in THEMES)
    doc.build(story)
    return output_path


if __name__ == "__main__":
    path = build()
    print(f"Wrote {path} ({path.stat().st_size} bytes, {len(THEMES)} themes)")
