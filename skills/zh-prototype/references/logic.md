# Logic and state-model prototype

Read this when the question concerns business logic, legal state transitions, or a data shape that must represent awkward cases. The default artifact is one self-contained HTML file that a non-developer can open without installing a runtime or starting a server.

## State the question

Put a short visible introduction at the top: what model is being explored, which question is open, which requirements are already fixed, and what observations would support or reject the idea. Label simulated inputs and assumptions. Keep the effective model/decision version in its task reference.

## Isolate the model

Keep the decision logic separate from DOM rendering and button handlers. Choose the smallest suitable form:

- A reducer `(state, action) => state` for discrete events over one state value.
- An explicit state machine when action legality depends on current state.
- Pure transformations over plain data when there is no ongoing implicit state.
- A small module with owned state when state ownership is the question.

The UI invokes that model and renders its result; the model does not inspect the DOM. Use domain language in the visible controls. Keep state in memory by default. When persistence behavior is the question, use a clearly isolated disposable store and record its initialization/reset method; do not point the prototype at production data.

## Make the model explorable

Arrange the page around the question:

1. Title and introduction.
2. The full relevant state as readable labeled fields, refreshed after each action; highlight the important change where helpful.
3. Free-play controls for the relevant actions and a reset action.
4. Guided scenarios in separate tabs or clearly distinct sections, with a short situation, what to watch for, and real step buttons.

Start each guided scenario from a known state. Include a normal path, an awkward business edge, and an illegal or disallowed action when relevant. Keep illegal-action behavior observable: either explain why the control is disabled or allow a safe attempt and show its rejection without mutating the model incorrectly. Record action history when order is part of the uncertainty.

Keep everything inline for the shareable-file branch: HTML, CSS, JavaScript, and required sample data. The reviewer should be able to reopen it offline. If the question genuinely requires a project runtime, state why and provide its actual one-command startup instead of claiming a double-click artifact.

## Check and collect feedback

Open the artifact and execute the scenarios. Verify reset determinism, action ordering, visible state, legal/illegal transitions, and completion behavior. Record the initial inputs, operations, and observed outcomes against the artifact version. Lightweight manual scenario checks are normally sufficient; add automation only when needed to resolve this experiment's question reliably.

Present the file/start command and ask for the concrete model choice when approval is required. Capture statements such as “this should be impossible” as feedback to investigate against the effective domain rules. Distinguish actual observations, hypothetical examples, and accepted changes. A prototype can reveal that the proposed model fails; that is a valid experiment result if the evidence answers the question.

## Handoff

Retain the artifact, scenarios, observations, and decision as accessible task material. A validated reducer or model can inform implementation after approval; its production use still needs normal error handling, relevant tests, and architecture checks. Keep the exploratory HTML shell out of production behavior unless the task explicitly makes it a product requirement.

Completion requires a runnable artifact, recorded relevant observations, an explicit answer or decision dependency, and applicable approval. A file that was never exercised is an unverified draft.

Adapted from Matt Pocock's `prototype/LOGIC.md`; see [source and license](upstream.md).
