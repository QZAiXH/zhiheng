# UI prototype

Read this for page presentation, important interaction flows, or broad layout choices. Use the project's actual design system and product context. A new page, major operation-flow change, or broad layout change needs approval of a concrete interactive artifact before business UI implementation.

## Choose a host

Prefer a plausible existing visual shell: header, navigation, surrounding content, realistic data density, and the intended user role. Work in an isolated prototype workspace or a clearly gated prototype surface; do not replace production business behavior while exploring.

- If the proposed content naturally belongs inside an existing page, render variants in that host while retaining its relevant read-only context and simulated role/data behavior.
- If it is genuinely a new surface with no suitable host, create a clearly labeled prototype route following the project's routing conventions, or a self-contained interactive artifact when that better serves review.

Use simulated mutations. Existing read access may be reused within authorization; actions such as save, delete, payment, or permission changes use stubs or an isolated fixture. Label sample data without exposing implementation details in ordinary product interactions.

## Define what alternatives should settle

Use several structural variants when the design direction is open: three is a useful default, fewer for a focused question, and more only when each tests a distinct idea. An already selected direction needs only the artifact necessary to validate it. Variants should differ in information hierarchy, navigation, layout, or the primary action, rather than colors alone.

Keep comparable scenarios and content across variants. Each needs the main user path and applicable loading, empty, error, unavailable, and permission states. Use realistic long text and data density where they affect the decision. Include relevant responsive behavior and keyboard access for the intended audience.

## Variant switching when applicable

For route-based alternatives, a `?variant=A` search parameter gives a shareable and reload-stable selection. Use the project's router and preserve unrelated parameters. Provide a small, clearly separate switcher with current label and previous/next controls. Keyboard shortcuts should not intercept typing or editing. Ensure the switcher does not obscure important content.

Keep variant rendering free to change structure; share established components but avoid a shared layout that forces all alternatives into the same shape. Gate prototype controls out of production using an actual project-supported mechanism. Do not add a new shared production abstraction solely to support disposable variants.

## Verify and present

Use the actual startup entry and exercise navigation, variant switching, main actions, and relevant states. Confirm that simulated actions cannot accidentally mutate the live backend. Check the intended viewport range and meaningful keyboard behavior. Record what was actually observed; list interaction checks that could not be run.

Present the runnable URL or artifact, variant keys, what differs, the primary review scenarios, known assumptions, and a recommendation tied to the page's purpose. Capture a chosen variant or explicit combination, why it was selected, requested changes, and the approved artifact version. Recheck affected parts after feedback; a changed major flow may invalidate approval of that flow without invalidating unrelated decisions.

## Preserve and transition

Keep the reviewed variants and feedback in durable task material or an already authorized artifact/branch. Link the chosen design from the effective specification. Production implementation follows after required approval and normal implementation verification; the exploratory code does not become production-ready simply because its appearance won.

When implementing later, remove prototype-only controls and discarded variants from the product within the implementation scope while retaining the necessary review evidence. A prototype-only assignment ends with its artifact, observations, decision status, and next step; it does not automatically commit or deploy anything.

Completion requires an accessible interactive artifact, exercised relevant paths and states, traceable observations, and explicit choice/approval status. If approval is pending, keep that dependency visible rather than reporting finalized UI design.

Adapted from Matt Pocock's `prototype/UI.md`; see [source and license](upstream.md).
