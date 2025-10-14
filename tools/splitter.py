import os, re, unicodedata

# ---- CONFIG ----
SOURCE_ROOT = "source"                               # all daily docs
OUT_ROOT    = "german-revision-helper/content"       # Hugo content/ root
VERBOSE     = os.environ.get("SPLIT_VERBOSE", "0") == "1"
# --------------

_slug_ascii = lambda s: re.sub(
    r"-{2,}", "-",
    re.sub(
        r"[\s/]+", "-",
        re.sub(
            r"[^\w\s-]", "",
            unicodedata.normalize("NFKD", re.sub(r"[*_`~#>]", "", s)).encode("ascii","ignore").decode("ascii")
        ).strip().lower()
    )
)

for _root, _dirs, _files in os.walk(SOURCE_ROOT):
    for _f in _files:
        if not _f.endswith(".md"):
            continue
        if _f.startswith(".") or _f.lower() == "template.md":
            continue

        IN_PATH = os.path.join(_root, _f)

        # per-document counters
        section_counts = {
            "grammar": {"new": 0, "updated": 0},
            "verbs": {"new": 0, "updated": 0},
            "vocabulary": {"new": 0, "updated": 0},
            "phrases": {"new": 0, "updated": 0},
            "daily paragraph": {"new": 0, "updated": 0},
        }
        total_new = 0
        total_updated = 0
        wrote_any = False

        text = open(IN_PATH, "r", encoding="utf-8").read()

        # date from top front matter or filename
        date = None
        _m = re.search(r"^---\s*(.*?)^---", text, flags=re.S|re.M)
        if _m:
            _fm = _m.group(1)
            _md = re.search(r'(?im)^\s*Date:\s*"?(?P<d>\d{4}-\d{2}-\d{2})"?', _fm)
            if _md: date = _md.group("d")
        if not date:
            _md = re.search(r'(\d{4}-\d{2}-\d{2})', IN_PATH)
            date = _md.group(1) if _md else "1970-01-01"

        # find top-level sections (# ...)
        _sections = []
        for _h1 in re.finditer(r"(?m)^#\s+(.+)$", text):
            _sections.append((_h1.start(), _h1.group(1).strip()))
        _sections.append((len(text), "__END__"))

        for _i in range(len(_sections)-1):
            sec_start, sec_name = _sections[_i]
            sec_end, _ = _sections[_i+1]
            sec_body = text[sec_start:sec_end]

            sec_key = sec_name.strip().lower()
            if sec_key not in {"grammar","vocabulary","verbs","daily paragraph","phrases"}:
                continue

            # H2 items under this section (## ...)
            _items = []
            for _h2 in re.finditer(r"(?m)^##\s+(.+)$", sec_body):
                _items.append((_h2.start(), _h2.group(1).strip()))
            _items.append((len(sec_body), "__END__"))

            for _j in range(len(_items)-1):
                item_start, item_title_raw = _items[_j]
                item_end, _ = _items[_j+1]
                block = sec_body[item_start:item_end]

                # title clean (for display); slug based on plain text
                item_title = re.sub(r"[*_`]+", "", item_title_raw).strip()
                _title_for_slug = item_title

                # parse sectionmeta fence (optional)
                meta_level = ""
                meta_topics = []; meta_usage = []; meta_themes = []; meta_context = []

                _fence = re.search(r"```sectionmeta\s*(.*?)\s*```", block, flags=re.S)
                if _fence:
                    meta_raw = _fence.group(1)

                    _ml = re.search(r'(?im)^\s*level\s*:\s*("?)([A-C][1-2])\1', meta_raw)
                    if _ml: meta_level = _ml.group(2).upper()

                    for _key in ("topics","usage","themes","context"):
                        _mm = re.search(rf'(?im)^\s*{_key}\s*:\s*(\[.*?\]|.+)$', meta_raw)
                        if _mm:
                            _val = _mm.group(1).strip()
                            if _val.startswith("[") and _val.endswith("]"): _val = _val[1:-1]
                            _parts = [p.strip() for p in _val.split(",") if p.strip()]
                            _norm = [re.sub(r"[\s/]+","-", p.lower()) for p in _parts]
                            if _key=="topics": meta_topics = _norm
                            if _key=="usage":  meta_usage  = _norm
                            if _key=="themes": meta_themes = _norm
                            if _key=="context":meta_context= _norm

                # body after fence (or after H2 line if no fence)
                if _fence:
                    body = block[_fence.end():].lstrip()
                else:
                    body = re.sub(r"(?m)^##\s+.+\n", "", block, count=1).lstrip()

                # slug for grammar/verbs; date-based for daily list sections
                _slug = _slug_ascii(_title_for_slug)

                if sec_key == "grammar":
                    out_dir = os.path.join(OUT_ROOT, "grammar", _slug)
                    title_out = item_title
                elif sec_key == "verbs":
                    out_dir = os.path.join(OUT_ROOT, "verbs", _slug)
                    title_out = item_title
                elif sec_key == "vocabulary":
                    out_dir = os.path.join(OUT_ROOT, "vocabulary", "lists", date)
                    title_out = f"Vocabulary — {date}"
                elif sec_key == "phrases":
                    out_dir = os.path.join(OUT_ROOT, "phrases", "lists", date)
                    title_out = f"Phrases — {date}"
                elif sec_key == "daily paragraph":
                    out_dir = os.path.join(OUT_ROOT, "writing", "daily", date)
                    title_out = f"Daily Paragraph — {date}"
                else:
                    continue

                # derived tags
                tags = []
                if sec_key: tags.append("section-" + re.sub(r"[\s/]+","-", sec_key))
                if meta_level: tags.append("level-" + meta_level.lower())
                for _v in meta_topics:  tags.append("topic-"   + _v)
                for _v in meta_usage:   tags.append("usage-"   + _v)
                for _v in meta_themes:  tags.append("theme-"   + _v)
                for _v in meta_context: tags.append("context-" + _v)

                # write leaf bundle with new/updated tracking
                os.makedirs(out_dir, exist_ok=True)
                out_path = os.path.join(out_dir, "index.md")
                existed_before = os.path.exists(out_path)

                front = []
                front.append("---")
                front.append(f'title: "{title_out}"')
                front.append(f'date: "{date}"')
                front.append(f'level: "{meta_level}"')
                front.append("topics: [" + ", ".join(f'"{x}"' for x in meta_topics) + "]")
                front.append("usage: [" + ", ".join(f'"{x}"' for x in meta_usage) + "]")
                front.append("themes: [" + ", ".join(f'"{x}"' for x in meta_themes) + "]")
                front.append("context: [" + ", ".join(f'"{x}"' for x in meta_context) + "]")
                front.append("draft: false")
                front.append("tags: [" + ", ".join(f'"{t}"' for t in tags) + "]")
                front.append("---\n")

                with open(out_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(front))
                    f.write(body.strip() + "\n")

                wrote_any = True
                if existed_before:
                    total_updated += 1
                    section_counts[sec_key]["updated"] += 1
                    if VERBOSE:
                        print(f"updated -> {out_path}")
                else:
                    total_new += 1
                    section_counts[sec_key]["new"] += 1
                    if VERBOSE:
                        print(f"new -> {out_path}")

        # per-document summary
        if not wrote_any:
            print(f"[SKIP] {IN_PATH} (no known sections)")
        else:
            print(f"[OK]   {IN_PATH} total={total_new + total_updated} new={total_new} updated={total_updated}")
            # per-section counters
            for _k in ("grammar","verbs","vocabulary","phrases","daily paragraph"):
                c = section_counts[_k]
                if c["new"] or c["updated"]:
                    print(f"  {_k}: new={c['new']} updated={c['updated']}")
