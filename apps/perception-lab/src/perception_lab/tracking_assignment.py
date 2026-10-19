"""Bounded rectangular minimum-cost assignment with explicit unmatched columns."""

import math


def assign(costs: list[list[float]], unmatched_cost: float) -> tuple[tuple[int, int], ...]:
    """Shortest augmenting paths, deterministic ascending-column tie break.

    Each row can choose its own dummy column. Forbidden edges use infinity;
    costs at/above unmatched_cost are not eligible. Offline evaluation permits
    512x512; runtime configuration separately caps matrices at 128x256.
    """
    n = len(costs)
    if not n:
        return ()
    m = len(costs[0])
    if n > 512 or m > 512 or any(len(row) != m for row in costs):
        raise ValueError("Assignment dimensions exceed bounds")
    if not math.isfinite(unmatched_cost) or unmatched_cost <= 0:
        raise ValueError("Invalid unmatched cost")
    if any(math.isnan(c) or c < 0 for row in costs for c in row):
        raise ValueError("Invalid association cost")
    a = [[min(c, unmatched_cost + 1) for c in row] + [unmatched_cost] * n for row in costs]
    columns = m + n
    u, v = [0.0] * (n + 1), [0.0] * (columns + 1)
    owner, way = [0] * (columns + 1), [0] * (columns + 1)
    for i in range(1, n + 1):
        owner[0] = i
        j0 = 0
        minimum = [math.inf] * (columns + 1)
        used = [False] * (columns + 1)
        while True:
            used[j0] = True
            i0, delta, j1 = owner[j0], math.inf, 0
            for j in range(1, columns + 1):
                if not used[j]:
                    cur = a[i0 - 1][j - 1] - u[i0] - v[j]
                    if cur < minimum[j]:
                        minimum[j], way[j] = cur, j0
                    if minimum[j] < delta:
                        delta, j1 = minimum[j], j
            for j in range(columns + 1):
                if used[j]:
                    u[owner[j]] += delta
                    v[j] -= delta
                else:
                    minimum[j] -= delta
            j0 = j1
            if owner[j0] == 0:
                break
        while j0:
            j1 = way[j0]
            owner[j0] = owner[j1]
            j0 = j1
    return tuple(
        sorted(
            (owner[j] - 1, j - 1)
            for j in range(1, m + 1)
            if owner[j] and costs[owner[j] - 1][j - 1] < unmatched_cost
        )
    )
