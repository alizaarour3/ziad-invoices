---
name: Ziad Invoices UI
colors:
  surface: '#11131b'
  surface-dim: '#11131b'
  surface-bright: '#373942'
  surface-container-lowest: '#0c0e16'
  surface-container-low: '#191b23'
  surface-container: '#1d1f27'
  surface-container-high: '#282a32'
  surface-container-highest: '#32343d'
  on-surface: '#e1e2ed'
  on-surface-variant: '#c3c6d7'
  inverse-surface: '#e1e2ed'
  inverse-on-surface: '#2e3039'
  outline: '#8d90a0'
  outline-variant: '#434655'
  surface-tint: '#b4c5ff'
  primary: '#b4c5ff'
  on-primary: '#002a78'
  primary-container: '#2563eb'
  on-primary-container: '#eeefff'
  inverse-primary: '#0053db'
  secondary: '#b4c5ff'
  on-secondary: '#182d63'
  secondary-container: '#33467e'
  on-secondary-container: '#a4b6f5'
  tertiary: '#ffb596'
  on-tertiary: '#581e00'
  tertiary-container: '#bc4800'
  on-tertiary-container: '#ffede6'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#dbe1ff'
  primary-fixed-dim: '#b4c5ff'
  on-primary-fixed: '#00174b'
  on-primary-fixed-variant: '#003ea8'
  secondary-fixed: '#dbe1ff'
  secondary-fixed-dim: '#b4c5ff'
  on-secondary-fixed: '#00174b'
  on-secondary-fixed-variant: '#31447b'
  tertiary-fixed: '#ffdbcd'
  tertiary-fixed-dim: '#ffb596'
  on-tertiary-fixed: '#360f00'
  on-tertiary-fixed-variant: '#7d2d00'
  background: '#11131b'
  on-background: '#e1e2ed'
  surface-variant: '#32343d'
typography:
  display:
    fontFamily: Geist
    fontSize: 48px
    fontWeight: '700'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Geist
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Geist
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.3'
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Geist
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Geist
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.5'
  label-sm:
    fontFamily: Geist
    fontSize: 12px
    fontWeight: '500'
    lineHeight: '1.2'
    letterSpacing: 0.02em
  code:
    fontFamily: Geist
    fontSize: 13px
    fontWeight: '400'
    lineHeight: '1.4'
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 40px
  container-max: 1280px
  gutter: 20px
---

## Brand & Style

The design system is engineered for a high-performance financial environment, prioritizing utility, clarity, and a sense of institutional stability. It targets professionals who demand efficiency and precision, moving away from generic administrative patterns toward a "Technical-Premium" aesthetic.

The visual narrative is inspired by high-end developer tools and modern fintech platforms. It utilizes a **Technical Minimalist** style: high-density information layouts characterized by rigorous alignment, monospaced-influenced details (where appropriate for data), and a dark-mode first orientation that reduces eye strain during prolonged sessions. The aesthetic is sharp, intentional, and evokes the feeling of a sophisticated terminal or a precision instrument.

## Colors

This design system employs a high-contrast dark palette to create a focused work environment. The primary color, **Professional Blue (#2563EB)**, is used sparingly as a functional signal for primary actions and active states, ensuring it retains its impact without overwhelming the user.

- **Foundations:** The background uses a deep slate-black to provide maximum contrast for white and light-gray text.
- **Surfaces:** Cards and containers utilize a slightly lighter navy-slate to create subtle layering without the need for heavy drop shadows.
- **Borders:** A consistent, low-opacity border is used to define structural boundaries, maintaining a "Technical" look that favors lines over shadows.
- **Bi-directional Intent:** Colors are neutral enough to support both English and Arabic scripts without clashing with the inherent weight of the different letterforms.

## Typography

The typography leverages **Geist** for its exceptional clarity in both data-heavy tables and high-level headers. The typeface's geometric construction mirrors the "technical" soul of the design system.

- **Data Precision:** For invoice numbers, currency values, and dates, use the `body-md` or `code` weight to ensure legibility across dense grids.
- **RTL Considerations:** When rendering Arabic (Noto Sans Arabic), maintain the same visual hierarchy. Note that Arabic script often requires a 10-15% increase in line-height compared to English to prevent diacritics from overlapping.
- **Hierarchy:** Use all-caps for labels (`label-sm`) to create a clear distinction between metadata and primary content.

## Layout & Spacing

The system follows a strict **4px baseline grid** to achieve a compact, professional feel typical of high-end productivity tools.

- **Grid:** A 12-column fluid grid is used for main dashboards, while sidebars are kept at a fixed width (e.g., 240px) to maximize the predictability of the data workspace.
- **Bi-directionality:** All horizontal spacing (margins, padding, icons) must be mirrored in RTL mode. "Start" and "End" logical properties should be used in development instead of "Left" and "Right."
- **Density:** Information density is "Comfortable-Compact." Padding inside cards should be `24px` (`lg`) for desktop, scaling down to `16px` (`md`) for mobile viewports.

## Elevation & Depth

In this design system, depth is communicated through **Tonal Layering** and **Technical Outlines** rather than traditional soft shadows.

- **Base Layer:** The darkest shade (#020617) represents the furthest depth.
- **Surface Layer:** Interactive elements and cards sit on the next level (#0F172A), defined by a subtle `1px` border (#1E293B).
- **Active Elevation:** When a component is hovered or focused, it does not "rise" via a shadow; instead, the border color brightens to the primary blue or a lighter slate, and the background color shifts slightly.
- **Overlays:** Modals and dropdowns use a sharp, high-contrast border with a 0% blur, 10px offset black shadow to create a "floating sheet" effect.

## Shapes

The shape language is controlled and systematic. A `roundedness` of **1** (Soft) is the standard, creating a balance between the clinical feel of sharp corners and the overly-consumer feel of heavy rounding.

- **Buttons & Inputs:** Use a 6px - 8px radius. This keeps the technical aesthetic while providing enough softness to feel modern.
- **Cards:** Use a 10px - 14px radius for outer containers.
- **Selection States:** Use sharp inner corners for nested elements (like tabs inside a card) to maintain a structural, architectural appearance.

## Components

### Buttons
Primary buttons use the Professional Blue (#2563EB) with white text. Secondary buttons are "Ghost" style: transparent backgrounds with subtle borders that only fill on hover.

### Inputs
Input fields use a dark-fill (#0F172A) with a `1px` border. The focus state is a clean `1px` solid Professional Blue stroke—avoid glowing outer rings. Label text should be placed above the input using the `label-sm` style.

### Cards
Cards are the primary organizational unit. They should have no shadow by default, relying on the `border_subtle` for definition. Headers within cards should be separated by a horizontal rule (`1px`).

### Tables (Data Grids)
The core of the invoice experience. Use a zebra-stripe pattern where every second row has a 2% lighter background. Row heights should be kept compact (approx 48px) to maximize data visibility.

### RTL Logic
All icons that indicate direction (arrows, chevrons) must be flipped in Arabic mode, unless they represent universal playback controls. Currency symbols in RTL should be placed according to local standards (typically after the amount).