"""Loop auto-assignment: assigns rooms to path_a / path_b for a given level."""
from __future__ import annotations

from collections import defaultdict, deque
from typing import NamedTuple

from dungeon_daddy.data.models import Level

_STAIR_TYPES = {"stair_up", "stair_down"}


class LoopAssignment(NamedTuple):
    entry: str
    goal: str
    path_a: list[str]
    path_b: list[str]


def auto_assign_loop_rooms(level: Level) -> LoopAssignment:
    """
    BFS-based assignment of rooms to path_a / path_b for a level.

    Algorithm (from spec F-16b):
    1. Build adjacency list, excluding stair connections.
    2. Entry = room with most connections; tie → lowest num.
    3. Goal  = BFS-furthest room from entry; tie → lowest num.
    4. path_a = shortest path entry → goal.
    5. path_b = alternate path with fewest overlapping intermediate rooms;
       tie → shortest; tie → first found. Degrades to path_a when no alternate.
    """
    adj = _build_adjacency(level)
    rooms = level.rooms

    conn_count = {r.id: len(adj.get(r.id, [])) for r in rooms}

    max_conns = max(conn_count.values(), default=0)
    entry = min(
        (r for r in rooms if conn_count[r.id] == max_conns),
        key=lambda r: r.num,
    ).id

    dist = _bfs_distances(adj, entry)
    max_dist = max(dist.values(), default=0)
    goal = min(
        (r for r in rooms if dist.get(r.id, 0) == max_dist),
        key=lambda r: r.num,
    ).id

    path_a = _shortest_path(adj, entry, goal)

    path_a_intermediates = set(path_a[1:-1])
    all_paths = _all_simple_paths(adj, entry, goal)
    alternates = [p for p in all_paths if p != path_a]

    if not alternates:
        path_b = path_a
    else:
        alternates.sort(key=lambda p: (len(set(p[1:-1]) & path_a_intermediates), len(p)))
        path_b = alternates[0]

    return LoopAssignment(entry=entry, goal=goal, path_a=path_a, path_b=path_b)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _build_adjacency(level: Level) -> dict[str, list[str]]:
    adj: dict[str, list[str]] = defaultdict(list)
    for conn in level.connections:
        if conn.type in _STAIR_TYPES:
            continue
        adj[conn.from_room].append(conn.to_room)
        adj[conn.to_room].append(conn.from_room)
    return dict(adj)


def _bfs_distances(adj: dict[str, list[str]], start: str) -> dict[str, int]:
    dist = {start: 0}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for neighbor in adj.get(node, []):
            if neighbor not in dist:
                dist[neighbor] = dist[node] + 1
                queue.append(neighbor)
    return dist


def _shortest_path(adj: dict[str, list[str]], start: str, end: str) -> list[str]:
    if start == end:
        return [start]
    parent: dict[str, str] = {}
    visited = {start}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for neighbor in adj.get(node, []):
            if neighbor in visited:
                continue
            visited.add(neighbor)
            parent[neighbor] = node
            if neighbor == end:
                path, cur = [], end
                while cur != start:
                    path.append(cur)
                    cur = parent[cur]
                path.append(start)
                return list(reversed(path))
            queue.append(neighbor)
    return []


def _all_simple_paths(adj: dict[str, list[str]], start: str, end: str) -> list[list[str]]:
    paths: list[list[str]] = []
    stack = [(start, [start])]
    while stack:
        node, path = stack.pop()
        for neighbor in adj.get(node, []):
            if neighbor == end:
                paths.append(path + [end])
            elif neighbor not in path:
                stack.append((neighbor, path + [neighbor]))
    return paths
