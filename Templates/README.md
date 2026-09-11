# Handoff: 현호의 주식 브리핑 — Instagram Card News Template

## Overview
A 5-card (1080×1080) Instagram-style "card news" template for a personal daily stock briefing.
Card flow: **01 Cover → 02 US market → 03 KR market (previous session) → 04 Watch list → 05 Outro**.
Two complete themes: dark (default) and light. Content is placeholder copy meant to be swapped daily.

## About the Design Files
The bundled HTML files are **design references** — prototypes showing intended look and layout, not
production code. The task is to recreate them in the target codebase's environment (React/Vue/native/
whatever exists), using its established patterns. If there is no codebase yet, pick a suitable stack and
implement there. A likely real-world target is a **1080×1080 image generator** (data in → PNG out).

Files, in order of usefulness for reading code:

| File | What it is |
| --- | --- |
| `cards-dark.html` | **Plain static HTML** — dark theme, no runtime, opens in any browser. Start here. |
| `cards-light.html` | Plain static HTML — light theme. |
| `dark-theme.dc.html` / `light-theme.dc.html` | Original authoring format (same markup + a small logic class for two boolean options). Needs `support.js` next to it. |
| `support.js` | Runtime for the `.dc.html` files only. Not needed for the plain HTML. |

All styling is **inline `style` attributes**; there is no CSS file to port. Two web fonts are loaded from
CDN (see Design Tokens).

## Fidelity
**High-fidelity.** Final colors, type scale, spacing, and artwork are decided. Recreate pixel-accurately
at 1080×1080 per card. There are no interactions — output is a static image sequence.

## Global card frame
- Card size: exactly `1080 × 1080 px`, `overflow: hidden`, `box-sizing: border-box`.
- Padding: `80px` on every card.
- Cards are laid out in the prototype as a vertical stack (`display:flex; flex-direction:column; gap:56px; padding:72px`) on the page background. That stack is **preview chrome only** — do not ship it.
- Every card carries the same background artwork (see Background artwork).
- Base font: `Pretendard` (Korean text + UI), `JetBrains Mono` (all numbers, labels, ASCII).
- `font-feature-settings: 'tnum'` on the container so figures align.

### Background artwork (identical on all 5 cards)
Encoded as an inline SVG data URI in each card's `background-image` (`background-size: cover; no-repeat`).
Composition, in `0 0 1080 1080` coordinates:
1. Four horizontal grid rules at y = 200, 440, 680, 920 — `stroke-width: 2`.
2. Eight candlesticks (rising trend), body `width: 44`, x = 100, 220, 340, 460, 580, 700, 820, 940; wick centered at x+22. Bodies (x, y, h): (100,800,70) (220,780,60) (340,700,90) (460,640,80) (580,660,55) (700,560,100) (820,470,110) (940,380,120). Wicks (top→bottom): 770–890, 750–860, 670–810, 610–740, 630–730, 530–680, 440–600, 350–520. Candles 2 and 5 are "down" colored, the rest "up".
3. A rising polyline `-20,860 122,835 242,810 362,745 482,680 602,687 722,610 842,525 962,440 1100,395`, `stroke-width: 4`, with an `r=11` dot at 962,440.
4. Four rotated monospace glyphs: `$` 180px at (790,250) rot −13°; `₩` 130px at (90,560) rot 11°; `▲` 70px at (600,1000) rot −7°; `▲` 58px at (420,330) rot 6°.

Artwork opacities — dark theme: grid `.05` white; up candles `#12d6b0` `.18`; down `#e0776c` `.14`;
trend line `#12d6b0` `.30`; glyphs `.11`. Light theme: grid `.05` `#17181a`; up `#0d8f74` `.14`;
down `#b8443b` `.12`; trend line `#1b3bf0` `.16`; `$`/`₩` gold `.20`, `▲` `.16`.

Cards 01 and 05 additionally have: a `1px` hairline inset frame at `inset: 44px`, a `22px` dot grid
(`radial-gradient` 1px dots), and (card 01 only) a row of 7 full-height silhouette bars along the bottom
(`padding: 0 44px 44px`, `gap: 14px`, heights 120/180/150/250/210/330/430px, the last two tinted mint).

## Screens / Views

