"""
Relationship Resolver
=====================
Parses dependency notation strings and builds predecessor/successor cross-references.

Supported notations:
  "489"          → simple Finish-to-Start, no lag
  "439;440;441"  → multiple FS predecessors (semicolon-separated)
  "1024FS+24"    → FS with +24 hour lag
  "1024SS-8"     → SS with -8 hour lag
  "1024FF"       → FF, no lag
"""
from __future__ import annotations
import re
import logging
from typing import Dict, List, Tuple
from ingestion.models.nusf import Relationship, DependencyType

logger = logging.getLogger(__name__)

_DEP_RE = re.compile(
    r"([A-Za-z0-9._\-]+?)"
    r"(?:(FS|SS|FF|SF))?"
    r"(?:([+\-]\d+))?"
    r"$",
    re.IGNORECASE,
)


def _parse_single_dep(token: str) -> Tuple[str, DependencyType, int]:
    """
    Returns (predecessor_source_id, dep_type, lag_hours).
    """
    token = token.strip()
    if not token:
        return "", DependencyType.FS, 0

    m = _DEP_RE.match(token)
    if not m:
        return token, DependencyType.FS, 0

    pred_id = m.group(1).strip()
    dep_str = (m.group(2) or "FS").upper()
    lag_str = m.group(3) or "0"

    try:
        dep_type = DependencyType(dep_str)
    except ValueError:
        dep_type = DependencyType.FS

    try:
        lag_hours = int(lag_str)
    except ValueError:
        lag_hours = 0

    return pred_id, dep_type, lag_hours


def parse_predecessor_string(value: str) -> List[Tuple[str, DependencyType, int]]:
    """
    Parse a predecessor field value into list of (source_id, dep_type, lag_hours).
    Handles semicolon-separated and comma-separated multi-predecessor strings.
    """
    if not value or not value.strip() or value.strip() in ("-", "—"):
        return []

    separators = r"[;,\s]+"
    tokens = re.split(separators, value.strip())
    results = []
    for token in tokens:
        token = token.strip()
        if not token:
            continue
        pred_id, dep_type, lag = _parse_single_dep(token)
        if pred_id:
            results.append((pred_id, dep_type, lag))
    return results


def build_relationships(
    activities_by_source_id: Dict[str, str],
    raw_predecessors: Dict[str, str],
    raw_successors: Dict[str, str],
) -> List[Relationship]:
    """
    Build Relationship objects from raw predecessor/successor strings.

    Args:
        activities_by_source_id: {source_id → internal_id}
        raw_predecessors: {internal_id → raw predecessor string}
        raw_successors:   {internal_id → raw successor string}

    Returns:
        List of Relationship objects (broken=True if referencing unknown activity)
    """
    relationships: List[Relationship] = []
    seen: set = set()

    for succ_internal_id, pred_str in raw_predecessors.items():
        deps = parse_predecessor_string(pred_str)
        for pred_source_id, dep_type, lag_hours in deps:
            pred_internal_id = activities_by_source_id.get(pred_source_id)
            is_broken = pred_internal_id is None

            if is_broken:
                pred_internal_id = f"__unknown_{pred_source_id}"

            edge_key = (pred_internal_id, succ_internal_id, dep_type.value)
            if edge_key in seen:
                continue
            seen.add(edge_key)

            relationships.append(
                Relationship(
                    predecessor_id=pred_internal_id,
                    successor_id=succ_internal_id,
                    lag_hours=lag_hours,
                    type=dep_type,
                    is_broken=is_broken,
                )
            )

    for pred_internal_id, succ_str in raw_successors.items():
        deps = parse_predecessor_string(succ_str)
        for succ_source_id, dep_type, lag_hours in deps:
            succ_internal_id = activities_by_source_id.get(succ_source_id)
            is_broken = succ_internal_id is None

            if is_broken:
                succ_internal_id = f"__unknown_{succ_source_id}"

            edge_key = (pred_internal_id, succ_internal_id, dep_type.value)
            if edge_key in seen:
                continue
            seen.add(edge_key)

            relationships.append(
                Relationship(
                    predecessor_id=pred_internal_id,
                    successor_id=succ_internal_id,
                    lag_hours=lag_hours,
                    type=dep_type,
                    is_broken=is_broken,
                )
            )

    return relationships
