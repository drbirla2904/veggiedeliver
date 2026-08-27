# Paytmcart Style Guide (mini)

## Colors (CSS variables in `static/css/app.css`)
- --soil: #2E3B24 (primary dark)
- --leaf: #4B6B3A (accent/green)
- --harvest: #E3A428 (accent/yellow)
- --clay: #C9552F (accent/orange)
- --cream: #F7F3E9 (page background)
- --paper: #FFFFFF (card background)
- --ink: #24291F (body text)
- --muted: #8A9080 (muted/secondary text)

## Components
- `.device` — center container with rounded corners and shadow
- `.auth-card` — elevated card for auth and key flows (login, profile, checkout)
- `.card` — generic card with subtle shadow and hover lift
- `.btn` — primary button; `.btn.clay` for CTA, `.btn.secondary` for muted actions, `.btn.small` for compact buttons
- `input`, `select`, `textarea` — rounded inputs with focus glow (use `.auth-form` for larger inputs)
- `.toast` — transient notifications

## Layout
- Use `.wrap` for page inner padding.
- Use `.grid` / `.row` utilities for layout; `.align-center` to center vertically.

## Tokens & spacing
- Border radius: 8–18px depending on component (.card 14px, .auth-card 18px)
- Shadows: subtle (0 6px 18px) and elevated (0 18px 40px) for prominent surfaces

## How to use
- For auth-like pages (login/checkout/profile), wrap content in `<div class="auth-card">` to get consistent spacing and visual focus.
- Prefer `.btn.full` for actions that span the full width on mobile.

