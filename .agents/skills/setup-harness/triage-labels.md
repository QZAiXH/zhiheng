# Triage labels

Map the five upstream roles to the labels this project actually uses. Preserve existing names when the roles match.

| Role | Project label | Meaning |
| --- | --- | --- |
| `needs-triage` | `needs-triage` | A maintainer needs to evaluate the issue. |
| `needs-info` | `needs-info` | The reporter needs to supply more information. |
| `ready-for-agent` | `ready-for-agent` | The acceptance criteria are sufficient for an agent to start. |
| `ready-for-human` | `ready-for-human` | The task calls for human implementation. |
| `wontfix` | `wontfix` | The maintainer has decided to close the request without implementation. |

Use the mapped strings for remote issue labels or the local `Status:` value when triaging. Local tickets keep their `## Comments` history.
