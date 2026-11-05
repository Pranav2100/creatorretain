# Roadmap

Where CreatorRetain is, what is left, and the decisions already
taken so they are not re-litigated. Kept here rather than in a
chat, because chats do not persist.

Last updated 6 November 2026.

## Built

- **Accounts and workspaces** — auth, onboarding, three workspace
  types (creator / brand / agency), plans and entitlements.
- **Creator profiles and discovery** — profiles, search by beat,
  platform, reach, language and budget, public brand pages.
- **Retainers** — offers with deliverables, monthly periods,
  pause and end by mutual approval, notice periods, append-only
  event history, per-retainer assignment.
- **Team and roles** — invitations, a join gate requiring details
  before accepting, named contact, four built-in roles, and
  custom roles on top of them.
- **Messaging** — requests, accept / decline / block,
  cold-contact limits, unread counts in the header.
- **Live updates** — every signed-in page polls a pulse endpoint
  and refreshes itself; nothing needs a manual reload.
- **Notifications** — an outbox: an event writes a row in the
  same transaction, a drain sends it afterwards. Email only so
  far.
- **Theming plumbing** — every colour is a token, light and dark
  resolved before first paint, skeleton screens, custom 404 and
  error pages. The *mechanism*, not the final look.

Verification: 13 suites, 531 in-process checks, plus
`verify_schema.py` which runs the real migration chain against
PostgreSQL and compares the result against the models column by
column.

## Left, in order

### 1. Payments

Plan changes are not wired to anything. Settings says so.

### 2. Final UI

The visual design has never been settled. This is deliberately
late: because every colour is a token, restyling is editing one
block rather than hunting through components.

### 3. Deployment

Includes three things that notifications depend on:

- **An SMTP provider.** `EMAIL_BACKEND` is still `console`, so
  emails print to the terminal. Any of Resend, Postmark, SES or
  Mailgun will do; all speak SMTP, so it is a `.env` change and
  not code.
- **The drain on a schedule.** `drain_notifications.py` has to
  run every minute or so. Nothing runs it today.
- **DNS for the sending domain** — SPF, DKIM, DMARC. Skipping
  this is how an app ends up in spam.

### 4. Mobile app, with push

Planned. Notes from working out what it would take:

The part that decides *whether to tell somebody* is already
channel-independent and transfers unchanged — who is responsible
for a retainer, never tell the person who did it, never tell a
read-only Member, one notification per thing, respect the
switches, drop it if they have already read it. Only the last
step is email-specific.

What would be new:

- A `device_tokens` table — which phones belong to which user.
- A channel on the notification row. It currently holds
  `to_email`; it would hold where to send rather than an address.
- A `PushSender` beside `EmailSender`, same interface. Expo's
  push service if React Native, otherwise FCM and APNs.
- Per-channel switches. Most people want push for messages and
  email for offers, so the three switches become a small grid.

One design difference, worth not getting wrong: **push should
not wait.** The ten-minute delay on message email exists because
email is intrusive and you might read it yourself first. Push is
the opposite - it is how you find out. Messages should push
immediately, and email only if the person still has not looked.

The API needs nothing: it is a REST API and the web app is one
client among others.

**Open:** React Native or native. It changes the push plumbing
and little else.

## Decisions already taken

- **Custom roles are additive, and bounded by subset.** A custom
  role only ever adds permissions on top of a built-in one;
  there is no way to express "an Admin, but without X". You can
  only put into a role what you already hold, only edit a role
  whose permissions you hold, and only grant one to somebody you
  outrank. Position in the list is presentation, not authority -
  a deliberate departure from Discord.
- **Notifications are an outbox, not inline sends.** A
  notification is a consequence, never the thing itself:
  accepting an offer must not fail because a provider is down.
- **Security email has no off switch.** Three preference
  switches, not four. An email saying your password changed is
  only worth anything if whoever changed it could not have
  turned it off.
- **Dark palette** — `#14171a` paper, `#7fb49f` sage accent.
  Proposed and used without objection; treat as settled unless
  the final UI pass says otherwise.

## Known gaps

- **Four lint errors**, all pre-existing: three
  `react-hooks/set-state-in-effect`
  (`app/setup/setup-form.tsx`, `app/settings/forms.tsx`,
  `app/messages/[id]/forms.tsx`) and one unused variable in
  `app/actions/workspace.ts`. They would fail a CI lint gate.
- **Period rollover happens on read, not on a schedule.**
  `ensure_periods` works out which months should exist whenever
  something reads a retainer. That is correct but means a
  retainer nobody looks at produces nothing until somebody does.
  A nightly job calling the same function would fix it; the
  function was written with that in mind.
- **Message notifications go to the workspace owner.** A
  conversation is between two workspaces rather than two people,
  and the owner is the only person guaranteed to be able to see
  it. Routing to whoever actually handles the account is worth
  doing once conversations are tied to one.

## Testing

Suites live in `apps/api/verify_*.py` and run in-process against
in-memory SQLite:

    uv run python verify_retainers.py

`verify_schema.py` is the exception — it needs a real PostgreSQL
and executes the migrations, which is the one thing the others
cannot do. Everything it writes is rolled back, so it is safe to
point at a database that matters.
