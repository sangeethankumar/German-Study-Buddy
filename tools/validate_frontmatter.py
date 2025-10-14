#!/usr/bin/env python3
"""
Validate generated Hugo front matter for each leaf bundle index.md.

Checks:
- Presence and basic types of required fields
- ISO date format (YYYY-MM-DD)
- Controlled vocabularies for section, level, topics, usage, themes, context
- Optional enforcement of key order for reproducibility
"""

import os
import re
import sys
import datetime
import yaml
from typing import Dict, List

# -------- CONFIG --------
CONTENT_DIRS = ["german-revision-helper/content", "content"]

ENFORCE_VOCAB = True
ENFORCE_KEY_ORDER = True

EXPECTED_KEY_ORDER = [
    "title", "date", "section", "level", "topics", "usage", "themes", "context",
]

# Accept both Title-Case/space and lowercase-hyphen variants
ALLOWED_SECTION_FIELD = {
    "Grammar Concept", "Vocabulary", "Verb", "Daily Paragraph", "Phrases",
    "grammar-concept", "vocabulary", "verb", "daily-paragraph", "phrases",
}

ALLOWED_LEVELS = {"A1","A2","B1","B2","C1","C2"}

ALLOWED_TOPICS = {
    # Title-Case / space forms
    "Nouns","Adjectives","Adverbs","Verbs Grammar","Word Order","Prepositions",
    "Cases","Tenses","Modal Verbs","Comparison","Pronouns","Conjunctions","Idiomatic",
    # lowercase-hyphen forms (what your bundles use)
    "nouns","adjectives","adverbs","verbs-grammar","word-order","prepositions",
    "cases","tenses","modal-verbs","comparison","pronouns","conjunctions","idiomatic",
}

ALLOWED_USAGE = {
    "Common","Colloquial","Formal","Idiomatic","Rare",
    "common","colloquial","formal","idiomatic","rare",
}

ALLOWED_THEMES = {
    # Title-Case / space
    "Daily Life","Feelings","Travel","Work","Weather","Food",
    "Family","Education","Nature","Health","Story Context",
    # lowercase-hyphen
    "daily-life","feelings","travel","work","weather","food",
    "family","education","nature","health","story-context",
}

ALLOWED_CONTEXT = {
    # Title-Case / space
    "Harry Potter","Book Based Learning","Story Context","Textbook Context","Real Conversations",
    # lowercase-hyphen
    "harry-potter","book-based-learning","story-context","textbook-context","real-conversations",
}

# Required fields (keep original behavior: 'section' is NOT required)
REQUIRED_FIELDS = {"title", "date", "level"}
# ------------------------


def find_content_roots() -> List[str]:
    roots = []
    for d in CONTENT_DIRS:
        if os.path.isdir(d):
            roots.append(d)
    return roots

def load_front_matter(text: str):
    m = re.search(r"^---\s*(.*?)\s*^---\s*", text, re.S | re.M)
    if not m:
        return None, None, "missing front matter (--- ... ---) at top"
    raw_yaml = m.group(1)
    try:
        fm = yaml.safe_load(raw_yaml) or {}
    except Exception as e:
        return None, raw_yaml, f"YAML parse error: {e}"
    return fm, raw_yaml, None

def normalize_key(key: str) -> str:
    return (key or "").strip().lower().replace("_", "-")

def get_key_order_from_raw_yaml(raw_yaml: str) -> List[str]:
    """
    Extract top-level key order as they appear in YAML.
    Handles common scalar/list lines. This is a heuristic (good enough for our generated files).
    """
    keys = []
    for line in raw_yaml.splitlines():
        # Ignore comments and empty lines
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        # Top-level key: value
        m = re.match(r"^([A-Za-z0-9_\-]+)\s*:\s*", line)
        if m:
            keys.append(normalize_key(m.group(1)))
    # Deduplicate while preserving order
    seen = set()
    ordered = []
    for k in keys:
        if k not in seen:
            seen.add(k)
            ordered.append(k)
    return ordered

def ensure_list_of_str(value, keyname, issues):
    if value is None:
        return []
    if not isinstance(value, list):
        issues.append(f"'{keyname}' must be a list of strings")
        return []
    bad = [x for x in value if not isinstance(x, str)]
    if bad:
        issues.append(f"'{keyname}' contains non-string items: {bad!r}")
    return value

def validate_vocab_list(values: List[str], allowed: set, keyname: str, issues: List[str]):
    if values is None:
        return
    bad = [v for v in values if v not in allowed]
    if bad and ENFORCE_VOCAB:
        issues.append(f"'{keyname}' has values not in allowed set: {bad}")