### 01 — Cover
Purpose: date + brand + table of contents.
Layout: `flex column; justify-content: space-between` over the full card.
- Top row (`space-between`): date `JetBrains Mono 26px, letter-spacing .18em`, gold — `2026.08.27 THU`. Right: two 12px dots (`#1b3bf0`, `#12d6b0`) + `VOL.128` mono 24px `.16em` in muted grey.
- Middle block (`gap: 36px`): eyebrow `MARKET NOTE` mono 24px `.3em` muted; title `150px / weight 800 / line-height .98 / letter-spacing -.055em` — "현호의 / 주식 브리핑" (two lines via `<br>`); then a row with an `88×1px` gold rule + subtitle `34px` muted ("3분 만에 읽는 어제와 오늘의 시장").
- Bottom row (`space-between`, align-end): a 3-column grid (`gap: 12px 22px`, `27px`) of `01 미국 시장 US / 02 국내 시장 KR / 03 관심 종목 PICK` — index and suffix in muted mono; right: `SWIPE →` mono 22px `.14em`.

### 02 — US market
- Header row: `10×10px` blue square + `US MARKET` mono 24px `.24em` (dark: `#6d8cff`, light: `#1b3bf0`); right `02 — 05` mono 24px muted. Bottom border 1px, `padding-bottom: 22px`.
- Headline `66px / 800 / line-height 1.12 / letter-spacing -.045em`, two lines.
- Index table: 3 equal columns, 1px top+bottom border, 1px dividers between columns, `padding: 30px 26px`. Each cell: label `26px` muted → value mono `50px / 700` → row with change `mono 29px / 700` (up/down color) + a 5-bar sparkline (`6px` wide bars, `gap: 3px`, `height ≤ 30px`, first three bars in the dim tint, last two in the trend color).
- Three numbered notes, `gap: 22px`: index mono `26px` blue, body `33px / line-height 1.5` with key figures wrapped in `<strong>` accent-colored.

### 03 — KR market (previous session)
- Header: mint square + `KR MARKET · 08.26`; right `03 — 05`.
- Hero row (`align-end`, `space-between`): left — label `28px` muted, KOSPI value **mono 104px / 700 / line-height 1**, change mono `30px / 700` mint. Right — a 6-bar column chart, bars `22px` wide, `gap: 6px`, heights 62/78/70/96/112/150px; last two bars accent, rest dim.
- Divider strip (1px top+bottom, `padding: 26px 0`, `space-between`): KOSDAQ label+value, its change, a `1×56px` vertical rule, USD/KRW label+value, its change (mono 40px values, 30px changes).
- 3-up 수급 grid (`gap: 16px`, 1px border, `padding: 24px`): mono `22px .14em` label (`FOREIGN` / `INSTITUTION` / `RETAIL`) + mono `34px / 700` value, colored by sign.
- Sector chips: eyebrow `SECTOR` mono 22px `.22em` gold; chips `padding: 14px 24px`, `border-radius: 999px`, `27px / 600`, tinted background at ~12% of the sign color.

### 04 — Watch list
- Header: gold square + `WATCH LIST`; right `04 — 05`.
- Title `60px / 800 / line-height 1.14`, two lines.
- Three rows, each `padding: 30px 0` with a 1px top border (last row also bottom border), `align-items: center`, `gap: 28px`:
  rank mono `24px` muted (`width: 34px`) → name `40px / 700` + ticker mono `24px` muted (baseline aligned, `gap: 14px`) + one-line rationale `28px / 1.45` → right-aligned price mono `32px / 700` and change mono `25px / 700` → status pill (`padding: 12px 22px`, `radius: 999px`, `24px / 700`, `white-space: nowrap`): 매수 관점 = filled green, 분할 매수 = filled blue `#1b3bf0` with white text, 관망 = 1px outlined.
- Footer disclaimer `23px / 1.5` muted (toggleable — see Options).

### 05 — Outro
`flex column; space-between` inside the hairline frame.
- Top: three `56×4px` bars — blue, mint, gold, `gap: 10px`.
- Middle: `104px / 800 / line-height 1.06 / letter-spacing -.05em` three-line message + `34px` muted subline.
- Bottom row: handle `@HYUNHO.MARKET` mono `26px .2em` gold; right: five `9px` page dots, `gap: 9px`, last one active (bright), rest dim.

