#!/usr/bin/env python3
"""
asset_generator.py

Generate 2‑D game graphics described in a spec file by calling the OpenAI Images API.

Revision history
----------------
* **r5** – Spec format is now *fully explicit*. Each non‑blank line **must** start
  with one of the whitelisted keywords—no generic “TAG VALUE” lines. Unknown
  tags abort parsing. The `--strict` flag was removed; strictness is always on.
* **r4** – Added detailed documentation for each configuration tag.
* **r3** – Replaced `INSTRUCTIONS` token with `PROMPT`.
* **r2** – Added strict whitelist for config tags.
* **r1** – Removed trailing colons from tokens.

Spec file format (v2)
---------------------
Each line (ignoring leading whitespace) **must begin with one of these tokens**
(case‑insensitive):

```
PROMPT <text …>
ASSET  <filename> <asset‑specific prompt>
MODEL  <dall-e-2|dall-e-3|gpt-image-1>
BACKGROUND <transparent|opaque|auto>
MODERATION <low|auto>
OUTPUT_COMPRESSION <0‑100>
OUTPUT_FORMAT <png|jpeg|webp>
QUALITY <auto|high|medium|low|hd|standard>
SIZE <WxH|auto>
STYLE <vivid|natural>
USER <identifier>
```

**Unknown keywords are a fatal error.** 

Example:

```text
PROMPT Create a clean top‑down 2‑D sprite on a transparent background.
MODEL gpt-image-1
SIZE 1024x1024
BACKGROUND transparent
ASSET road_straight_ns.png A seamless 256×256 asphalt road …
ASSET road_corner_ne.png  A 256×256 90‑degree bend …
```

Configuration reference
-----------------------
(unchanged – see table below for allowable values and defaults.)

Behaviour summary
-----------------
* Generates up to **‑n / --count** new sprites per run, skipping files that already exist.
* Saves each image plus `*.md` companion file containing the full prompt.
* Prints: `Created X; Y remaining; Z total.`
* Configuration precedence: **CLI > ENV vars > spec file**. Unknown config keys
  on the CLI or in ENV are ignored, but the spec file itself must be clean.
"""

from __future__ import annotations

import argparse
import base64
import os
import re
import sys
import textwrap
from pathlib import Path
from typing import Dict, List, Tuple

try:
    import requests
except ImportError:
    sys.exit("This script requires the ‘requests’ library; install with `pip install requests`")

###############################################################################
# Constants & regexes
###############################################################################

ALLOWED_TAGS = {
    "model",
    "background",
    "moderation",
    "n",
    "output_compression",
    "output_format",
    "quality",
    "response_format",
    "size",
    "style",
    "user",
}

_PROMPT_RE = re.compile(r"^\s*PROMPT\s+(.+)$", re.IGNORECASE)
_ASSET_RE = re.compile(r"^\s*ASSET\s+(\S+)\s+(.+)$", re.IGNORECASE)
_CONFIG_RE = re.compile(r"^\s*([A-Z_]+)\s+(.+)$")  # used only to detect keyword

###############################################################################
# Parsing (strict by design)
###############################################################################

