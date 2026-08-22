from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, get_args


SnapType = Literal[
    "recommendation",
    "attention",
    "warning",
    "opportunity",
]

SnapPriority = Literal[
    "low",
    "medium",
    "high",
    "critical",
]

SnapDomain = Literal[
    "growth",
    "operations",
    "finances",
    "revenue",
    "sales",
    "marketing",
    "customers",
    "product",
    "people",
    "others"
]


@dataclass(
    slots=True,
    frozen=True,
)
class SnapModel:

    type: SnapType

    priority: SnapPriority

    confidence: float

    title: str

    message: str

    why_it_matters: str

    action: str

    domain: SnapDomain


SnapStatus = Literal[
    "active",
    "pending",
    "completed",
]


SnapTab = Literal[
    "attention",
    "recommendation",
    "priority",
]


@dataclass(
    slots=True,
    frozen=True,
)
class SnapRecord:

    snap_id: str

    business_id: str

    snap: SnapModel

    status: SnapStatus = "active"

    created_at: str | None = None


SNAP_TYPES: tuple[SnapType, ...] = get_args(
    SnapType,
)

SNAP_STATUSES: tuple[SnapStatus, ...] = get_args(
    SnapStatus,
)

SNAP_TABS: tuple[SnapTab, ...] = get_args(
    SnapTab,
)

_PRIORITY_RANK: dict[SnapPriority, int] = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
}


@dataclass(
    slots=True,
    frozen=True,
)
class SnapTabFilter:

    statuses: tuple[SnapStatus, ...]

    types: tuple[SnapType, ...]


def resolve_tab(
    tab: SnapTab,
) -> SnapTabFilter:
    """
    The attention tab carries every type except recommendation, so it is
    derived by exclusion rather than an explicit list. A new SnapType then
    surfaces in the attention tab automatically.
    """

    if tab == "recommendation":
        return SnapTabFilter(
            statuses=("active",),
            types=("recommendation",),
        )

    if tab == "attention":
        return SnapTabFilter(
            statuses=("active",),
            types=tuple(
                snap_type
                for snap_type in SNAP_TYPES
                if snap_type != "recommendation"
            ),
        )

    if tab == "priority":
        return SnapTabFilter(
            statuses=("pending",),
            types=SNAP_TYPES,
        )

    raise ValueError(
        f"Unknown Snap tab '{tab}'.",
    )


def sort_key(
    record: SnapRecord,
) -> tuple[int, float, str]:

    return (
        _PRIORITY_RANK.get(
            record.snap.priority,
            len(_PRIORITY_RANK),
        ),
        -record.snap.confidence,
        record.created_at or "",
    )


@dataclass(
    slots=True,
    frozen=True,
)
class SnapBreakdown:

    key: str

    count: int

    share: float

    avg_confidence: float

    urgent: int


@dataclass(
    slots=True,
    frozen=True,
)
class SnapOverview:

    total: int

    active: int

    pending: int

    completed: int

    completion_rate: float

    avg_confidence: float

    urgent: int

    urgent_share: float

    by_priority: tuple[SnapBreakdown, ...]

    by_type: tuple[SnapBreakdown, ...]

    by_domain: tuple[SnapBreakdown, ...]


_URGENT_PRIORITIES: frozenset[str] = frozenset(
    {
        "critical",
        "high",
    },
)


def _ratio(
    part: int,
    total: int,
) -> float:

    if total <= 0:
        return 0.0

    return round(
        part / total,
        4,
    )


def _mean_confidence(
    records: list[SnapRecord],
) -> float:

    if not records:
        return 0.0

    return round(
        sum(
            record.snap.confidence
            for record in records
        ) / len(records),
        4,
    )


def _breakdown(
    records: list[SnapRecord],
    key: Callable[[SnapRecord], str],
    order: tuple[str, ...] | None = None,
) -> tuple[SnapBreakdown, ...]:
    """
    Groups records by `key`. When `order` is given the result follows it and
    empty groups are dropped, so callers get a stable ordering without having
    to sort in the UI.
    """

    groups: dict[str, list[SnapRecord]] = {}

    for record in records:
        groups.setdefault(
            key(record),
            [],
        ).append(
            record,
        )

    keys = (
        [name for name in order if name in groups]
        if order
        else sorted(
            groups,
            key=lambda name: -len(groups[name]),
        )
    )

    return tuple(
        SnapBreakdown(
            key=name,
            count=len(groups[name]),
            share=_ratio(
                len(groups[name]),
                len(records),
            ),
            avg_confidence=_mean_confidence(
                groups[name],
            ),
            urgent=sum(
                1
                for record in groups[name]
                if record.snap.priority in _URGENT_PRIORITIES
            ),
        )
        for name in keys
    )


def build_overview(
    *,
    active: list[SnapRecord],
    pending: list[SnapRecord],
    completed: list[SnapRecord],
) -> SnapOverview:
    """
    Aggregates every Snap the business currently has. Completed Snaps are
    included in the totals so the completion rate is meaningful, but the
    breakdowns cover open Snaps only, since those are the ones a user can act
    on.
    """

    total = len(active) + len(pending) + len(completed)
    open_snaps = active + pending

    urgent = sum(
        1
        for record in open_snaps
        if record.snap.priority in _URGENT_PRIORITIES
    )

    return SnapOverview(
        total=total,
        active=len(active),
        pending=len(pending),
        completed=len(completed),
        completion_rate=_ratio(
            len(completed),
            total,
        ),
        avg_confidence=_mean_confidence(
            open_snaps,
        ),
        urgent=urgent,
        urgent_share=_ratio(
            urgent,
            len(open_snaps),
        ),
        by_priority=_breakdown(
            open_snaps,
            lambda record: record.snap.priority,
            get_args(SnapPriority),
        ),
        by_type=_breakdown(
            open_snaps,
            lambda record: record.snap.type,
            SNAP_TYPES,
        ),
        by_domain=_breakdown(
            open_snaps,
            lambda record: record.snap.domain,
        ),
    )
