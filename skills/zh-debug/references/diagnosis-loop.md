# Symptom-Specific Diagnosis Loop

Read this reference when creating the feedback loop. Return to the relevant branch when the signal is weak or an experiment stops producing information.

## Choose a runnable signal

Try the smallest boundary that still exercises the symptom:

| Available boundary | Useful feedback |
| --- | --- |
| Public operation or service interface | A failing behavioral test with controlled fixtures |
| Running development service | A repeatable HTTP request with an assertion on the response |
| Command-line operation | Fixed input and a comparison with an independently expected result |
| Browser interaction | A repeatable user path with DOM, network, or visible-result assertions |
| Captured traffic or events | A redacted replay that retains the conditions causing the failure |
| Complex startup path | A minimal harness retaining the load-bearing services and dependencies |
| Version-dependent failure | Bisection or old-versus-new execution with the same symptom check |

Run the loop and capture its actual result before treating it as diagnostic evidence. It must fail on the specific symptom and be capable of passing when that symptom is corrected. A server that merely starts or a command that merely exits successfully may miss the defect.

Make setup reusable, inputs controlled, and feedback as fast and unattended as practical. Speed is a design goal; a genuinely slow integration boundary remains usable when its cost and signal are clear.

## Human-only reproduction

When the necessary action cannot be automated, adapt [the human reproduction template](../assets/human-reproduction.template.sh) into the assigned task's run location. Set its instructions to the actual path and symptom, inspect it, and run it in an interactive terminal accessible to the human. The template records observations; it does not automatically assert a fix or poll forever.

Keep sign-in, secret entry, and privileged confirmations in the application's own interface. Ask for redacted observations only. If the host cannot provide an interactive terminal, present the same bounded steps through its supported interaction channel and retain the resulting observations. This branch ends when that one attempt is recorded, then the agent evaluates the next experiment.

## Intermittent defects

Record input seeds, triggering conditions, attempt counts, failure counts, and the exact failure signature. Increase reproduction frequency using controlled concurrency, load, scheduling, or replay, without changing the defect being investigated. Choose sample size and runtime from observed frequency and actual limits. Compare before and after under equivalent conditions; an unexplained non-reproduction is an observation requiring interpretation.

## Performance defects

Record the relevant workload, data volume, environment, warmup and cache conditions, timing distribution, and acceptance threshold. Profile, inspect query plans, or bisect the suspected interval before optimizing. Change one factor and rerun the same workload. Keep functional and data-correctness checks alongside performance measurements.

## Hypotheses and probes

Keep a short ranked set of plausible alternatives rather than anchoring on the first idea. For each, state: suspected cause, predicted observation, experiment, actual result, and next inference. Prefer probes that distinguish alternatives. Mark temporary instrumentation with a unique task-specific token so it can be located and removed precisely.

When no reproduction is available, use existing artifacts to define missing conditions and candidate experiments. Label untested explanations as hypotheses. Report the attempted routes and the specific missing input; preserve recovery material and continue investigations that do not depend on it.

Method source: Matt Pocock's selected diagnosis skill and human-loop template, version 1.3.2. The stage entry retains the upstream license notice.
