# Tarteel House Brand Rules

## Core direction
Tarteel House should feel minimal, premium, warm, elegant, and parent-friendly. The experience should be calm and trustworthy, not loud, gimmicky, or sales-heavy.

## Non-negotiable design rules
- Do not change fonts casually.
- Do not change typography, spacing, colors, layout language, or visual hierarchy unless explicitly requested.
- Do not introduce a new design system.
- Do not redesign sections just because a different approach might be possible.
- Preserve the current premium editorial look and feel.
- Prefer minimal edits that fix concrete problems.

## Logo
Logo files live in `assets/logo/`. The mark uses an italic serif "Tarteel" with uppercase spaced "HOUSE" in sans. Keep the logo presentation simple and consistent.

## Brand verse
The homepage is built around Surah Al-Muzzammil 73:4:

> "And recite the Qur'an with tarteel (in a distinct and measured tone)."

Arabic Qur'anic text must be handled respectfully and checked carefully.

## Color tokens
Use the existing CSS variables in `assets/css/styles.css`.

- `--ink`: primary text
- `--ink-2`: secondary dark text
- `--ivory`: primary light canvas
- `--ivory-2`: secondary ivory
- `--paper`: warm alternating section background
- `--forest`: primary action green
- `--forest-2`: action hover green
- `--forest-soft`: soft green tags/backgrounds
- `--bronze`: accents and section detail
- `--bronze-2`: stronger accent
- `--bronze-soft`: soft accent background
- `--rule`: borders/dividers
- `--muted`, `--subtle`: supporting text

## Fonts
- Playfair Display: logo feel, editorial headings, premium stat values.
- Inter: body text, UI labels, navigation, buttons, form controls.
- Amiri: Arabic Qur'anic text.
- Fraunces: rare alternate serif for special editorial details.

## Tone of voice
- Warm, reassuring, clear, and respectful.
- Parent-friendly and practical.
- Premium but simple.
- Avoid hype, pressure, vague claims, and generic AI copy.
- Use "Qur'an" consistently.
- Use "Tarteel" consistently.

## Motion rules
- Motion should be subtle: fade/slide-up reveals, restrained hover states, gentle page transitions.
- Avoid flashy counters, aggressive hover effects, or startup-style animation.
- All motion must respect `prefers-reduced-motion`.

## UI rules
- Keep forms simple and parent-friendly.
- Keep CTAs clear and consistent.
- Reuse existing components and classes where possible.
- Do not add decorative visual noise.
- Avoid large refactors unless required for a real bug.
