# Baseline — logo resources

Direction **5c, "B on the line"**: the wordmark set in ink with the baseline as a green rule
beneath it and the centre arc rising out of that rule. The standalone mark is the same line
under a single B.

## Files

| File                                                 | Use                                                       |
| ---------------------------------------------------- | --------------------------------------------------------- |
| `baseline-lockup.svg`                                | Primary lockup, ink on paper. Headers, docs, decks.       |
| `baseline-lockup-reversed.svg`                       | Lockup in paper white, for green or photographic grounds. |
| `baseline-mark.svg`                                  | Square mark, transparent ground.                          |
| `baseline-mark-on-paper.svg`                         | Square mark on the app paper tone.                        |
| `baseline-mark-reversed.svg`                         | Square mark, paper on green.                              |
| `favicon.svg`                                        | Browser tab icon (scalable).                              |
| `favicon-16.png`, `favicon-32.png`, `favicon-64.png` | Raster tab icons. 16px drops the arc.                     |
| `apple-touch-icon-180.png`                           | iOS home screen.                                          |

## Colour

| Token        | Hex       | Role                                           |
| ------------ | --------- | ---------------------------------------------- |
| Forest green | `#2D5A27` | The baseline rule and arc. Never the wordmark. |
| Ink          | `#1A1A1A` | The wordmark and the B.                        |
| Paper        | `#FBFAF5` | Ground; also the reversed-art ink.             |

## Type

IBM Plex Sans, 600 for the wordmark, 700 for the standalone B, tracking −0.03em.

## Rules

- The rule always spans the full width of the wordmark — never shorter, never wider.
- The arc sits centred on the rule and never touches the letters above it.
- Minimum lockup width 96px; below that use the square mark.
- Clearspace on all sides equals the cap height of the B.
- Do not recolour the wordmark green, add a container to the lockup, or set the rule at an angle.

## Fonts in SVG

The SVGs reference IBM Plex Sans by name and fall back to Helvetica/Arial where it is not
installed. For print or third-party tools, open the SVG and convert the text to outlines first.

The primary lockup uses a tight `0 12 198 47` viewBox. In the header, size it by height (30px) with automatic width so the wordmark cap height stays aligned with the navigation text.

## Favicon markup

```html
<link rel="icon" href="/logo/favicon.svg" type="image/svg+xml" />
<link rel="icon" href="/logo/favicon-32.png" sizes="32x32" />
<link rel="apple-touch-icon" href="/logo/apple-touch-icon-180.png" />
```
