"""Anthropic theme-factory skill, ported as a Workplace-CLI built-in.

Source: https://github.com/anthropics/skills/tree/main/skills/theme-factory
License: Apache-2.0 (Anthropic, see NOTICE for attribution).
"""

from __future__ import annotations

from vibe.core.skills.models import SkillInfo

_DESCRIPTION = (
    "Toolkit for styling artifacts with a theme. These artifacts can be "
    "slides, docs, reportings, HTML landing pages, etc. There are 10 pre-set "
    "themes with colors/fonts that you can apply to any artifact that has "
    "been creating, or can generate a new theme on-the-fly."
)

_PROMPT = """\
# Theme Factory Skill

This skill provides a curated collection of professional font and color themes themes, each with carefully selected color palettes and font pairings. Once a theme is chosen, it can be applied to any artifact.

## Purpose

To apply consistent, professional styling to presentation slide decks, use this skill. Each theme includes:
- A cohesive color palette with hex codes
- Complementary font pairings for headers and body text
- A distinct visual identity suitable for different contexts and audiences

## Usage Instructions

To apply styling to a slide deck or other artifact:

1. **Show the theme showcase**: Display the `theme-showcase.pdf` file to allow users to see all available themes visually. Do not make any modifications to it; simply show the file for viewing.
2. **Ask for their choice**: Ask which theme to apply to the deck
3. **Wait for selection**: Get explicit confirmation about the chosen theme
4. **Apply the theme**: Once a theme has been chosen, apply the selected theme's colors and fonts to the deck/artifact

## Themes Available

The following 10 themes are available, each showcased in `theme-showcase.pdf`:

1. **Ocean Depths** - Professional and calming maritime theme
2. **Sunset Boulevard** - Warm and vibrant sunset colors
3. **Forest Canopy** - Natural and grounded earth tones
4. **Modern Minimalist** - Clean and contemporary grayscale
5. **Golden Hour** - Rich and warm autumnal palette
6. **Arctic Frost** - Cool and crisp winter-inspired theme
7. **Desert Rose** - Soft and sophisticated dusty tones
8. **Tech Innovation** - Bold and modern tech aesthetic
9. **Botanical Garden** - Fresh and organic garden colors
10. **Midnight Galaxy** - Dramatic and cosmic deep tones

## Theme Details

Each theme is defined in the `themes/` directory with complete specifications including:
- Cohesive color palette with hex codes
- Complementary font pairings for headers and body text
- Distinct visual identity suitable for different contexts and audiences

## Application Process

After a preferred theme is selected:
1. Read the corresponding theme file from the `themes/` directory
2. Apply the specified colors and fonts consistently throughout the deck
3. Ensure proper contrast and readability
4. Maintain the theme's visual identity across all slides

## Create your Own Theme
To handle cases where none of the existing themes work for an artifact, create a custom theme. Based on provided inputs, generate a new theme similar to the ones above. Give the theme a similar name describing what the font/color combinations represent. Use any basic description provided to choose appropriate colors/fonts. After generating the theme, show it for review and verification. Following that, apply the theme as described above.

## Theme Definitions (embedded)

### `arctic-frost.md`

# Arctic Frost

A cool and crisp winter-inspired theme that conveys clarity, precision, and professionalism.

## Color Palette

- **Ice Blue**: `#d4e4f7` - Light backgrounds and highlights
- **Steel Blue**: `#4a6fa5` - Primary accent color
- **Silver**: `#c0c0c0` - Metallic accent elements
- **Crisp White**: `#fafafa` - Clean backgrounds and text

## Typography

- **Headers**: DejaVu Sans Bold
- **Body Text**: DejaVu Sans

## Best Used For

Healthcare presentations, technology solutions, winter sports, clean tech, pharmaceutical content.

### `botanical-garden.md`

# Botanical Garden

A fresh and organic theme featuring vibrant garden-inspired colors for lively presentations.

## Color Palette

- **Fern Green**: `#4a7c59` - Rich natural green
- **Marigold**: `#f9a620` - Bright floral accent
- **Terracotta**: `#b7472a` - Earthy warm tone
- **Cream**: `#f5f3ed` - Soft neutral backgrounds

## Typography

- **Headers**: DejaVu Serif Bold
- **Body Text**: DejaVu Sans

## Best Used For

Garden centers, food presentations, farm-to-table content, botanical brands, natural products.

### `desert-rose.md`

# Desert Rose

A soft and sophisticated theme with dusty, muted tones perfect for elegant presentations.

## Color Palette

- **Dusty Rose**: `#d4a5a5` - Soft primary color
- **Clay**: `#b87d6d` - Earthy accent
- **Sand**: `#e8d5c4` - Warm neutral backgrounds
- **Deep Burgundy**: `#5d2e46` - Rich dark contrast

## Typography

- **Headers**: FreeSans Bold
- **Body Text**: FreeSans

## Best Used For

Fashion presentations, beauty brands, wedding planning, interior design, boutique businesses.

### `forest-canopy.md`

# Forest Canopy

A natural and grounded theme featuring earth tones inspired by dense forest environments.

## Color Palette

- **Forest Green**: `#2d4a2b` - Primary dark green
- **Sage**: `#7d8471` - Muted green accent
- **Olive**: `#a4ac86` - Light accent color
- **Ivory**: `#faf9f6` - Backgrounds and text

## Typography

- **Headers**: FreeSerif Bold
- **Body Text**: FreeSans

## Best Used For

Environmental presentations, sustainability reports, outdoor brands, wellness content, organic products.

### `golden-hour.md`

# Golden Hour

A rich and warm autumnal palette that creates an inviting and sophisticated atmosphere.

## Color Palette

- **Mustard Yellow**: `#f4a900` - Bold primary accent
- **Terracotta**: `#c1666b` - Warm secondary color
- **Warm Beige**: `#d4b896` - Neutral backgrounds
- **Chocolate Brown**: `#4a403a` - Dark text and anchors

## Typography

- **Headers**: FreeSans Bold
- **Body Text**: FreeSans

## Best Used For

Restaurant presentations, hospitality brands, fall campaigns, cozy lifestyle content, artisan products.

### `midnight-galaxy.md`

# Midnight Galaxy

A dramatic and cosmic theme with deep purples and mystical tones for impactful presentations.

## Color Palette

- **Deep Purple**: `#2b1e3e` - Rich dark base
- **Cosmic Blue**: `#4a4e8f` - Mystical mid-tone
- **Lavender**: `#a490c2` - Soft accent color
- **Silver**: `#e6e6fa` - Light highlights and text

## Typography

- **Headers**: FreeSans Bold
- **Body Text**: FreeSans

## Best Used For

Entertainment industry, gaming presentations, nightlife venues, luxury brands, creative agencies.

### `modern-minimalist.md`

# Modern Minimalist

A clean and contemporary theme with a sophisticated grayscale palette for maximum versatility.

## Color Palette

- **Charcoal**: `#36454f` - Primary dark color
- **Slate Gray**: `#708090` - Medium gray for accents
- **Light Gray**: `#d3d3d3` - Backgrounds and dividers
- **White**: `#ffffff` - Text and clean backgrounds

## Typography

- **Headers**: DejaVu Sans Bold
- **Body Text**: DejaVu Sans

## Best Used For

Tech presentations, architecture portfolios, design showcases, modern business proposals, data visualization.

### `ocean-depths.md`

# Ocean Depths

A professional and calming maritime theme that evokes the serenity of deep ocean waters.

## Color Palette

- **Deep Navy**: `#1a2332` - Primary background color
- **Teal**: `#2d8b8b` - Accent color for highlights and emphasis
- **Seafoam**: `#a8dadc` - Secondary accent for lighter elements
- **Cream**: `#f1faee` - Text and light backgrounds

## Typography

- **Headers**: DejaVu Sans Bold
- **Body Text**: DejaVu Sans

## Best Used For

Corporate presentations, financial reports, professional consulting decks, trust-building content.

### `sunset-boulevard.md`

# Sunset Boulevard

A warm and vibrant theme inspired by golden hour sunsets, perfect for energetic and creative presentations.

## Color Palette

- **Burnt Orange**: `#e76f51` - Primary accent color
- **Coral**: `#f4a261` - Secondary warm accent
- **Warm Sand**: `#e9c46a` - Highlighting and backgrounds
- **Deep Purple**: `#264653` - Dark contrast and text

## Typography

- **Headers**: DejaVu Serif Bold
- **Body Text**: DejaVu Sans

## Best Used For

Creative pitches, marketing presentations, lifestyle brands, event promotions, inspirational content.

### `tech-innovation.md`

# Tech Innovation

A bold and modern theme with high-contrast colors perfect for cutting-edge technology presentations.

## Color Palette

- **Electric Blue**: `#0066ff` - Vibrant primary accent
- **Neon Cyan**: `#00ffff` - Bright highlight color
- **Dark Gray**: `#1e1e1e` - Deep backgrounds
- **White**: `#ffffff` - Clean text and contrast

## Typography

- **Headers**: DejaVu Sans Bold
- **Body Text**: DejaVu Sans

## Best Used For

Tech startups, software launches, innovation showcases, AI/ML presentations, digital transformation content.


"""

SKILL = SkillInfo(
    name="theme-factory",
    description=_DESCRIPTION,
    user_invocable=True,
    license="Apache-2.0 (Anthropic, https://github.com/anthropics/skills)",
    prompt=_PROMPT,
)
