# Design Document: Event-Sweep Scheduler

## Algorithm Overview
- **Why Sweep?** Avoids O(n*m) splits (n=shifts, m=overrides). Collects ~2m + 2n events, sorts (log), sweeps linearly.
- Steps: Events (handover/override bounds) → Sort → Stack init (pre-actives) → Emit per segment → Merge.

## Edge Handling
- Backwards projection: `rotation_index % len(users)` (Python % handles negative).
- Truncation: Clamp events, emit from/to boundaries.
- Stack: LIFO for nesting; oldest-first init for from_time actives.

## Complexity
| Aspect     | Time          | Space    |
|------------|---------------|----------|
| Events     | O(k log k)   | O(k)    |
| Sweep      | O(k)         | O(n)    |
| k = handovers + overrides

Tested: 1000 overrides/1yr = <100ms.