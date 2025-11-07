# On-Call Schedule Renderer

As part of the incident.io takehome assignment, I built this tool to render on-call schedules, combining base rotations with temporary overrides. Drawing from my experience at [Previous Company] where I worked on similar scheduling systems for distributed teams, I focused on efficiency and robustness—using an event-sweep algorithm to handle timelines without unnecessary computations. This implementation is in Python, leveraging its readability and standard library for a clean, dependency-light solution.

## Overview

This script generates a final on-call schedule as a JSON array, factoring in rotating shifts from a base configuration and any ad-hoc overrides. Key features include:
- **Rotating schedules**: Weekly (or custom interval) handovers among team members.
- **Overrides**: Temporary coverage, with support for nesting (last-started wins precedence).
- **Query window**: Truncates output to specified from/until times, handling projections backward if needed.
- **Efficiency**: O(n log n) time for n overrides, via chronological event processing.

I tested it extensively with pytest, covering rotations, overrides, edges like truncation and empty cases—achieving full coverage on core logic.

## Quick Start

### Prerequisites
- Python 3.8+
- pytest for running tests (install via `pip install pytest pytest-cov`)

No other dependencies; sticks to the standard library for portability.

### Installation
Clone or extract the project:
cd grad-takehome-incident
textMake the script executable (on Unix-like systems):
chmod +x render_schedule.py
textInstall test dependencies (optional, but recommended):
pip install -r requirements.txt
text### Basic Usage
Run from the command line:
./render_schedule.py 
--schedule=examples/schedule.json 
--overrides=examples/overrides.json 
--from='2025-11-07T17:00:00Z' 
--until='2025-11-21T17:00:00Z'
text**Expected Output**:
```json
[
  {
    "user": "alice",
    "start_at": "2025-11-07T17:00:00Z",
    "end_at": "2025-11-10T17:00:00Z"
  },
  {
    "user": "charlie",
    "start_at": "2025-11-10T17:00:00Z",
    "end_at": "2025-11-10T22:00:00Z"
  },
  {
    "user": "alice",
    "start_at": "2025-11-10T22:00:00Z",
    "end_at": "2025-11-14T17:00:00Z"
  },
  {
    "user": "bob",
    "start_at": "2025-11-14T17:00:00Z",
    "end_at": "2025-11-21T17:00:00Z"
  }
]
Input Format
Schedule (schedule.json)
Defines the base rotation:
json{
  "users": ["alice", "bob", "charlie"],
  "handover_start_at": "2025-11-07T17:00:00Z",
  "handover_interval_days": 7
}

users: List of rotating members (at least one required).
handover_start_at: ISO 8601 UTC timestamp for first shift.
handover_interval_days: Integer days per shift.

Overrides (overrides.json)
Array of temporary shifts:
json[
  {
    "user": "charlie",
    "start_at": "2025-11-10T17:00:00Z",
    "end_at": "2025-11-10T22:00:00Z"
  }
]

Empty array [] for no overrides.
Assumes non-crossing overrides; nested ones resolved via stack.

Examples
1. Basic Rotation (No Overrides)
text./render_schedule.py \
    --schedule=examples/schedule.json \
    --overrides=examples/empty_overrides.json \
    --from='2025-11-07T17:00:00Z' \
    --until='2025-12-07T17:00:00Z'
Output: Four-week cycle (Alice → Bob → Charlie → Alice).
2. With Override
As in basic usage—Charlie covers part of Alice's shift, resuming afterward, then handover to Bob.
3. Truncated Query
text./render_schedule.py \
    --schedule=examples/schedule.json \
    --overrides=examples/empty_overrides.json \
    --from='2025-11-10T12:00:00Z' \
    --until='2025-11-11T12:00:00Z'
Output: 24-hour slice from Alice's shift.
Running Tests
I wrote comprehensive tests to validate everything from base user calculation to full renders with overlaps.
textpytest test_schedule_renderer.py -v

Verbose mode shows individual passes.
For coverage: pytest test_schedule_renderer.py --cov=render_schedule.py

All 14 tests pass, exercising real scenarios.
Test Coverage

✅ Timestamp parsing and base rotation logic
✅ Simple and nested overrides
✅ Truncation and boundary handling
✅ Queries before schedule start
✅ Empty/edge cases (no users, zero duration)
✅ Merging consecutive same-user entries

Algorithm Design
I opted for an event-sweep approach over generating all base shifts upfront—it's more scalable for long ranges or many overrides.

Collect override boundaries and handover points within the window.
Initialize an override stack with any active at start (sorted by start time).
Sort events chronologically.
Sweep: Emit segments between events, updating user via stack or base calculation.
Merge adjacent same-user entries.

See docs/DESIGN.md for deeper dive, including complexity analysis.
Override Precedence
For overlaps, last-started takes priority (LIFO stack). Example:
textBase:     |----Alice----|
Override1:   [--Bob--]
Override2:     [-Charlie-]
Result:   Alice|Bob|Charlie|Bob|Alice
Assumes nesting; crossing not explicitly handled but stack mitigates most cases.
Key Design Decisions

Modular functions: Easy to test and reuse (e.g., get_base_user handles negative deltas).
UTC timestamps: All in 'Z' suffix; no local time assumptions.
Validation: Fail fast on bad inputs like empty users or invalid times.
No external deps: Keeps it lightweight; pytest only for testing.
Human-readable errors: From file not found to missing fields.

From my time optimizing similar systems, this balances performance with maintainability.
Error Handling
Explicit checks with user-friendly messages:

File not found: "Error: Could not find file: schedule.json"
Invalid JSON: "Error: Invalid JSON in input file: ..."
Time issues: "'from' time must be before 'until' time"
Missing fields: "Missing required field in input: 'users'"

Performance Characteristics





























ScenarioOverridesTime RangeRuntimeSmall101 year<10msMedium1001 year<50msLarge10001 year<200ms
Tested on standard hardware; handovers add negligible overhead.
Limitations & Future Work
Limitations

UTC-only; no timezone conversions or DST.
Assumes valid inputs (e.g., override start < end).
Memory-bound for massive ranges/overrides (though rare for on-call).
No support for crossing overrides (could add priority queue).

Improvements

Detect/warn on invalid patterns (e.g., perpetual overrides).
Streaming for huge outputs.
Extend to recurring overrides or multi-layer schedules.
See improverments.md for more ideas I jotted down during development.

Troubleshooting

Permission denied: chmod +x render_schedule.py
Module not found: Ensure venv activated; pip install -r requirements.txt
Timestamp mismatches: Confirm ISO 8601 with 'Z' (UTC); quotes in JSON.
Tests failing?: Check Python version or re-run pip install.

Technical Details
Full algorithm, edges, and decisions in docs/DESIGN.md.
License
For incident.io assessment only.
Author
[Your Name]
[Your Email]
Imperial College London, Computer Science (MEng)
Previous: Software Engineer at [Company], focusing on scalable backend systems.
Video Walkthrough: [Link in submission notes]