import os, re, sys, yaml, datetime

# ---- CONFIG ----
SOURCE_DIR = "source"  # scan all .md under this folder

# If True, enforce controlled vocabularies below. If False, only types are checked.
ENFORCE_VOCAB = True

# Allowed top-level H1 section names in the daily doc
ALLOWED_H1_SECTIONS = {"grammar","vocabulary","verbs","daily paragraph","phrases"}

# Allowed values for sectionmeta fields (aligned with template + project snapshot).
# See template structure for placement/order expectations. :contentReference[oaicite:0]{index=0}
ALLOWED_SECTION_FIELD = {"Grammar Concept","Vocabulary","Verb","Daily Paragraph","Phrases"}

# Keep broad; validator accepts A1–C2 even if daily templates commonly use A1–B1. :contentReference[oaicite:1]{index=1}
ALLOWED_LEVELS = {"A1","A2","B1","B2","C1","C2"}

# Topics (added Adverbs, Conjunctions) :contentReference[oaicite:2]{index=2}
ALLOWED_TOPICS = {
    "Nouns","Adjectives","Adverbs","Verbs Grammar","Word Order","Prepositions",
    "Cases","Tenses","Modal Verbs","Comparison","Pronouns","Conjunctions","Idiomatic"
}

# Usage (unchanged) :contentReference[oaicite:3]{index=3}
ALLOWED_USAGE = {"Common","Colloquial","Formal","Idiomatic"}

# Themes (added Family, Education, Nature, Health) :contentReference[oaicite:4]{index=4}
ALLOWED_THEMES = {
    "Daily Life","Feelings","Travel","Work","Weather","Food",
    "Family","Education","Nature","Health","Story Context"
}

# Context (added Textbook Context, Real Conversations) :contentReference[oaicite:5]{index=5}
ALLOWED_CONTEXT = {
    "Harry Potter","Book Based Learning","Story Context","Textbook Context","Real Conversations"
}
# ----------------

errors = []
checked = 0

