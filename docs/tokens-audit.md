BeardMeatsFood Site Tokens Audit (Webflow)

Summary
- Site platform: Webflow
- Primary fonts: Roboto (Google), Thunder (custom display)
- CSS variables present under :root for brand/neutral/system colors
- Breakpoints: 991px, 767px, 479px (Webflow defaults)

Discovered Variables (from :root)
- --base-color-brand--black: #1a1a1a
- --base-color-brand--white: #f8f8f8
- --base-color-brand--neon: #e0ff00
- --base-color-neutral--white: #f8f8f8
- --base-color-neutral--black: #1a1a1a
- --base-color-neutral--neutral-lightest: #eee
- --base-color-neutral--neutral-lighter: #ccc
- --base-color-neutral--neutral-light: #aaa
- --base-color-neutral--neutral: #666
- --base-color-neutral--neutral-dark: #444
- --base-color-neutral--neutral-darker: #222
- --base-color-neutral--neutral-darkest: #111
- --base-color-system--success-green: #027a48
- --base-color-system--success-green-light: #ecfdf3
- --base-color-system--error-red: #b42318
- --base-color-system--error-red-light: #fef3f2
- Semantic mappings in use:
  - --background-color--background-primary: var(--base-color-neutral--black)
  - --text-color--text-primary: var(--base-color-neutral--white)
  - --link-color--link-primary: var(--base-color-neutral--white)
  - --text-color--text-alternate: var(--base-color-neutral--black)
  - --border-color--border-primary: var(--base-color-neutral--white)
  - ...and variants for secondary/tertiary/success/error

Typography
- Body: Roboto, sans-serif (loaded via WebFont loader)
- Display/Headings: Thunder (custom), fallback Impact, sans-serif
- Example sizes in CSS (selected): 1rem, 1.25rem, 1.5rem, 1.88rem, 3.5rem, 5rem, 7.5rem, 11.13rem, 16.5rem
- Line-height patterns: 1, 1.4–1.6, and 90% for display sizes

Spacing & Radius (observed)
- Spacing scale (rem): 0.25, 0.5, 0.75, 1, 1.5, 2, 2.5, 3, 4, 5, 6, 7, 10
- Gaps commonly at: .25, .5, .75, 1, 1.5, 2, 2.5
- Radii: .25rem, .6875rem (~11px), .75rem (12px), 100vw (pill), 50% (round)
- Shadows (examples):
  - 0 1px 2px rgba(0,0,0,0.05)
  - 0 1px 3px rgba(0,0,0,0.10), 0 1px 2px rgba(0,0,0,0.06)
  - 0 20px 24px -4px rgba(0,0,0,0.08), 0 8px 8px -4px rgba(0,0,0,0.03)
  - 0 24px 48px -12px rgba(0,0,0,0.18)
  - 0 32px 64px -12px rgba(0,0,0,0.14)

Breakpoints
- max-width: 991px, 767px, 479px
- min-width: 768px (used in a few rules)

Proposed Cross-App Tokens (to consume in widgets)
- Colors:
  - --bmf-color-bg: var(--background-color--background-primary)
  - --bmf-color-bg-alt: var(--background-color--background-alternate)
  - --bmf-color-surface: var(--background-color--background-tertiary)
  - --bmf-color-text: var(--text-color--text-primary)
  - --bmf-color-text-alt: var(--text-color--text-alternate)
  - --bmf-color-link: var(--link-color--link-primary)
  - --bmf-color-border: var(--border-color--border-primary)
  - --bmf-color-brand: var(--base-color-brand--neon)
  - --bmf-color-success: var(--base-color-system--success-green)
  - --bmf-color-success-bg: var(--base-color-system--success-green-light)
  - --bmf-color-danger: var(--base-color-system--error-red)
  - --bmf-color-danger-bg: var(--base-color-system--error-red-light)
- Typography:
  - --bmf-font-sans: Roboto, Arial, sans-serif
  - --bmf-font-display: "Thunder", Impact, sans-serif
  - --bmf-font-size-100: .875rem
  - --bmf-font-size-200: 1rem
  - --bmf-font-size-300: 1.25rem
  - --bmf-font-size-400: 1.5rem
  - --bmf-font-size-500: 1.88rem
  - --bmf-font-size-700: 3.5rem
  - --bmf-font-size-900: 5rem
- Spacing:
  - --bmf-space-1: .25rem; --bmf-space-2: .5rem; --bmf-space-3: .75rem; --bmf-space-4: 1rem; --bmf-space-6: 1.5rem; --bmf-space-8: 2rem; --bmf-space-10: 2.5rem; --bmf-space-12: 3rem
- Radius:
  - --bmf-radius-sm: .25rem; --bmf-radius-md: .5rem; --bmf-radius-lg: .75rem; --bmf-radius-pill: 100vw; --bmf-radius-round: 50%
- Shadow:
  - --bmf-shadow-1: 0 1px 2px rgba(0,0,0,0.05)
  - --bmf-shadow-2: 0 1px 3px rgba(0,0,0,0.10), 0 1px 2px rgba(0,0,0,0.06)
  - --bmf-shadow-3: 0 12px 16px -4px rgba(0,0,0,0.08), 0 4px 6px -2px rgba(0,0,0,0.03)
  - --bmf-shadow-4: 0 24px 48px -12px rgba(0,0,0,0.18)

Usage Notes
- The page already defines brand and semantic colors in :root; aliasing via --bmf-* ensures widgets inherit site theme automatically.
- Fonts are loaded by Webflow; widgets should not load their own fonts, but reference the stacks above.
- Consider a light-mode variant if the site ever flips background primary to white; aliases above will follow.

