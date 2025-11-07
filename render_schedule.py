#!/usr/bin/env python3
"""
On-call schedule renderer with override support.

Uses an event-sweep algorithm to efficiently compute the final schedule
by processing temporal boundaries in chronological order.
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class EventType(Enum):
    """Event types ordered by processing priority at the same timestamp."""
    OVERRIDE_END = 1
    OVERRIDE_START = 2
    HANDOVER = 3


@dataclass
class Event:
    """A temporal boundary in the schedule."""
    time: datetime
    event_type: EventType
    user: Optional[str] = None
    
    def __lt__(self, other):
        """Sort by time, then by event type priority."""
        if self.time != other.time:
            return self.time < other.time
        return self.event_type.value < other.event_type.value


def parse_timestamp(ts: str) -> datetime:
    """Parse ISO 8601 timestamp to datetime object."""
    return datetime.fromisoformat(ts.replace('Z', '+00:00'))


def get_base_user(schedule: Dict[str, Any], time: datetime) -> str:
    """
    Calculate which user should be on-call at a given time based on rotation.
    
    Handles times before schedule start by projecting the rotation backwards.
    """
    users = schedule['users']
    handover_start = parse_timestamp(schedule['handover_start_at'])
    interval_seconds = schedule['handover_interval_days'] * 24 * 3600
    
    # Calculate seconds elapsed since handover_start (can be negative)
    delta_seconds = (time - handover_start).total_seconds()
    
    # Determine which rotation period we're in
    rotation_index = int(delta_seconds // interval_seconds)
    
    # Map to user index (handles negative indices correctly)
    user_index = rotation_index % len(users)
    
    return users[user_index]


def collect_override_events(overrides: List[Dict[str, Any]], 
                            from_time: datetime, 
                            until_time: datetime) -> List[Event]:
    """
    Collect all temporal events from overrides that intersect the query window.
    
    Returns list of events (not sorted here; sorted later).
    """
    events = []
    
    for override in overrides:
        start = parse_timestamp(override['start_at'])
        end = parse_timestamp(override['end_at'])
        
        # Only include overrides that intersect our query window
        if end > from_time and start < until_time:
            if start >= from_time:
                events.append(Event(start, EventType.OVERRIDE_START, override['user']))
            if end <= until_time:
                events.append(Event(end, EventType.OVERRIDE_END, override['user']))
    
    return events


def collect_handover_events(schedule: Dict[str, Any], 
                            from_time: datetime, 
                            until_time: datetime) -> List[Event]:
    """
    Collect handover events within the query window.
    """
    users = schedule['users']
    if not users:
        return []
    
    handover_start = parse_timestamp(schedule['handover_start_at'])
    interval_delta = timedelta(days=schedule['handover_interval_days'])
    
    # Calculate the start of the shift covering from_time
    delta_seconds = (from_time - handover_start).total_seconds()
    interval_seconds = schedule['handover_interval_days'] * 86400
    rotation_index = int(delta_seconds // interval_seconds)
    current_shift_start = handover_start + rotation_index * interval_delta
    
    handovers = []
    next_handover = current_shift_start + interval_delta
    while next_handover < until_time:
        if next_handover >= from_time:
            handovers.append(Event(next_handover, EventType.HANDOVER))
        next_handover += interval_delta
    
    return handovers


def render_schedule(schedule: Dict[str, Any],
                    overrides: List[Dict[str, Any]],
                    from_time: datetime,
                    until_time: datetime) -> List[Dict[str, Any]]:
    """
    Render the final schedule by processing events chronologically.
    
    Algorithm:
    1. Collect override and handover boundary events.
    2. Initialize stack with active overrides at from_time.
    3. Sweep through timeline from start to end.
    4. Track active overrides in a stack (most recent = active).
    5. Emit entry for each segment between events.
    6. Merge consecutive entries with same user.
    
    Time complexity: O((n + m) log (n + m)) where n is overrides, m is handovers (typically small).
    Space complexity: O(n + m) for events and output.
    """
    if from_time >= until_time:
        return []

    if not schedule.get('users'):
        raise ValueError("Schedule must contain at least one user")
    
    override_events = collect_override_events(overrides, from_time, until_time)
    handover_events = collect_handover_events(schedule, from_time, until_time)
    events = override_events + handover_events
    events.sort()
    
    # Initialize stack with overrides active at from_time (sorted by start time for precedence)
    active_overrides = []
    for override in overrides:
        start = parse_timestamp(override['start_at'])
        end = parse_timestamp(override['end_at'])
        if start < from_time and end > from_time:
            active_overrides.append((start, override['user']))
    active_overrides.sort(key=lambda x: x[0])  # Oldest first
    override_stack = [user for _, user in active_overrides]
    
    entries = []
    current_time = from_time
    current_user = override_stack[-1] if override_stack else get_base_user(schedule, current_time)
    
    for event in events:
        # Emit the segment before this event if there's duration
        if current_time < event.time:
            entries.append({
                'user': current_user,
                'start_at': current_time.isoformat().replace('+00:00', 'Z'),
                'end_at': event.time.isoformat().replace('+00:00', 'Z')
            })
        
        # Process the event
        if event.event_type == EventType.OVERRIDE_START:
            override_stack.append(event.user)
        elif event.event_type == EventType.OVERRIDE_END:
            if override_stack and override_stack[-1] == event.user:
                override_stack.pop()
        elif event.event_type == EventType.HANDOVER:
            pass  # Base user will update automatically
        
        # Update current user and time
        current_time = event.time
        current_user = override_stack[-1] if override_stack else get_base_user(schedule, current_time)
    
    # Emit the final segment if remaining
    if current_time < until_time:
        entries.append({
            'user': current_user,
            'start_at': current_time.isoformat().replace('+00:00', 'Z'),
            'end_at': until_time.isoformat().replace('+00:00', 'Z')
        })
    
    return merge_consecutive_entries(entries)


def merge_consecutive_entries(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Merge consecutive entries with the same user.
    """
    if not entries:
        return []
    
    merged = [entries[0]]
    
    for entry in entries[1:]:
        prev = merged[-1]
        if prev['user'] == entry['user'] and prev['end_at'] == entry['start_at']:
            prev['end_at'] = entry['end_at']
        else:
            merged.append(entry)
    
    return merged


def main():
    parser = argparse.ArgumentParser(
        description='Render on-call schedule with overrides'
    )
    parser.add_argument('--schedule', required=True,
                        help='Path to schedule JSON file')
    parser.add_argument('--overrides', required=True,
                        help='Path to overrides JSON file')
    parser.add_argument('--from', dest='from_time', required=True,
                        help='Start time (ISO 8601 format)')
    parser.add_argument('--until', required=True,
                        help='End time (ISO 8601 format)')
    
    args = parser.parse_args()
    
    try:
        with open(args.schedule, 'r') as f:
            schedule = json.load(f)
        
        with open(args.overrides, 'r') as f:
            overrides = json.load(f)
        
        # Validate inputs
        if not schedule.get('users'):
            raise ValueError("Schedule must contain at least one user")
        if not isinstance(overrides, list):
            raise ValueError("Overrides must be an array")
        
        from_time = parse_timestamp(args.from_time)
        until_time = parse_timestamp(args.until)
        
        if from_time >= until_time:
            raise ValueError("'from' time must be before 'until' time")
        
        entries = render_schedule(schedule, overrides, from_time, until_time)
        print(json.dumps(entries, indent=2))
        
    except FileNotFoundError as e:
        print(f"Error: Could not find file: {e.filename}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in input file: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyError as e:
        print(f"Error: Missing required field in input: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()