def validate_front_matter_dict(fm: Dict, raw_yaml: str, file_path: str) -> List[str]:
    issues = []

    if not isinstance(fm, dict):
        issues.append("front matter must be a mapping")
        return issues

    # Normalize keys for lookups (still use original fm for type checks)
    fm_norm = {normalize_key(k): v for k, v in fm.items()}

    # Required fields present?
    missing = [k for k in REQUIRED_FIELDS if k not in fm_norm]
    if missing:
        issues.append(f"missing required field(s): {missing}")

    # title
    title = fm_norm.get("title")
    if title is not None and not (isinstance(title, str) and title.strip()):
        issues.append("'title' must be a non-empty string")

    # date
    date_s = fm_norm.get("date")
    if date_s is None or not isinstance(date_s, (str,)):
        issues.append("'date' must be a string in YYYY-MM-DD")
    else:
        try:
            datetime.date.fromisoformat(date_s)
        except Exception:
            issues.append(f"'date' not ISO (YYYY-MM-DD): {date_s!r}")

    # section
    section = fm_norm.get("section")
    if section is not None:
        if not isinstance(section, str):
            issues.append("'section' must be a string")
        elif ENFORCE_VOCAB and section not in ALLOWED_SECTION_FIELD:
            issues.append(f"invalid 'section': {section!r}")

    # level
    level = fm_norm.get("level")
    if level is not None:
        if not isinstance(level, str):
            issues.append("'level' must be a string")
        else:
            lvl = level.upper()
            if ENFORCE_VOCAB and lvl not in ALLOWED_LEVELS:
                issues.append(f"invalid 'level': {level!r} (allowed: {sorted(ALLOWED_LEVELS)})")

    # list-like fields
    topics  = ensure_list_of_str(fm_norm.get("topics"),  "topics",  issues)
    usage   = ensure_list_of_str(fm_norm.get("usage"),   "usage",   issues)
    themes  = ensure_list_of_str(fm_norm.get("themes"),  "themes",  issues)
    context = ensure_list_of_str(fm_norm.get("context"), "context", issues)

    if ENFORCE_VOCAB:
        validate_vocab_list(topics,  ALLOWED_TOPICS,  "topics",  issues)
        validate_vocab_list(usage,   ALLOWED_USAGE,   "usage",   issues)
        validate_vocab_list(themes,  ALLOWED_THEMES,  "themes",  issues)
        validate_vocab_list(context, ALLOWED_CONTEXT, "context", issues)

    # Optional: tags (if present, just type-check)
    if "tags" in fm_norm:
        tags = fm_norm.get("tags")
        ensure_list_of_str(tags, "tags", issues)

    # Key order enforcement (heuristic on raw YAML)
    if ENFORCE_KEY_ORDER and raw_yaml:
        seen_order = get_key_order_from_raw_yaml(raw_yaml)
        # Only compare order of EXPECTED_KEY_ORDER keys that are present
        expected_present = [k for k in EXPECTED_KEY_ORDER if k in fm_norm]
        seen_filtered = [k for k in seen_order if k in expected_present]
        if seen_filtered != expected_present:
            issues.append(
                "front matter key order mismatch. Expected order for present keys: "
                f"{expected_present}; found: {seen_filtered}"
            )

    return issues

def iter_index_files(roots: List[str]):
    for base in roots:
        for root, dirs, files in os.walk(base):
            for f in files:
                if f.lower() == "index.md":
                    yield os.path.join(root, f)

def main():
    roots = find_content_roots()
    if not roots:
        print("[WARN] No content roots found. Checked:", ", ".join(CONTENT_DIRS))
        sys.exit(0)

    errors = []
    checked = 0
    total_ok = 0

    for path in iter_index_files(roots):
        checked += 1
        try:
            text = open(path, encoding="utf-8").read()
        except Exception as e:
            print(f"[FAIL] {path}: cannot read file: {e}")
            errors.append(path)
            continue

        fm, raw_yaml, err = load_front_matter(text)
        if err:
            print(f"[FAIL] {path}: {err}")
            errors.append(path)
            continue

        issues = validate_front_matter_dict(fm, raw_yaml, path)
        if issues:
            print(f"[FAIL] {path}: " + "; ".join(issues))
            errors.append(path)
        else:
            total_ok += 1
            print(f"[OK]   {path}")

    if errors:
        print(f"\n{len(errors)} file(s) failed front matter validation out of {checked} checked.")
        sys.exit(1)
    else:
        print(f"\nAll {checked} index.md files validated successfully.")
        sys.exit(0)

if __name__ == "__main__":
    main()
