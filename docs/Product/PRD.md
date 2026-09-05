# CreatorRetain — Product Requirements Document

**Version:** 1.1
**Status:** Product source of truth
**Date:** September 2026
**Category:** Creator economy / B2B SaaS / creator hiring platform

Changes from 1.0: added §55 on scheduled work, moved the entitlements
layer earlier in the build order (§54), and reclassified three open
items as schema blockers rather than business questions (§56).

---

## 1. Product vision

CreatorRetain is a platform where brands build long-term creator
partnerships through monthly retainers instead of one-off influencer
campaigns.

A brand should be able to discover suitable creators, evaluate their
profiles and audience, contact or invite them, propose a monthly
retainer, define monthly deliverables, manage the relationship,
approve work, pay the creator, and renew, pause or end the retainer.

A creator should be able to build a professional profile, display
platforms and engagement, set rates, receive opportunities, accept
retainers, complete monthly deliverables, track earnings, and build
long-term brand relationships.

An agency should be able to manage its internal team, represent
creators, manage those relationships, participate in brand
engagements, and run multiple creators from one workspace.

The platform's central business object is the **retainer**, not the
campaign.

---

## 2. The problem

Influencer marketing is structured around one post, one reel, one
campaign, one short collaboration.

**Brands** constantly need new creators, get inconsistent content,
renegotiate repeatedly, lack continuity, and often cannot afford a
full-time content team.

**Creators** have unpredictable income, relationships that end after
one campaign, and no visibility into future earnings.

**Agencies** manage creators through fragmented tools and lack
structured visibility into relationships and engagements.

---

## 3. The solution

Convert creator marketing from:

> one-off campaign → one payment → relationship ends

into:

> creator partnership → monthly retainer → recurring deliverables →
> recurring payment → renewal

A creator should function like a long-term external member of a
brand's content team.

---

## 4. Thesis

Brands want consistent creator output. Creators want predictable
income. Retainers connect those incentives.

Profiles, discovery, subscriptions, campaigns and collaboration exist
to support: **find → hire → retain → renew.**

---

## 5. Users

### 5.1 Brands

The primary paying customer. D2C, fashion, beauty, skincare,
restaurants, cafés, fitness, local businesses, apps, startups,
events, personal brands, e-commerce.

They want to find creators, build creator teams, hire monthly, manage
deliverables and maintain long-term relationships.

### 5.2 Creators

Primarily free users. Nano and micro creators across lifestyle, food,
fashion, fitness, travel, tech, gaming, education, video, editing and
local content.

They want professional presence, brand opportunities, recurring
income, and long-term partnerships.

### 5.3 Agencies

Agencies represent and manage creators. An agency is not a creator
workspace.

**Agency staff are workspace members. Represented creators are not.**
This distinction is architectural, not cosmetic.

Staff hold Owner, Admin or Member roles.

### 5.4 The CreatorRetain team

An operational user type. The platform team runs managed campaigns,
creator selection, coordination, brand support, verification,
disputes and operations. This matters most for the Managed tier.

---

## 6. Workspace architecture

Every account operates through a workspace, typed Creator, Agency or
Brand.

**Creator workspace** — an individual creator. Cannot invite staff.

**Agency workspace** — an agency and its employees. Owner, Admin,
Member.

**Brand workspace** — a company managing creator partnerships. Owner,
Admin, Member.

Workspace membership is separate from creator representation.

---

## 7. Creator representation

Representation is a distinct relationship from membership. A creator
keeps their own Creator workspace even when represented.

```
Agency workspace
       │ represents
       ▼
Creator workspace
```

This prevents the creator becoming an employee of the agency.

States: INVITED, ACTIVE, ENDED, with dates and history.

---

## 8. Creator profile

One of the most important objects in the product.

**Basic:** display name, bio, location, country, languages, content
categories, skills.

**Platforms** (Instagram, YouTube, TikTok at launch): handle, profile
URL, follower count, engagement rate. Further platforms must be
addable without redesigning the schema.

---

## 9. Creator metrics

Profiles display followers, engagement rate, platform, average views
where available, categories, portfolio, pricing and verification
status.

**Follower data model.** Self-reported counts are allowed for MVP.
Platform API verification becomes the premium mechanism behind
Verified status — self-reported ships fast, and API connection gives
Verified something real to sell.

