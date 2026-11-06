# Roadmap

Where CreatorRetain is, what is left, and the decisions already
taken so they are not re-litigated. Kept here rather than in a
chat, because chats do not persist.

Last updated 7 November 2026.

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
- **Plan subscriptions** — buying Pro or Business through a
  provider, behind a switch that is off. See *Payments* below.

Verification: 14 suites and 585 in-process checks, plus
`verify_schema.py`, which runs the real migration chain against
PostgreSQL and compares the result against the models column by
column — 4 more, and the only ones that touch a real database.
589 in all. Counted with the loop in *Testing* below rather
than by memory, because this number was quoted wrongly three
times in one evening.

What the suites did *not* catch, and clicking the real page did:
stacked checkouts on repeated presses of Choose, a confirmation
that described something that had not happened, a Plan section
missing from the pulse, and a page frozen by the browser's
back-forward cache. Checks now cover all four. Worth remembering
the next time the suite passing feels like being finished.

## Left, in order

### 1. Payments — built, switched off

Plans can be bought. `BILLING_PROVIDER` defaults to `fake`, so
nothing can take money until the six values below are set. The
rule the whole design rests on: **the provider grants the plan,
not the request** — pressing Choose writes a pending row and
sends the person off to pay, and the plan arrives only when a
signed webhook says it was paid for.

Prices are placeholders. All of them must stay under **₹15,000**,
the RBI ceiling for auto-debit: above it every single monthly
charge needs an OTP from the payer, which ends automatic
renewal. Razorpay's live mode also needs a registered business
entity, so until CreatorRetain is incorporated, test mode is as
far as this can go.

#### Turning Razorpay on

1. **Keys.** Dashboard in **Test** mode → Account & Settings →
   API Keys → Generate Key. The secret is shown once; download
   it there and then. Test keys need no website. Live keys need
   verified website details, which Razorpay checks in about
   three working days — start that before it is urgent.
2. **Two plans.** Subscriptions → Plans, monthly, INR, one per
   paid tier. Each gives a `plan_id` like `plan_0000...`. Prices
   live in Razorpay, not here, so changing one later means a new
   plan there rather than an edit in this repo.
3. **Webhook.** Settings → Webhooks → `https://<api>/billing/webhook`.
   The secret is one you invent; it must match
   `RAZORPAY_WEBHOOK_SECRET`. Subscribe to exactly the eight the
   code handles: `subscription.authenticated`, `.activated`,
   `.charged`, `.pending`, `.halted`, `.cancelled`, `.completed`,
   `.expired`. With no secret set the code rejects every webhook
   rather than trust an unsigned one — which looks exactly like
   "payments never activate".
4. **Six values in `apps/api/.env`:** `BILLING_PROVIDER=razorpay`,
   `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`,
   `RAZORPAY_WEBHOOK_SECRET`, `RAZORPAY_PLAN_PRO`,
   `RAZORPAY_PLAN_BUSINESS`.

Testing this on a laptop needs a tunnel (ngrok or similar) to
port 8000, because the webhook has to arrive from the internet.

A second provider is a new file implementing the same four
methods, not a change to the service.

### 2. Final UI

The visual design has never been settled. This is deliberately
late: because every colour is a token, restyling is editing one
block rather than hunting through components.

### 3. Cleanup, before anything is deployed

One pass over the whole codebase, for two reasons: nothing
should ship that is no longer true, and the next person to read
this - a new developer, or either of us in six months - should
not have to work out which parts still count.

**Things a later decision made obsolete.** The one already
found, and the reason this section exists:

- **`ALLOW_SELF_SERVE_PLAN_CHANGE` still defaults to `true`.**
  It was the stand-in for billing - it lets an owner move their
  own workspace between plans. Billing now exists, so shipping
  with this on means anyone can give themselves Business for
  free. It must be `false` in production, and the default here
  should probably be flipped so that forgetting the variable
  fails closed rather than open.

The rest of the pass looks for more of the same:

- Code, settings, columns and migrations kept for a decision
  that has since changed.
- Exports nobody imports, dependencies nobody uses, environment
  variables nothing reads.
- Comments describing how something used to work.
- The four lint errors under *Known gaps*, so a CI gate can be
  added without it going red on day one.

**Readable by somebody new.** The architecture holds up - router
to service to repository to model, permissions in one place,
derived state over stored state - but almost none of it is
written down outside the code. What a new developer would need:

- A README that gets the thing running: the two apps, the
  environment variables, the migrations, how to seed a usable
  account.
- The conventions that are not guessable and have each already
  cost a bug: SQLAlchemy persists enums by `.name`, so every
  Postgres enum carries uppercase labels; `TimestampMixin` adds
  `deleted_at` as well as the other two, so migrations must
  create all three; `save()` commits, so anything flushed after
  it is lost; migrations spell enum labels inline because the
  checker reads them as text.
- Why the odd-looking choices are that way, so nobody
  "simplifies" them back into bugs.

Worth doing before deployment rather than after, because
deployment is when somebody is most likely to change something
in a hurry.

### 4. Deployment

Includes three things that notifications depend on:

- **An SMTP provider.** `EMAIL_BACKEND` is still `console`, so
  emails print to the terminal. Any of Resend, Postmark, SES or
  Mailgun will do; all speak SMTP, so it is a `.env` change and
  not code.
- **The drain on a schedule.** `drain_notifications.py` has to
  run every minute or so. Nothing runs it today.
- **DNS for the sending domain** — SPF, DKIM, DMARC. Skipping
  this is how an app ends up in spam.

### 5. Mobile app, with push

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

All of them at once, with the total, from `apps/api`:

    for f in verify_*.py; do uv run "$f" | grep -E '^[0-9]+ (passed|failed)'; done \
      | awk '{p+=$1; f+=$3} END {print p" passed, "f" failed"}'

(PowerShell has no `awk`; run this in Git Bash, or just read the
last line of each suite.)