for root, dirs, files in os.walk(SOURCE_DIR):
    for f in files:
        if not f.endswith(".md"):
            continue
        path = os.path.join(root, f)
        checked += 1
        issues = []
        total_blocks = 0

        try:
            text = open(path, encoding="utf-8").read()
        except Exception as e:
            issues.append(f"cannot read file: {e}")
            print(f"[FAIL] {path}: {'; '.join(issues)}")
            errors.append(path)
            continue

        # --- Top front matter (--- ... ---) ---
        m = re.search(r"^---\s*(.*?)\s*^---\s*", text, re.S | re.M)
        if not m:
            issues.append("missing top front matter (--- ... ---)")
            fm = {}
        else:
            try:
                fm = yaml.safe_load(m.group(1)) or {}
            except Exception as e:
                fm = {}
                issues.append(f"YAML parse error in top front matter: {e}")

        if fm:
            missing = [k for k in ["Title","Date","Summary"] if k not in fm]
            if missing:
                issues.append(f"missing top fields {missing}")

            if "Title" in fm and (not isinstance(fm["Title"], str) or not fm["Title"].strip()):
                issues.append("Title must be a non-empty string")

            date_s = fm.get("Date")
            if not isinstance(date_s, str):
                issues.append("Date must be a string in YYYY-MM-DD")
            else:
                try:
                    datetime.date.fromisoformat(date_s)
                except Exception:
                    issues.append(f"Date not ISO (YYYY-MM-DD): {date_s!r}")

            if "Summary" in fm and (not isinstance(fm["Summary"], str) or not fm["Summary"].strip()):
                issues.append("Summary must be a non-empty string")

            if "Source" in fm and not isinstance(fm.get("Source"), str):
                issues.append("Source must be a string if present")

        # --- Sections and H2 blocks ---
        body = text[m.end():] if m else text

        sections = []
        for mm in re.finditer(r"(?m)^#\s+(.+)$", body):
            sections.append((mm.start(), mm.group(1).strip()))
        sections.append((len(body), "__END__"))

        for i in range(len(sections)-1):
            s_start, s_name = sections[i]
            s_end, _ = sections[i+1]
            s_body = body[s_start:s_end]

            sec_key = s_name.lower().strip()
            if sec_key not in ALLOWED_H1_SECTIONS:
                # ignore unknown top-level sections; could be notes
                continue

            items = []
            for mm in re.finditer(r"(?m)^##\s+(.+)$", s_body):
                items.append((mm.start(), mm.group(1).strip()))
            items.append((len(s_body), "__END__"))

            for j in range(len(items)-1):
                total_blocks += 1
                i_start, h2_title = items[j]
                i_end, _ = items[j+1]
                block = s_body[i_start:i_end]

                fence = re.search(r"```sectionmeta\s*(.*?)\s*```", block, flags=re.S)
                if not fence:
                    issues.append(f"missing sectionmeta under H2 '{h2_title}' in section '{s_name}'")
                    continue

                meta_raw = fence.group(1)

                # Collect values (order not enforced here; presence/type/allowed are)
                # section (optional enforcement)
                m_section = re.search(r'(?im)^\s*section\s*:\s*(.+)$', meta_raw)
                if m_section:
                    section_val = m_section.group(1).strip()
                    # strip wrapping brackets or quotes
                    if section_val.startswith("[") and section_val.endswith("]"):
                        section_val = section_val[1:-1].strip()
                    section_val = re.sub(r'^\s*"(.*)"\s*$', r"\1", section_val)
                    if ENFORCE_VOCAB and section_val not in ALLOWED_SECTION_FIELD:
                        issues.append(f"invalid section value '{section_val}' under '{h2_title}'")
                else:
                    # section is present in template; warn if missing. :contentReference[oaicite:6]{index=6}
                    issues.append(f"sectionmeta missing 'section' under H2 '{h2_title}'")

                # level
                m_level = re.search(r'(?im)^\s*level\s*:\s*("?)([A-Za-z0-9\-–]+)\1\s*$', meta_raw)
                if not m_level:
                    issues.append(f"sectionmeta missing 'level' under H2 '{h2_title}'")
                    lvlv = None
                else:
                    lvlv = m_level.group(2).upper()
                    if ENFORCE_VOCAB and lvlv not in ALLOWED_LEVELS:
                        issues.append(f"invalid level '{lvlv}' under '{h2_title}' (allowed: {sorted(ALLOWED_LEVELS)})")

                # list-like fields (allow empty lists)
                def _grab_list(field):
                    mm2 = re.search(rf'(?im)^\s*{field}\s*:\s*(.+)$', meta_raw)
                    if not mm2:
                        return None, f"sectionmeta missing '{field}' under H2 '{h2_title}'"
                    raw = mm2.group(1).strip()
                    if raw.startswith("[") and raw.endswith("]"):
                        raw = raw[1:-1]
                    items2 = [x.strip() for x in raw.split(",")] if raw else []
                    bad = [x for x in items2 if not isinstance(x, str)]
                    if bad:
                        return None, f"{field} contains non-string item(s) under '{h2_title}': {bad!r}"
                    return items2, None

                topics, err = _grab_list("topics");  issues.append(err) if err else None
                usage, err  = _grab_list("usage");   issues.append(err) if err else None
                themes, err = _grab_list("themes");  issues.append(err) if err else None
                context, err= _grab_list("context"); issues.append(err) if err else None

                if ENFORCE_VOCAB:
                    if topics is not None:
                        bad = [x for x in topics if x not in ALLOWED_TOPICS]
                        if bad: issues.append(f"topics contains values not in allowed list under '{h2_title}': {bad}")
                    if usage is not None:
                        bad = [x for x in usage if x not in ALLOWED_USAGE]
                        if bad: issues.append(f"usage contains values not in allowed list under '{h2_title}': {bad}")
                    if themes is not None:
                        bad = [x for x in themes if x not in ALLOWED_THEMES]
                        if bad: issues.append(f"themes contains values not in allowed list under '{h2_title}': {bad}")
                    if context is not None:
                        bad = [x for x in context if x not in ALLOWED_CONTEXT]
                        if bad: issues.append(f"context contains values not in allowed list under '{h2_title}': {bad}")

        if issues:
            print(f"[FAIL] {path}: " + "; ".join(issues))
            errors.append(path)
        else:
            print(f"[OK]   {path} (blocks validated: {total_blocks})")

# ---- Summary ----
if errors:
    print(f"\n{len(errors)} file(s) failed validation out of {checked} checked.")
    sys.exit(1)
else:
    print(f"\nAll {checked} source markdown files validated successfully.")
    sys.exit(0)