**Tension to resolve (see §36):** self-reported counts and
fake-follower detection collide the first time a brand disputes a
retainer over inflated numbers. Decide what recourse exists before
real money moves.

---

## 10. Creator pricing

Creators define pricing, eventually supporting a monthly retainer
figure (e.g. ₹30,000/month) and deliverable pricing — reels in
various quantities, stories, editing, posting, promotion, content
strategy.

Keep the structure flexible; different creator categories need
different packages.

---

## 11. Verification

A paid feature. Benefits: verification badge, verified social
metrics, increased trust, better discovery visibility, eligibility
for certain brand opportunities.

Verification must mean something rather than being decorative.

---

## 12. Boost

Creators pay for increased discovery visibility — search placement,
discovery placement, featured sections.

Boosted creators must remain distinguishable from organically ranked
ones.

---

## 13. Discovery

The primary mechanism by which brands find creators.

Filters: category, platform, follower count, engagement rate,
location, language, pricing, skills, verification, availability.

Later: audience demographics, average views, previous brand
categories, performance history.

---

## 14. Discovery ranking

Ranking considers profile completeness, relevance, verification,
engagement, creator quality, availability, performance history and
boost status.

Boosting improves visibility but must not replace relevance.

---

## 15. Brand plans

| Tier | Unlocks |
|---|---|
| Free | Basic account, limited discovery, limited profile views |
| Pro | Full discovery, contact creators, post campaigns, hiring workflows |
| Business | Everything in Pro, campaign dashboard, multiple relationships, unlimited hiring, advanced collaboration |
| Managed | The CreatorRetain team identifies, selects and coordinates creators |

Managed is a service, not a feature flag. Its fees are separate from
software subscription pricing.

---

## 16. Creator plans

| Tier | Unlocks |
|---|---|
| Free | Profile, basic presence, basic discovery, portfolio, basic opportunities |
| Verified | Badge, verified identity and metrics, trust, discovery advantage |
| Boosted | Higher placement, featured and promotional visibility |

---

## 17. Pricing

Actual prices are not final. **Architecture must not hard-code
pricing.** Tier boundaries are settled; the numbers are configurable.

---

## 18. Retainer — the core object

A retainer is the primary commercial relationship between a brand and
a creator: recurring monthly payment for an agreed set of work.

A **campaign** is a marketing initiative. A **retainer** is an
ongoing commercial relationship. One retainer may contain many
monthly cycles.

---

## 19. Retainer terms

| Term | Product name |
|---|---|
| 1 month | Trial |
| 3 months | Growth |
| 6 months | Brand Ambassador |
| 12 months | Creator Partner |

Longer commitment should mean lower effective monthly pricing.
Discount percentages TBD.

---

## 20. Retainer data

`id`, `brand`, `creator`, `agency` (if applicable), `monthly_value`,
`platform_commission_rate`, `term`, `start_date`, `end_date`,
`status`, `payment_status`, `created_at`, `updated_at`.

---

## 21. Retainer status

PROPOSED — offered, not accepted.
ACTIVE — currently running.
PAUSED — temporarily halted.
COMPLETED — reached its end successfully.
CANCELLED — ended before normal completion.

---

## 22. Retainer deliverables

Every active retainer carries recurring monthly deliverables: reels,
stories, posts, editing, captions, posting, community engagement,
monthly reporting.

Each holds title, description, due date, status, submission, approval
and comments.

---

## 23. Monthly workflow

```
Brand discovers creator
        ↓
Contacts or invites creator
        ↓
Retainer proposed
        ↓
Creator accepts
        ↓
Retainer ACTIVE
        ↓
Monthly deliverables created
        ↓
Creator submits work
        ↓
Brand reviews and approves
        ↓
Payment processed
        ↓
Next monthly cycle
        ↓
Renew / pause / complete / cancel
```

This is the core product loop. Several of these steps require
scheduled work that nothing currently triggers — see §55.

---

## 24. Campaigns

Campaigns sit underneath the wider relationship. They hold objective,
description, budget, dates, creators, deliverables, status and
approval workflow.

---

## 25. Multi-creator hiring

Brands hire one creator, several, or a team.

