---
source: Google Stitch — project 11424231694215614824
name: AutoHire Web Design System
colors:
  primary: "#2563EB"
  deep-navy: "#0F172A"
  soft-blue-bg: "#EFF6FF"
  accent-cyan: "#06B6D4"
  ai-purple: "#7C3AED"
  success-green: "#16A34A"
  warning-amber: "#F59E0B"
  error-red: "#DC2626"
  neutral-bg: "#F8FAFC"
  surface-white: "#FFFFFF"
  border-gray: "#E2E8F0"
  muted-text: "#64748B"
  primary-text: "#0F172A"
typography:
  display-xl:   { fontFamily: Inter, fontSize: 64px, fontWeight: 700 }
  page-title:   { fontFamily: Inter, fontSize: 32px, fontWeight: 600 }
  section-title:{ fontFamily: Inter, fontSize: 24px, fontWeight: 600 }
  card-title:   { fontFamily: Inter, fontSize: 18px, fontWeight: 600 }
  body:         { fontFamily: Inter, fontSize: 16px, fontWeight: 400 }
  table-text:   { fontFamily: Inter, fontSize: 14px, fontWeight: 400 }
  helper-text:  { fontFamily: Inter, fontSize: 13px, fontWeight: 400 }
spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  xxl: 40px
  section-gap: 32px
rounded:
  sm: 4px
  md: 8px
  lg: 16px
  xl: 24px
---

# AutoHire Design System

**Implementation note:** these tokens are implemented in `frontend/src/styles/tokens.css`.
Use the Tailwind utility names (`bg-primary`, `text-muted`, `rounded-card`) — never raw
hex values and never arbitrary values like `text-[#2563EB]`. If a token is missing, add
it to `tokens.css` first.

## Overview

AutoHire is an AI-powered recruitment automation platform. This design system defines all
UI rules for **web desktop** screens: dashboards, templates, candidate ranking, scheduling,
emails, and admin panels. All screens must adhere to this system for consistent color,
typography, spacing, and component usage.

The platform should feel **intelligent, reliable, professional, and human-centered**. AI
features are highlighted with subtle purple/blue accents. Interactive states and CTAs are
primarily blue, while warnings, errors, and success states follow the palette rules.

## Colors

- **Primary Blue (#2563EB)**: Main CTAs, key interactive elements
- **Deep Navy (#0F172A)**: Headers, primary text
- **Soft Blue Background (#EFF6FF)**: Subtle section backgrounds
- **Accent Cyan (#06B6D4)**: Highlights, secondary accents
- **AI Purple (#7C3AED)**: AI analysis, semantic ranking, automation indicators
- **Success Green (#16A34A)**: Completed actions, available slots, connected integrations
- **Warning Amber (#F59E0B)**: TTL warnings, pending states, quota alerts
- **Error Red (#DC2626)**: Errors, failed tasks, destructive actions
- **Neutral Background (#F8FAFC)**: Page background
- **Surface White (#FFFFFF)**: Cards, modals, input backgrounds
- **Border Gray (#E2E8F0)**: Card and input borders
- **Muted Text (#64748B)**: Secondary text
- **Primary Text (#0F172A)**: Body and headings

## Typography

| Role | Font | Size | Weight |
|---|---|---|---|
| Display / Hero | Inter | 64px | 700 |
| Page Title | Inter | 32px | 600 |
| Section Title | Inter | 24px | 600 |
| Card Title | Inter | 18px | 600 |
| Body Text | Inter | 16px | 400 |
| Table Text | Inter | 14px | 400 |
| Helper / Metadata | Inter | 13px | 400 |

## Layout

- Desktop: 1440px frame, 12-column grid
- App shell: sidebar 260px, header 72px
- Main content padding: 24–32px
- Card padding: 20–24px
- Section gap: 32px
- 8px spacing scale: 4, 8, 12, 16, 24, 32, 40, 48, 64

## Components

### Buttons
- **Primary**: Blue fill, white text, 12px vertical × 20px horizontal, 10px radius, semibold
- **Secondary**: White fill, gray border, navy text, 10px vertical × 16px horizontal
- **Ghost**: Transparent, muted text
- **Destructive**: Red background, white text, 10px radius — always behind a confirm modal

### Cards
Rounded 16px, white surface, subtle shadow, 1px gray border, 24px padding.
Types: KPI, Job, AI Analysis.

### Badges
Pill-shaped, 4px × 12px padding, semibold, with text + optional icon.

Statuses: Active, Expired, Draft, Processing, Scheduled, Interview Invited, Confirmed,
Reschedule Requested, Rejected, Failed, Connected, Disconnected, Syncing, Quota Warning.

Match Score: circular progress or horizontal bar with color thresholds —
strong `#16A34A`, good `#06B6D4`, partial `#F59E0B`, weak `#DC2626`.

### Tables
Sticky headers, optional alternating rows, row hover `#EFF6FF`, 12px row padding.
Checkbox selection for bulk actions. Right-aligned actions. Search/filter/sort controls.
Clear empty state message.

### Forms
Label above input (500 weight, 8px below). Helper text below (13px, muted). Inline
validation with error state styling. Input: 1px border, 8px radius, 12px padding, 16px font.
Field spacing 12–16px, group spacing 16–24px.

Field types: Full Name, Email, Phone, Experience, Salary Expectation, Notice Period,
Resume Upload, Short/Long Text, Dropdown, Multiple Choice, File Upload.

### Calendar / Scheduling
Slots 48px height, 8px radius. Available (green), Unavailable (gray), Pending (amber),
Confirmed (blue).

### Modals
Rounded 16px, white, 24px padding. Primary and cancel actions.

### AI Components
AI Analysis Card, Match Score Badge, Skills Chips, Strengths/Weaknesses Panel,
Ranking Rationale Box, Pipeline Stepper, Status Logs, Failed Resume Alert.

## Accessibility

- Strong color contrast
- Readable font sizes
- Focus states for interactive elements
- Labels on all form fields
- Tables with clear spacing
- Status colors supplemented with icons/text — never color alone

## Component Naming Conventions

- AppShell / Sidebar / SidebarItem
- Header / PageHeader
- Button / Primary / Secondary / Destructive
- Card / KPI / Job / AIAnalysis
- Badge / Status / MatchScore
- Table / DataTable / CandidateRanking
- Form / Input / Select / Textarea / Upload
- Modal / Confirmation
- Calendar / AvailabilitySlot
- Email / Editor
- Chart / Bar / Funnel
- EmptyState / Generic
- Alert / Error / Warning
- Stepper / AIProcessing

---

## Screens not covered by Stitch

The public candidate apply page (`/apply/{slug}`) is new — it did not exist in the
original design because the candidate form was going to be a Google Form (see ADR-001).

It should deliberately **not** use AppShell. No sidebar, no recruiter chrome. Centered
single column, max-width ~640px, on `#F8FAFC`, with the job title as Page Title and the
company/recruiter name as helper text. It is the only screen an outside user ever sees,
so it carries the product's first impression on its own.
