# Architecture

> Write this yourself. Do not paste a generated version — the value of this
> file is that you can reproduce the diagram on a whiteboard from memory.

## Context
What the product is, who it's for, what it must not do.

## Services
| Service | Responsibility | Scales on | Fails how |
|---|---|---|---|
| api | | | |
| inference | | | |
| ingestion | | | |
| orchestrator | | | |

## Data flow
1. Article enters the system →
2. A user opens the feed →
3. A click is recorded →
4. A training round runs →

## Why it is split this way
One paragraph per boundary. Each paragraph must answer: what would break if
these two services were one?

## Degraded modes
What still works when each service is down?