def parse_spec(path: Path) -> Tuple[str, List[Tuple[str, str]], Dict[str, str]]:
    """Parse *path* and return (global_prompt, assets, config).

    Raises `SystemExit` on the first syntax or keyword error.
    """

    global_parts: List[str] = []
    assets: List[Tuple[str, str]] = []
    config: Dict[str, str] = {}

    with path.open(encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.rstrip("\n")
            if not line.strip():
                continue

            if (m := _PROMPT_RE.match(line)):
                global_parts.append(m.group(1).strip())
                continue
            if (m := _ASSET_RE.match(line)):
                filename, prompt_detail = m.groups()
                assets.append((filename.strip(), prompt_detail.strip()))
                continue
            if (m := _CONFIG_RE.match(line)):
                key, val = m.groups()
                key_lower = key.lower()
                if key_lower in ALLOWED_TAGS:
                    config[key_lower] = val.strip()
                    continue
                else:
                    sys.exit(f"Spec error line {lineno}: unknown keyword '{key}'.")
            # If line didn't match any pattern, it's invalid
            sys.exit(f"Spec error line {lineno}: malformed line.")

    return " ".join(global_parts).strip(), assets, config

###############################################################################
# OpenAI API helpers (unchanged)
###############################################################################

def build_payload(prompt: str, filename: str, cfg: Dict[str, str]) -> Dict[str, object]:
    payload: Dict[str, object] = {"prompt": prompt, "n": int(cfg.get("n", 1))}
    for key in ALLOWED_TAGS - {"n"}:
        if key in cfg:
            payload[key] = cfg[key]
    ext_map = {".png": "png", ".webp": "webp", ".jpg": "jpeg", ".jpeg": "jpeg"}
    if cfg.get("model", "dall-e-2").startswith("gpt-image") and "output_format" not in payload:
        if fmt := ext_map.get(Path(filename).suffix.lower()):
            payload["output_format"] = fmt
    return payload


def call_openai(payload: Dict[str, object], api_base: str, api_path: str, api_key: str):
    url = f"{api_base.rstrip('/')}/{api_path.lstrip('/')}"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    r = requests.post(url, headers=headers, json=payload, timeout=120)
    r.raise_for_status()
    return r.json()


def image_bytes(d: Dict[str, str]) -> bytes:
    if "b64_json" in d:
        return base64.b64decode(d["b64_json"])
    if "url" in d:
        return requests.get(d["url"], timeout=120).content
    raise ValueError("Unexpected image data object")

###############################################################################
# Generation loop (unchanged except strict removed)
###############################################################################

def generate(spec: Path, outdir: Path, limit: int, cfg_cli: Dict[str, str]):
    preamble, assets, cfg_file = parse_spec(spec)
    total = len(assets)

    env_cfg = {k.lower(): v for k, v in os.environ.items() if k.lower() in ALLOWED_TAGS}
    cfg = {**cfg_file, **env_cfg, **cfg_cli}

    api_base = cfg.get("api_base", os.getenv("OAI_API_BASE", "https://api.openai.com"))
    api_path = cfg.get("api_path", os.getenv("OAI_API_PATH", "/v1/images/generations"))
    api_key = cfg.get("api_key", os.getenv("OPENAI_API_KEY"))
    if not api_key:
        sys.exit("OPENAI_API_KEY (or --api-key) not provided.")

    created = 0
    outdir.mkdir(parents=True, exist_ok=True)

    for filename, details in assets:
        if created >= limit:
            break
        dest = outdir / filename
        if dest.exists():
            continue
        prompt = f"{preamble} {details}".strip()
        payload = build_payload(prompt, filename, cfg)
        try:
            rsp = call_openai(payload, api_base, api_path, api_key)
            img = image_bytes(rsp["data"][0])
            dest.write_bytes(img)
            dest.with_suffix(".md").write_text(textwrap.dedent(f"""
                # Prompt for {filename}
                ```
                {prompt}
                ```
                """))
            created += 1
            print(f"✓ {filename}")
        except Exception as exc:
            print(f"⚠️  {filename}: {exc}")

    rem = sum(1 for f, _ in assets if not (outdir / f).exists())
    print(f"Created {created}; {rem} remaining; {total} total.")

###############################################################################
# CLI (strict always)
###############################################################################

def parse_cli(argv=None):
    ap = argparse.ArgumentParser(description="Generate missing sprites from an asset spec.")
    ap.add_argument("spec", type=Path)
    ap.add_argument("-n", "--count", type=int, default=1, help="max images this run (default 1)")
    ap.add_argument("-o", "--output-dir", type=Path, default=Path("."))
    for tag in sorted(ALLOWED_TAGS):
        ap.add_argument(f"--{tag}")
    ap.add_argument("--api-base")
    ap.add_argument("--api-path")
    ap.add_argument("--api-key")
    ns = ap.parse_args(argv)

    cli_cfg = {k: v for k, v in vars(ns).items() if v is not None and k in ALLOWED_TAGS | {"api_base", "api_path", "api_key"}}
    return ns, cli_cfg


def main(argv=None):
    ns, cfg_cli = parse_cli(argv)
    generate(ns.spec, ns.output_dir, ns.count, cfg_cli)


if __name__ == "__main__":
    main()