```
Brand
 └── Campaign
      ├── Creator A → reels
      ├── Creator B → stories
      ├── Creator C → UGC
      └── Creator D → editing
```

Especially important for Business and Managed customers.

---

## 26. Collaboration

Invitations, creator applications, brand invitations, retainer
offers, deliverable assignments, approvals, notifications, messaging.

Native messaging is not required initially — WhatsApp and email work.
Build it when usage proves the need.

---

## 27. Workspace permissions

**Owner:** view members, invite, cancel and resend invitations, view
sent invitations, remove members, change roles, remove admins,
transfer ownership, delete workspace.

**Admin:** view members, invite, cancel and resend invitations, view
sent invitations, remove regular members, promote members. Cannot
remove or modify another admin, transfer ownership, or delete the
workspace.

**Member:** access permitted functionality, leave workspace. No
membership management.

---

## 28. Ownership

Exactly one owner per workspace. The owner cannot leave without
transferring ownership first.

Transfer must verify the current owner, verify the target belongs to
the workspace, transfer ownership, demote the previous owner
appropriately, and preserve history.

---

## 29. Invitations

Invite, accept, decline, cancel, resend, view my invitations, view
sent invitations.

History is retained for audit rather than deleted. Already
implemented and validated.

---

## 30. Payments

The platform earns roughly 10–20% of monthly retainer value.

> ₹50,000 monthly retainer at 10% → ₹5,000 platform, ₹45,000 to the
> creator or agency.

Commission may vary by plan or transaction.

---

## 31. Payment architecture

Design so payment processing *can* eventually run through the
platform, but do not assume automated money movement for MVP until
KYC, processing, escrow, refunds, disputes, tax and financial
regulation are resolved.

Phase 1: payment tracking.
Phase 2: payment integration.
Phase 3: automated recurring payments and escrow where legal.

---

## 32. Payment states

PENDING, AUTHORIZED, PAID, FAILED, REFUNDED, DISPUTED.

Linked to brand, creator, retainer, month, deliverables, amount,
commission and status.

---

## 33. Early cancellation

Must be defined before real retainers launch. Recommended structure:
notice period, possible early termination fee, documented reason.

Notice length and fee are business and legal decisions and must not
be hard-coded.

---

## 34. Agency retainer model

```
Brand
   │ retainer
   ▼
Creator
   ▲ represented by
   │
Agency
```

**Schema blocker.** Whether payment flows brand → creator or brand →
agency → creator determines who `payments.payee` points at and who
the commission is deducted from. The database should support both,
but the default must be chosen before the payments table is written.

---

## 35. Reviews and reputation

Brands review creators on reliability, quality, communication,
timeliness and completion. Creators review brands on payment
reliability, communication, professionalism and scope clarity.

Reviews attach to completed engagements, not free anonymous ratings.

---

## 36. Trust and safety

Creator and brand verification, payment protection, dispute handling,
content approval logs, fake-follower detection, sponsored-content
compliance, cancellation policies, audit history.

Trust matters more here than in transactional marketplaces because
the platform encourages multi-month commitments.

---

## 37. Notifications

Channels: in-app, email, push, optionally SMS or WhatsApp.

Events: invitation received and accepted, retainer proposed and
accepted, deliverable due, submitted and approved, payment processed
and failed, retainer ending, renewal, cancellation.

Several of these are time-triggered rather than action-triggered —
see §55.

---

## 38. Admin platform

**Users:** view, suspend, verify.
**Creators:** review profiles, verify, feature, manage boosts.
**Brands:** review, verify.
**Retainers:** view, monitor disputes and cancellations.
**Payments:** monitor, track commission, handle issues.
**Platform:** manage subscriptions, pricing, featured creators,
metrics.

---

## 39. Managed service

A brand says: "We need creators, but we don't want to manage
selection ourselves."

CreatorRetain handles requirements gathering, creator selection,
shortlisting, campaign planning, coordination, deliverable management
and reporting.

Managed revenue is separate from SaaS revenue.

---

## 40. Business model

| Revenue | Description |
|---|---|
| Retainer commission | 10–20% of monthly retainer value |
| Brand subscriptions | Free / Pro / Business / Managed |
| Creator verification | Paid verification |
| Creator boost | Paid visibility |
| Managed service | Human-managed creator programs |

