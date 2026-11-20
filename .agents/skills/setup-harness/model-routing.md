# Configure project model routing

## Agree on the table

1. Match three difficulty levels to the project's work. Start with a local change and clear checks for `simple`, one business flow touching several places for `regular`, and a cross-module contract, historical data migration, or concurrent consistency for `complex`. Record one project example accepted by the user for each level. Classify the work assigned to each stage, so a regular implementation can have a complex review.
2. List exact models and supported reasoning efforts using the current client's model catalog and dispatch tool capabilities. Use the target runtime's supported pairs when setup runs elsewhere. Treat a catalog entry as a configurable choice and an actual dispatch as execution evidence. Agree on a default pair for each difficulty, then review each row below for exceptions. Retain the user's existing confirmed choices.
3. Preview the examples, defaults, role exceptions and the fully resolved table together. Obtain one approval for that preview with the rest of setup. An existing approval for the same values is sufficient. Apply only approved values. On refresh, preserve the existing examples and cells, fill missing values from confirmed choices, and confirm any unresolved choices before filling those cells. An identical rerun leaves files byte-identical.

## Save the resolved configuration

Use the project's language for prose, keeping the role and difficulty IDs below. Each `model / reasoning_effort` cell holds two exact values as code spans, separated by ` / `. Present the three default pairs in the preview and materialize them in every role cell that uses the default. Save the fully resolved table and the three confirmed examples in `docs/agents/model-routing.md`. The runtime reads the role cell directly. The table below shows the shape with placeholders for the preview only.

| Difficulty | Confirmed example |
| --- | --- |
| `simple` | Project example |
| `regular` | Project example |
| `complex` | Project example |

| Role | `simple` | `regular` | `complex` |
| --- | --- | --- | --- |
| `plan-feature` | `model` / `reasoning_effort` | `model` / `reasoning_effort` | `model` / `reasoning_effort` |
| `implement-ticket` | `model` / `reasoning_effort` | `model` / `reasoning_effort` | `model` / `reasoning_effort` |
| `implementation-slice` | `model` / `reasoning_effort` | `model` / `reasoning_effort` | `model` / `reasoning_effort` |
| `accept-delivery` | `model` / `reasoning_effort` | `model` / `reasoning_effort` | `model` / `reasoning_effort` |
| `Standards` | `model` / `reasoning_effort` | `model` / `reasoning_effort` | `model` / `reasoning_effort` |
| `Spec` | `model` / `reasoning_effort` | `model` / `reasoning_effort` | `model` / `reasoning_effort` |
| `setup-harness` | `model` / `reasoning_effort` | `model` / `reasoning_effort` | `model` / `reasoning_effort` |
