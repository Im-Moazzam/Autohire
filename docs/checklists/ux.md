# UX definition of done

A screen is not finished when the happy path renders. It is finished when all five
states exist and the words are right. Every PR touching UI is reviewed against this.

## The five states

Every screen and every data-fetching component ships all five:

1. **Loading** — skeleton matching the real layout for tables and cards; spinner only
   for actions under ~300ms. A layout that jumps when data lands is a bug.
2. **Empty** — never a blank panel. Say what would appear here and give the action that
   makes it appear. "No jobs yet" + a **Create job** button.
3. **Error** — what went wrong and what to do next. Retry where retry is possible.
4. **Partial / degraded** — some rows parsed, some failed. AutoHire hits this constantly:
   a ranking table where three resumes failed to parse must show the ranked ones *and*
   surface the failures. Never silently drop rows.
5. **Success** — confirmation the action landed. Toast for background work, inline for
   immediate work. Never both.

## Writing

From `docs/design.md`, and it is enforced, not aspirational:

- Name things by what the user controls, not how we built it. "Application form",
  not "template instance".
- Buttons say what happens: **Save changes**, not Submit. **Launch job**, not Create.
- An action keeps its name through the whole flow. **Publish** → toast says *Published*.
- Errors don't apologise and are never vague. "Resume must be PDF or DOCX under 5MB",
  not "Something went wrong".
- Sentence case everywhere. One job per element — a label labels, help text explains,
  neither does both.

## Interaction floor

- Every interactive element is keyboard reachable with a visible focus ring
- Destructive actions behind a confirm modal that names the thing being destroyed
- Forms validate inline on blur, not only on submit; the first invalid field receives focus
- Long operations (AI processing) show progress and what stage they're at, not an
  indeterminate spinner — the pipeline stepper in `design.md` exists for this
- Optimistic updates for cheap toggles; never for anything that calls an external API
- Status is never communicated by colour alone — icon or text always accompanies it

## AutoHire-specific

- **Reconnect Google** banner is persistent and non-dismissable in `REAUTH_REQUIRED`.
  Every action that needs a Google call is disabled with a tooltip explaining why.
- Match scores show the number *and* the band. A bare 0.73 means nothing to a recruiter.
- Every AI output is accompanied by its evidence, or a link to it. A ranking a recruiter
  cannot interrogate is one they will not trust — that is the whole explainability thesis.
- Candidate-facing pages carry no recruiter chrome and no AutoHire jargon.
