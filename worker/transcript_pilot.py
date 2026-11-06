from __future__ import annotations

from typing import Any


def select_sample(connection, sample_size: int) -> list[dict[str, Any]]:
    """Select a deterministic, age-spread sample for the future transcript pilot."""
    rows = connection.execute(
        "SELECT video_id, title, published_at, duration_seconds FROM videos "
        "ORDER BY published_at ASC, video_id ASC"
    ).fetchall()
    if not rows or sample_size <= 0:
        return []
    if sample_size >= len(rows):
        return [dict(row) for row in rows]
    indexes = {round(i * (len(rows) - 1) / (sample_size - 1)) for i in range(sample_size)} if sample_size > 1 else {len(rows) // 2}
    return [dict(rows[index]) for index in sorted(indexes)]
