"""
AgentSkills folder-format reader.

Skill discovery rule:
  1. Look for `<skills_dir>/<slug>/SKILL.md` (folder format — preferred).
  2. Fall back to `<skills_dir>/<slug>.md` (flat — legacy, accepted with a warning).
  3. If both exist with the same slug, folder wins.

Frontmatter parsing is eager; body parsing is lazy (read on `load_skill`).
The empire-namespace metadata (`metadata.empire.*`) is surfaced verbatim so
agents can introspect a skill's runtime requirements before loading.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


@dataclass
class SkillIndex:
    slug: str
    name: str
    description: str
    path: Path
    is_folder_format: bool
    version: str | None = None
    emoji: str | None = None
    homepage: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    flat_warning: str | None = None  # set when discovered via legacy flat-file path


@dataclass
class Skill(SkillIndex):
    body: str = ""


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Return (frontmatter_dict, body). Empty dict if no frontmatter."""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        fm = {}
    return fm, m.group(2)


def _index_from(path: Path, fm: dict[str, Any], is_folder: bool, flat_warning: str | None = None) -> SkillIndex:
    slug = fm.get("name") or (path.parent.name if is_folder else path.stem)
    return SkillIndex(
        slug=slug,
        name=fm.get("name", slug),
        description=fm.get("description", ""),
        path=path,
        is_folder_format=is_folder,
        version=fm.get("version"),
        emoji=fm.get("emoji"),
        homepage=fm.get("homepage"),
        metadata=fm.get("metadata") or {},
        flat_warning=flat_warning,
    )


def list_skills(skills_dir: Path, active_filter: list[str] | None = None) -> list[SkillIndex]:
    """
    Return indexed skills (frontmatter only — bodies not loaded).

    If active_filter is non-empty, only skills whose slug is in the filter are
    returned. (active_filter is the workspace's `active_skills` list.)
    """
    if not skills_dir.exists():
        return []

    found: dict[str, SkillIndex] = {}

    # Folder format wins — index it first
    for skill_md in skills_dir.glob("*/SKILL.md"):
        try:
            fm, _ = _parse_frontmatter(skill_md.read_text())
        except Exception:
            continue
        idx = _index_from(skill_md, fm, is_folder=True)
        found[idx.slug] = idx

    # Flat fallback — only adds skills not already indexed by folder
    for flat in skills_dir.glob("*.md"):
        if flat.stem in ("README", "INSTRUCTIONS"):
            continue
        if flat.stem in found:
            continue
        try:
            fm, _ = _parse_frontmatter(flat.read_text())
        except Exception:
            continue
        warning = (
            f"Flat-file skill '{flat.name}' detected. AgentSkills format is "
            f"<slug>/SKILL.md — consider migrating."
        )
        idx = _index_from(flat, fm, is_folder=False, flat_warning=warning)
        found[idx.slug] = idx

    skills = sorted(found.values(), key=lambda s: s.slug)
    if active_filter:
        active_set = set(active_filter)
        skills = [s for s in skills if s.slug in active_set]
    return skills


def load_skill(skills_dir: Path, slug: str) -> Skill | None:
    """Load full skill body. Tolerant of partial slugs (single unambiguous match)."""
    if not skills_dir.exists():
        return None

    slug_l = slug.strip().lower()
    if slug_l.endswith(".md"):
        slug_l = slug_l[:-3]

    indices = list_skills(skills_dir)
    # Exact match
    for idx in indices:
        if idx.slug.lower() == slug_l:
            return _hydrate(idx)
    # Substring match — prefer the shortest slug if multiple
    matches = [idx for idx in indices if slug_l in idx.slug.lower()]
    if matches:
        matches.sort(key=lambda i: len(i.slug))
        return _hydrate(matches[0])
    return None


def _hydrate(idx: SkillIndex) -> Skill:
    text = idx.path.read_text()
    fm, body = _parse_frontmatter(text)
    return Skill(
        slug=idx.slug,
        name=idx.name,
        description=idx.description,
        path=idx.path,
        is_folder_format=idx.is_folder_format,
        version=idx.version,
        emoji=idx.emoji,
        homepage=idx.homepage,
        metadata=idx.metadata,
        flat_warning=idx.flat_warning,
        body=body.strip(),
    )


def index_to_dict(idx: SkillIndex) -> dict[str, Any]:
    return {
        "slug": idx.slug,
        "name": idx.name,
        "description": idx.description,
        "version": idx.version,
        "emoji": idx.emoji,
        "homepage": idx.homepage,
        "metadata": idx.metadata,
        "is_folder_format": idx.is_folder_format,
        "flat_warning": idx.flat_warning,
    }


def skill_to_dict(s: Skill) -> dict[str, Any]:
    d = index_to_dict(s)
    d["body"] = s.body
    return d
