# Domain documentation

Render links for the observed layout. For one domain, link the actual glossary and ADR directory. For several domains, link the root map, each glossary it selects, and shared and context-specific ADR directories. State the owned paths or topics for each context. Preserve active legacy names.

List canonical Git sources. If an optional glossary or ADR directory is absent, give its intended location and add the file when the first term or decision is confirmed. Keep definitions in the glossary and version-specific decisions in the accepted ADR.

Before intake or design, use the affected paths or topic to select the relevant glossary from the map when present. Read the relevant context and shared ADRs at the target revision. Use the glossary terms in ticket titles and bodies, specs, tests and review. Cite any conflicting ADR clause and take the proposed change to the decision owner.

List the engineering standards that actually apply, including scoped instruction files and contribution guides. Read the original clause with `git show <revision>:<path>` and cite its path, section and revision. When a source moved or a knowledge reference is stale, follow the rendered project knowledge guide or use `git log --follow -- <path>` and confirmed tracker decisions to recover the clause effective for the scenario and release. Record its source and any superseding decision on the original ticket.