Enterprise later.

---

## 41. MVP scope

**Authentication** — signup, login, JWT, password security.

**Workspaces** — creator, agency and brand workspaces; members;
roles; invitations.

**Creator** — profile, social platforms, metrics, portfolio, pricing.

**Brand** — profile, creator discovery, creator profiles, search and
filtering.

**Hiring** — creator invitation, retainer proposal, acceptance.

**Retainers** — creation, terms, monthly value, status, deliverables.

**Collaboration** — member management, invitations, permissions.

Note: MVP includes retainers but not paid subscriptions, so it ships
without Free-tier limits enforced. The entitlements *layer* still
ships early (§54) even though billing does not.

---

## 42. Explicitly not MVP

Native mobile apps. Advanced AI matching. Complex analytics. Full
escrow. Sophisticated fake-follower detection. Enterprise
administration. Contract and e-signature systems. Social APIs for
every platform. Full native messaging.

---

## 43. Development phases

**Phase 1 — Foundation.** Complete: authentication, users,
workspaces, members, invitations.

**Phase 2 — Collaboration.** Complete: list members, remove, leave,
change role, transfer ownership, Owner/Admin authorization,
integration tests.

**Phase 3 — Creator profiles.** Profile, social accounts, metrics,
categories, skills, portfolio, rates, verification status,
availability.

**Phase 4 — Entitlements.** Plan on a workspace and a service-level
capability check. No billing.

**Phase 5 — Discovery.** Search, filters, ranking, profile view,
shortlisting, contact and invite.

**Phase 6 — Agency representation.** Roster, representation
invitations, status, agency creator management, visibility into
retainers.

**Phase 7 — Retainers.** Proposal, acceptance, terms, monthly value,
status, deliverables, monthly cycles, renewal, pause, cancellation.

**Phase 8 — Campaigns.** Creation, creator assignment, deliverables,
submission, approval, status.

**Phase 9 — Payments.** Records, states, commission calculation,
creator earnings, brand history, platform revenue. Processing after
compliance decisions.

**Phase 10 — Billing.** Subscription charging on top of the Phase 4
entitlements layer.

**Phase 11 — Managed platform.** Internal tooling for selection,
requirements, shortlisting, campaign and retainer management,
operations, reporting.

---

## 44. Technical principles

```
Router → Service → Repository → Database
```

**Routers:** HTTP, auth dependencies, request and response schemas,
HTTP errors.

**Services:** business rules, permissions, state transitions,
validation, workflows.

**Repositories:** queries and persistence.

Business logic must not move into repositories.

---

## 45. Security

JWT authentication, password hashing, workspace isolation, permission
validation, ownership validation, resource ownership, invitation
authorization, input validation, audit history.

A user must never reach another workspace's resources by changing an
ID in a request.

---

## 46. Database

**Current:** `users`, `workspaces`, `workspace_members`,
`workspace_invitations`.

**Future:** `creator_profiles`, `creator_social_accounts`,
`creator_portfolio_items`, `creator_rates`, `representations`,
`campaigns`, `campaign_creators`, `deliverables`, `retainers`,
`retainer_deliverables`, `retainer_months`, `payments`,
`platform_commissions`, `subscriptions`, `plans`, `reviews`,
`notifications`, `admin_actions`, plus whatever §55 requires.

PostgreSQL on Supabase, Alembic migrations.

---

## 47. Success metrics

1. **Active retainers** — how many brand → creator retainers are
   running.
2. **Retainer duration** — how many months relationships last.
3. **Renewal rate** — how many retainers renew after their term.
4. **Monthly retainer GMV.**
5. **Platform revenue** — commission plus subscriptions plus other.

**Creator metric:** do creators return unprompted, without a brand or
agency pushing them?

Signup count is not a success metric.

---

## 48. Flywheel

```
More creators → better discovery → more brands → more retainers
→ more creator income → more creator retention → more creators
```

```
More retainers → more commission → more investment in discovery
and trust → better product → more retainers
```

---

## 49. Core journeys

**Brand:** signup → profile → plan → discover → filter → view
creator → invite → propose retainer → creator accepts → retainer
begins → monthly deliverables → approval → payment → renew.

