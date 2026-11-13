# Domain glossary format

Read this when creating or changing canonical business terms. This format is self-contained; the project's established authoritative glossary location and format take precedence where they express the same meaning.

## Locate the relevant context

Follow the existing domain index or context map. A root `GLOSSARY-MAP.md`, if present, may identify context-specific glossaries; an existing root `GLOSSARY.md` may already be authoritative. Do not create a competing glossary under a new directory. Without an existing convention, start a glossary under `docs/domain/` when the first term is resolved, and link it from the project knowledge entry.

Use one context when the concepts form one coherent language. Use multiple contexts when the same word has genuinely different business meanings or ownership. A context map records each glossary's location and a short description of relevant relationships and translations. Create it only when those distinctions are needed.

## Entry shape

```markdown
# Ordering context

Receives and tracks purchase commitments from customers.

## Language

**Order**: A customer's commitment to purchase a specified set of items under agreed terms.
Avoid: purchase record, transaction.

**Customer**: The person or organization that places an order in this context.
Avoid: login account, operator.
```

Choose one canonical name for one concept within the context. List confusing synonyms or overloaded names only when that prevents a real misunderstanding. Keep definitions to one or two precise sentences about what the concept is; group related terms when useful.

## Keep the glossary focused

Include project-specific business concepts. Keep technical patterns, class layouts, SQL columns, migration scripts, checklists, speculative notes, and implementation decisions in their appropriate sources. Lifecycle rules, permissions, and relationship constraints can live in the domain model or specification with links from the task; the glossary is not a substitute for them.

When code and intended meaning disagree, record the code observation separately, resolve the target meaning through the applicable decision boundary, and write the confirmed term here. Unresolved proposals remain in task notes. Write a resolved definition promptly within the authorized documentation scope; otherwise return the proposed entry and destination to its owner.

## Context map example

```markdown
# Domain contexts

- Ordering — glossary location: `ordering/glossary.md`; owns order commitments and order lifecycle.
- Billing — glossary location: `billing/glossary.md`; owns payment obligations and settlement records.

## Relationships

- Ordering sends accepted order references to Billing.
- A Billing payer can differ from the Ordering customer; translation uses explicit identities.
```

The map expresses business responsibility and translation. Use architecture sources for transport protocols and implementation types.

## Completion check

A glossary update is ready when each new term belongs to a named context, has one precise meaning, agrees with the effective decision, and can be found through the existing knowledge entry. Conflicting uses are resolved or explicitly pending; no competing authoritative definition is introduced.

Method adapted from Matt Pocock's `domain-modeling/GLOSSARY-FORMAT.md`; see [source and license](upstream.md).
