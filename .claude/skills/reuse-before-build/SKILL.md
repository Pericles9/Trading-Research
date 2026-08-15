---
name: reuse-before-build
description: Use this before starting implementation of any new feature, service, or subsystem — not small helper functions or one-off glue code, but anything that amounts to a real chunk of infrastructure (auth, parsing, queuing, caching, rate limiting, scheduling, file format handling, protocol clients, data validation, state machines, and similar "solved problem" territory). Before writing the first line of that kind of component, stop and check whether a maintained library or open-source project already does it well enough to use or adapt. Trigger this even when the user doesn't explicitly ask "is there a library for this" — the default posture is to look first, build second, and only build from scratch once looking has actually ruled out reuse.
---

# Reuse Before Build

## Why this matters

Time spent rebuilding infrastructure that already exists, tested, and hardened elsewhere is time not spent on the part of the project that's actually novel. Mature libraries for things like auth, parsing, rate limiting, and scheduling have usually already hit and fixed the edge cases a first-pass custom version won't think of.

The flip side: window-shopping libraries for every small function wastes time in the other direction. This skill is about catching the moments that deserve the look — not turning every function into a research project.

## When to pause and check

**Check first for:** a new module, service, or subsystem — the kind of thing where you're about to define a new boundary in the codebase, not just add a function inside an existing one. If the task description sounds like "build a thing that does X" and X is a category of problem (auth, a job queue, a rate limiter, a parser for some format, a scheduler, a caching layer, a protocol client), that's the trigger, whether or not the user used the word "library."

**Skip the check for:** small helper functions, one-off scripts, glue code, and business logic that's inherently specific to this codebase (nobody has published a library for "the way this particular app maps orders to invoices"). If reusing something would need so much adaptation that little of the original would survive, that's also a sign this isn't really a reuse candidate — note that quickly and move on rather than forcing the search.

Rule of thumb: if what you're about to write has a name a stranger would recognize out of context ("rate limiter," "CSV parser," "job scheduler"), check. If it only makes sense described in terms of this specific codebase, just build it.

## How to check

1. **Search before writing.** Look at the package registry relevant to the language in play (PyPI, npm, crates.io, Go modules, etc.) and GitHub, for what already exists.
2. **Read enough to know if it actually fits.** Does it solve the specific problem, or something adjacent that would need heavy reshaping?
3. **Weigh it with judgment, not a checklist.** Worth asking:
   - Is it actively maintained — recent commits or releases, issues getting responses?
   - Is the license compatible with how this code will be used?
   - Does adopting it cost more than it saves — heavy dependency tree, awkward API, doesn't fit the existing architecture?
   - Are there real signals of trust (adoption, notable users, a track record), or does it look abandoned or thin?
   - If it touches credentials, untrusted input, or the network, does it look like anyone has looked at it from a security angle?
4. **Decide, and be able to say why.** Use it as-is, use it with adaptation, vendor or fork a relevant piece, or build custom. Building custom is a fine outcome — it just needs to be the outcome of having looked, not the default from skipping the look.

## What not to do

- Don't turn a small function into a dependency-evaluation project — this is for feature/subsystem-scale decisions, not every line of code.
- Don't reach for a library that's clearly heavier or worse than the direct implementation just because it exists.
- Don't skip the check because building it yourself sounds more familiar or more interesting than researching options — make the call from what's actually out there, not from a hunch.

## Recording the decision

When the call is to build instead of reuse, say why in a sentence or two — in a commit message, a code comment, or the response to the user. That's enough to keep the decision visible instead of quietly defaulting to custom code every time without a record of what was ruled out.