**Creator:** signup → creator workspace → build profile → connect
socials → portfolio → pricing → discoverable → receive opportunity →
review retainer → accept → monthly work → get paid → renew.

**Agency:** signup → agency workspace → invite staff → build roster →
represent creators → find opportunities → manage engagements → track
retainers.

---

## 50. What this is not

Not another Instagram, Fiverr, Upwork, influencer directory, one-off
campaign marketplace, or generic project-management tool.

The differentiator is long-term creator hiring through structured
monthly retainers.

---

## 51. Positioning

Between influencer marketplace, creator management platform,
recurring hiring and campaign management.

Central differentiator: a monthly, employment-shaped relationship
without employment. The creator stays independent; the brand gets
ongoing access.

---

## 52. North star

Optimize for **more successful, longer-lasting creator–brand
relationships.** Not accounts, campaigns or profile views.

```
Brand hires creator → retainer starts → work completed
→ payment happens → brand renews → creator continues
```

---

## 53. Definition

CreatorRetain is a creator hiring platform that helps brands build
long-term creator teams through monthly retainers, while giving
creators predictable recurring income and agencies structured tools
to manage creator relationships.

**Core object:** retainer.
**Primary customer:** brand.
**Creator value:** predictable recurring income.
**Brand value:** consistent creator support without a full-time team.
**Agency value:** structured creator and engagement management.
**Primary revenue:** 10–20% recurring monthly commission.
**Secondary revenue:** subscriptions, verification, boosts, managed
services.
**North star:** active retainers and retained months.

---

## 54. Build order

```
1.  Authentication              done
2.  Users                       done
3.  Workspaces                  done
4.  Workspace collaboration     done
5.  Creator profiles
6.  Creator social + portfolio
7.  Entitlements layer
8.  Discovery
9.  Agency representation
10. Retainer proposals
11. Retainers
12. Deliverables + scheduling
13. Campaigns
14. Payments + commission
15. Billing + subscriptions
16. Reviews / trust
17. Managed operations
18. Analytics
19. AI / advanced
```

**Why entitlements moved to 7.** Free tier's defining feature is
*limited* discovery. Verification and boost both affect ranking. Pro
unlocks contact and retainer creation. Every one of those is a
capability check, so discovery, retainers and contact would each need
retrofitting if the layer arrived at 15.

Position 7 is not billing. It is a plan column on the workspace and a
service-level `can(workspace, capability)` check that features call.
Charging money arrives at 15 and writes to the same layer.

---

## 55. Scheduled work

Nothing in the current system is time-triggered. Invitations expire
lazily — status is computed on read, which works because someone
always opens them.

The retainer loop breaks that assumption. These need to happen with
no user present:

- Generate next month's deliverables when a cycle rolls over
- Mark deliverables overdue when a due date passes
- Raise the monthly commission and payment record
- Warn both sides that a retainer is ending
- Move a retainer to COMPLETED at its end date
- Send renewal prompts before expiry
- Expire proposed retainers that were never answered

**Decision needed before the retainer schema is written:** cron
process, job queue, or lazy generation on read.

Lazy generation is cheapest and matches the invitation pattern, but
it fails where nobody reads — a creator who never logs in still needs
their deliverables to exist and their payment recorded. A scheduled
worker is the honest answer for anything touching money.

This affects `retainer_months`, `deliverables`, `payments` and
`notifications`, and it is the largest piece of infrastructure the
product does not yet have.

---

## 56. Open decisions

| # | Question | Blocks |
|---|---|---|
| 1 | Self-reported vs API follower counts | `creator_social_accounts` schema |
| 2 | Does money move through the platform? | Payment architecture, compliance |
| 3 | Brand → creator or brand → agency → creator? | `payments.payee`, commission source |
| 4 | What does Free tier "limited" mean? | Discovery, entitlements |
| 5 | Scheduling: cron, queue, or lazy? | Retainer and deliverable schema |
| 6 | Early termination: notice, fee, or neither? | Retainer cancellation logic |
| 7 | Actual prices per tier | Billing only, not schema |
| 8 | Recourse when follower counts are inflated | Trust and safety, disputes |

Items 1, 3 and 5 are schema blockers. Settle them before writing the
tables they affect.