## Interactions & Behavior
None — static cards. Behavior to reproduce is generation, not interaction:
- Text and figures come from data (date, index values, changes, 수급 amounts, sector list, 3 watch-list rows).
- Sign drives color and arrow/prefix: `+`/mint-green for up, `−` (U+2212, not a hyphen) / rose-red for down, neutral grey for 0.00%.
- Sparkline/bar heights are data-driven in principle; in the prototype they are hardcoded.

## State Management
No UI state. If built as a generator, the input shape is roughly:
`{ date, volume, us: [{name, value, change, spark[]}], usNotes: [{title?, body}], kr: {kospi, kosdaq, fx, flows:{foreign,institution,retail}, sectors:[{name,change}]}, picks: [{name, ticker, note, price, change, status}], theme: 'dark'|'light' }`

## Design Tokens

### Dark theme
| Role | Hex |
| --- | --- |
| Card background | `#1a1b1d` |
| Page background (preview only) | `#0f1011` |
| Primary text | `#f6f4ef` |
| Secondary text | `#c8cbd0` |
| Muted text | `#8a8d92` |
| Faint text / meta | `#6f7276` |
| Hairline / border | `#33353a` |
| Dim bar / chart fill | `#2c2e32` |
| Up (positive) | `#12d6b0` |
| Down (negative) | `#e0776c` |
| Brand blue (label) | `#6d8cff` |
| Brand blue (fills) | `#1b3bf0` |
| Gold accent | `#c9a227` |
| Text on mint fill | `#10312a` |
| Pill outline | `#4a4d52` |
| Page dot (inactive) | `#3a3d42` |

### Light theme
| Role | Hex |
| --- | --- |
| Card background | `#f6f4ef` |
| Page background (preview only) | `#e8e4dc` |
| Primary text | `#17181a` |
| Secondary text | `#4b4740` |
| Muted text | `#7c766c` |
| Faint text / meta | `#78716a` (min. for AA at ≤27px) |
| Hairline / border | `#ddd8ce` |
| Dim bar / chart fill | `#ded8cd` |
| Up (positive) | `#0d8f74` |
| Down (negative) | `#b8443b` |
| Brand blue | `#1b3bf0` |
| Gold accent | `#9d7a17` (text) / `#c9a227` (artwork) |
| Pill outline | `#b4aea4` |
| Page dot (inactive) | `#cfc8bc` |

Contrast note: in the light theme nothing smaller than 30px may go lighter than `#78716a`.

### Typography
- Korean/UI: **Pretendard** — `https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css`
- Numbers/labels: **JetBrains Mono** 400/500/700 — Google Fonts
- Scale used: 150 / 104 / 66 / 60 / 50 / 44 / 40 / 36 / 34 / 33 / 32 / 30 / 29 / 28 / 27 / 26 / 25 / 24 / 23 / 22 px
- Weights: 800 (display), 700 (values/labels), 600 (chips), 400 (body)
- Tracking: display `-0.045em ~ -0.055em`; mono eyebrows `+0.14em ~ +0.3em`
- Minimum size anywhere: 22px (at 1080px card width)

### Spacing / radius
- Card padding `80px`; section gaps `32–44px`; row gaps `20–28px`
- Hairlines `1px`; emphasis rules `2px` (grid) and `4px` (trend line, outro bars)
- Radius: `999px` (pills, dots) — everything else is square. No shadows anywhere.

## Options (from the prototype's two booleans)
- `showNumbering` (default true) — the `0X — 05` counter in card headers.
- `showDisclaimer` (default true) — the footer line on card 04.
Both are rendered as always-on in the exported plain HTML.

## Assets
No bitmap images. All graphics are inline SVG/CSS generated from the values above. Two CDN webfonts.
The palette derives from the user's own reference logos (cobalt blue + mint, charcoal + gold); if the
target codebase already has a brand system, map these roles onto it instead of copying hexes.

## Files
- `cards-dark.html`, `cards-light.html` — static references (read these)
- `dark-theme.dc.html`, `light-theme.dc.html`, `support.js` — authoring originals
