# Auth Pages Redesign

**Date:** 2026-05-16
**Status:** Approved

## Overview

Replace the current two-column login page (form + brand panel) and the unstyled signup page with a unified, minimalist single-column design. Both pages share the same visual language, respect the system theme (light/dark), and display the app logo above the login card.

## Goals

- Simpler, cleaner auth experience — no decorative brand panel
- Consistent design between login and signup
- Full light/dark mode support via shadcn CSS variables
- All UI text in English

## Design

### Layout

Both pages are centered on screen using the existing `(auth)/layout.tsx`. The layout's `max-w-3xl` is narrowed to `max-w-sm` to suit a single-column card.

```
┌─────────────────────────────┐
│                             │
│   [logo] Agent Studio       │  ← centered logo header
│                             │
│  ┌───────────────────────┐  │
│  │  Welcome back         │  │  ← card
│  │  Sign in to your…     │  │
│  │                       │  │
│  │  Email ____________   │  │
│  │  Password __________  │  │
│  │                       │  │
│  │  [    Sign in      ]  │  │
│  │                       │  │
│  │  No account? Sign up  │  │
│  └───────────────────────┘  │
│                             │
└─────────────────────────────┘
```

### Logo Header

- `agent_studio.png` at 32×32px with `rounded-md overflow-hidden unoptimized`
- "Agent Studio" in `font-semibold` next to the image
- Centered above the card; shared between both pages (extracted as inline JSX, not a separate component)

### Theme

All colors use shadcn CSS variables so they adapt automatically:

| Token | Role |
|---|---|
| `bg-background` | page background |
| `bg-card` / `border-border` | card surface and outline |
| `text-foreground` | primary text |
| `text-muted-foreground` | secondary / hint text |
| `bg-primary` / `text-primary-foreground` | submit button |

The green accent (`#2a9d8f`) is the current `--primary` value and stays consistent across both modes.

### Login page

File: `components/login-form.tsx`

- Full rewrite; keep the existing `login()` API call, react-hook-form + zod schema
- Fields: Email, Password
- Submit button: "Sign in" / "Signing in…" while loading
- Footer: "Don't have an account? Sign up" → `/signup`

### Signup page

File: `app/(auth)/signup/page.tsx`

- Full rewrite; keep `apiRegister()`, react-hook-form + zod schema
- Fields: Name, Email, Password (min 8 chars)
- Submit button: "Create account" / "Creating…" while loading
- Footer: "Already have an account? Sign in" → `/login`

### Auth layout

File: `app/(auth)/layout.tsx`

- Change `max-w-3xl` → `max-w-sm`
- Add `gap-6 flex flex-col items-center` so the logo header and card stack naturally

## Files Changed

| File | Action |
|---|---|
| `app/(auth)/layout.tsx` | Update max-width and flex direction |
| `components/login-form.tsx` | Full rewrite |
| `app/(auth)/signup/page.tsx` | Full rewrite |

## Out of Scope

- Password reset / forgot password flow
- OAuth / social login
- Any changes outside the `(auth)` route group
