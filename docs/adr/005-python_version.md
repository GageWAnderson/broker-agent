# ADR 005: Python Version

## Status
Accepted

## Context
What version of Python should we use?

## Decision
Use python 3.13 for future proofing and new features - greenfield development enables us to use the latest version.

## Consequences
- Positive:
	•	Performance improvements:
CPython 3.13 has made the interpreter even faster (continuing work from 3.11 and 3.12). Benchmarks show ~5–10% speedups over 3.12 depending on the workload.
	•	New language features:
	•	New syntax and typing improvements (more gradual typing, enhanced type inference, etc.)
	•	Possible small QoL features for standard library (improvements in asyncio, dataclasses, math, etc.)
	•	More deprecations completed:
Stuff that’s been “warned” about for a while in 3.11/3.12 might finally be removed, cleaning up old behavior.
	•	Better debugging tools:
Built-in support for improved debugging hooks, error messages, profiling (Python has been actively improving error tracebacks recently).
- Negative: 
	•	Pre-release instability (for now):
Until October 2025, 3.13 is not considered “production ready.” Some libraries (especially C-extension based ones like NumPy, PyTorch) may not yet fully support it.
	•	Third-party library compatibility:
Even after full release, some packages lag behind in adding 3.13 support. If you heavily rely on specific packages (especially for machine learning, data science, or niche APIs), you might encounter issues.
	•	Minor learning curve:
Some deprecated behavior may now break outright. If your code used old quirks, you might need small rewrites.
	•	Environment management overhead:
If you’re managing multiple versions (say 3.9/3.10 for old projects and now 3.13 for new ones), you’ll need virtualenv/pyenv/docker to not go crazy.
- Risk: 

## Date
2025-04-27