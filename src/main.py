#!/usr/bin/env python3
"""
asset_generator.py

Generate game graphics described in a spec file by calling the OpenAI Images API.

Revision history
----------------
* **r8** – Changed default behavior to exit on API errors
* **r7** – Added support for OpenAI-Organization and OpenAI-Project headers
* **r6** – Added rate limiting support with automatic request throttling
* **r5** – Spec format is now *fully explicit*. Each non‑blank line **must** start
  with one of the whitelisted keywords—no generic "TAG VALUE" lines. Unknown
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
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

try:
    import requests
except ImportError:
    sys.exit("This script requires the 'requests' library; install with `pip install requests`")

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
    "openai_organization",
    "openai_project",
    "continue_on_error",
}

_PROMPT_RE = re.compile(r"^\s*PROMPT\s+(.+)$", re.IGNORECASE)
_ASSET_RE = re.compile(r"^\s*ASSET\s+(\S+)\s+(.+)$", re.IGNORECASE)
_CONFIG_RE = re.compile(r"^\s*([A-Z_]+)\s+(.+)$")  # used only to detect keyword

###############################################################################
# Parsing (strict by design)
###############################################################################

def parse_spec(path: Path) -> Tuple[str, List[Tuple[str, str]], Dict[str, str], int]:
    """Parse *path* and return (global_prompt, assets, config, total_assets).

    Raises `SystemExit` on the first syntax or keyword error.
    """

    global_parts: List[str] = []
    assets: List[Tuple[str, str]] = []
    config: Dict[str, str] = {}

    print("\nReading configuration from spec file:")
    print("-" * 40)

    with path.open(encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.rstrip("\n")
            if not line.strip():
                continue

            if (m := _PROMPT_RE.match(line)):
                global_parts.append(m.group(1).strip())
                print(f"PROMPT: {m.group(1).strip()}")
                continue
            if (m := _ASSET_RE.match(line)):
                filename, prompt_detail = m.groups()
                assets.append((filename.strip(), prompt_detail.strip()))
                print(f"ASSET: {filename.strip()} -> {prompt_detail.strip()}")
                continue
            if (m := _CONFIG_RE.match(line)):
                key, val = m.groups()
                key_lower = key.lower()
                if key_lower in ALLOWED_TAGS:
                    config[key_lower] = val.strip()
                    print(f"{key}: {val.strip()}")
                    continue
                else:
                    sys.exit(f"Spec error line {lineno}: unknown keyword '{key}'.")
            # If line didn't match any pattern, it's invalid
            sys.exit(f"Spec error line {lineno}: malformed line.")

    print("-" * 40)
    total_assets = len(assets)
    print(f"Found {total_assets} total assets in spec file\n")

    return " ".join(global_parts).strip(), assets, config, total_assets

###############################################################################
# OpenAI API helpers (unchanged)
###############################################################################

def build_payload(prompt: str, filename: str, cfg: Dict[str, str]) -> Dict[str, object]:
    # Base payload with required parameters
    payload: Dict[str, object] = {
        "prompt": prompt,
        "n": 1,  # Always request one image at a time
        "model": "gpt-image-1"  # Default to gpt-image-1
    }
    
    # Add response_format only for dall-e models
    model = cfg.get("model", "gpt-image-1")
    if model.startswith("dall-e"):
        payload["response_format"] = "b64_json"
    
    # Add other allowed parameters from config, excluding internal parameters
    internal_params = {
        "n", "response_format", "continue_on_error", 
        "api_base", "api_path", "api_key",
        "openai_organization", "openai_project"
    }
    for key in ALLOWED_TAGS - internal_params:
        if key in cfg:
            payload[key] = cfg[key]
            
    # Set output format based on file extension
    ext_map = {".png": "png", ".webp": "webp", ".jpg": "jpeg", ".jpeg": "jpeg"}
    if model.startswith("gpt-image") and "output_format" not in payload:
        if fmt := ext_map.get(Path(filename).suffix.lower()):
            payload["output_format"] = fmt
            
    return payload


def call_openai(payload: Dict[str, object], api_base: str, api_path: str, api_key: str, cfg: Dict[str, str]):
    url = f"{api_base.rstrip('/')}/{api_path.lstrip('/')}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # Add organization and project headers if specified
    if org_id := cfg.get("openai_organization"):
        headers["OpenAI-Organization"] = org_id
    if project_id := cfg.get("openai_project"):
        headers["OpenAI-Project"] = project_id
    
    # Print API configuration
    print("\nAPI Request Configuration:")
    print("-" * 40)
    print(f"URL: {url}")
    print("Headers:")
    for key, value in headers.items():
        if key == "Authorization":
            print(f"  {key}: Bearer [REDACTED]")
        else:
            print(f"  {key}: {value}")
    print("\nPayload:")
    for key, value in payload.items():
        print(f"  {key}: {value}")
    print("-" * 40)
    
    while True:
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=120)
            
            # Print API response headers
            print("\nAPI Response Headers:")
            print("-" * 40)
            
            # API meta information
            print("API Meta Information:")
            for header in ["openai-organization", "openai-processing-ms", "openai-version", "x-request-id"]:
                if value := r.headers.get(header):
                    print(f"  {header}: {value}")
            
            # Rate limiting information - only show if we have rate limit headers
            rate_limit_headers = [
                "x-ratelimit-limit-requests",
                "x-ratelimit-limit-tokens",
                "x-ratelimit-remaining-requests",
                "x-ratelimit-remaining-tokens",
                "x-ratelimit-reset-requests",
                "x-ratelimit-reset-tokens"
            ]
            
            has_rate_limits = any(r.headers.get(h) for h in rate_limit_headers)
            if has_rate_limits:
                print("\nRate Limiting Information:")
                for header in rate_limit_headers:
                    if value := r.headers.get(header):
                        print(f"  {header}: {value}")
            
            # Print all headers in verbose mode
            if cfg.get("verbose"):
                print("\nAll Response Headers:")
                for header, value in r.headers.items():
                    print(f"  {header}: {value}")
            
            print("-" * 40)
            
            # Check rate limits
            remaining_requests = r.headers.get('x-ratelimit-remaining-requests')
            reset_requests = r.headers.get('x-ratelimit-reset-requests')
            
            if remaining_requests == '0' and reset_requests:
                reset_time = int(reset_requests)
                wait_time = max(0, reset_time - int(time.time()))
                if wait_time > 0:
                    print(f"Rate limit reached. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
            
            # Try to get detailed error information
            if not r.ok:
                error_data = r.json() if r.headers.get('content-type', '').startswith('application/json') else None
                error_msg = f"API Error: {r.status_code} {r.reason}"
                if error_data:
                    error_msg += f"\nDetails: {error_data}"
                raise requests.exceptions.HTTPError(error_msg)
                
            return r.json()
            
        except requests.exceptions.RequestException as e:
            if isinstance(e, requests.exceptions.HTTPError):
                raise  # Re-raise HTTP errors with our enhanced error message
            raise requests.exceptions.RequestException(f"Request failed: {str(e)}")


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
    # Convert spec path to absolute path
    spec = spec.resolve()
    
    # If outdir is relative, make it relative to the spec file's directory
    if not outdir.is_absolute():
        outdir = spec.parent / outdir
    
    preamble, assets, cfg_file, total_assets = parse_spec(spec)
    
    # Count how many assets need to be generated
    assets_to_generate = sum(1 for filename, _ in assets if not (outdir / filename).exists())
    print(f"Found {assets_to_generate} assets to generate (out of {total_assets} total)")

    # Map environment variables to config keys
    env_map = {
        "OPENAI_ORGANIZATION": "openai_organization",
        "OPENAI_PROJECT": "openai_project",
        "OPENAI_API_BASE": "api_base",
        "OPENAI_API_PATH": "api_path",
        "OPENAI_API_KEY": "api_key",
        "CONTINUE_ON_ERROR": "continue_on_error",
    }
    
    # Convert environment variables to config format
    env_cfg = {
        env_map[k]: v 
        for k, v in os.environ.items() 
        if k in env_map
    }
    
    # Add other allowed tags from environment
    env_cfg.update({
        k.lower(): v 
        for k, v in os.environ.items() 
        if k.lower() in ALLOWED_TAGS
    })
    
    cfg = {**cfg_file, **env_cfg, **cfg_cli}

    api_base = cfg.get("api_base", os.getenv("OPENAI_API_BASE", "https://api.openai.com"))
    api_path = cfg.get("api_path", os.getenv("OPENAI_API_PATH", "/v1/images/generations"))
    api_key = cfg.get("api_key", os.getenv("OPENAI_API_KEY"))
    if not api_key:
        sys.exit("OPENAI_API_KEY (or --api-key) not provided.")

    created = 0
    outdir.mkdir(parents=True, exist_ok=True)

    for filename, details in assets:
        if created >= limit:  # This is the count parameter for multiple requests
            break
        dest = outdir / filename
        if dest.exists():
            continue
        prompt = f"{preamble} {details}".strip()
        payload = build_payload(prompt, filename, cfg)
        try:
            rsp = call_openai(payload, api_base, api_path, api_key, cfg)
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
            # Handle continue_on_error for both string and boolean values
            continue_on_error = cfg.get("continue_on_error")
            if isinstance(continue_on_error, bool):
                should_continue = continue_on_error
            else:
                should_continue = str(continue_on_error).lower() in ("true", "1", "yes")
            if not should_continue:
                sys.exit(1)

    rem = sum(1 for f, _ in assets if not (outdir / f).exists())
    print(f"Created {created}; {rem} remaining; {total_assets} total.")

###############################################################################
# CLI (strict always)
###############################################################################

def parse_cli(argv=None):
    ap = argparse.ArgumentParser(description="Generate missing sprites from an asset spec.")
    ap.add_argument("spec", type=Path, help="Path to the spec file")
    ap.add_argument("-c", "--count", type=int, default=1, help="max images this run (default 1)")
    ap.add_argument("-o", "--output-dir", type=Path, default=Path("."), help="output directory (relative to spec file location)")
    ap.add_argument("--continue-on-error", action="store_true", help="continue processing on API errors")
    ap.add_argument("-v", "--verbose", action="store_true", help="show detailed API response information")
    
    # Add OpenAI API parameters with detailed help text
    ap.add_argument("--background", choices=["transparent", "opaque", "auto"], 
                   help="Set transparency for the background (gpt-image-1 only). Default: auto")
    ap.add_argument("--model", choices=["dall-e-2", "dall-e-3", "gpt-image-1"], 
                   help="The model to use for image generation. Default: dall-e-2")
    ap.add_argument("--moderation", choices=["low", "auto"], 
                   help="Content-moderation level for gpt-image-1. Default: auto")
    ap.add_argument("--output-compression", type=int, metavar="0-100", 
                   help="Compression level (0-100%%) for gpt-image-1 with webp/jpeg. Default: 100")
    ap.add_argument("--output-format", choices=["png", "jpeg", "webp"], 
                   help="Format for generated images (gpt-image-1 only). Default: png")
    ap.add_argument("--quality", choices=["auto", "high", "medium", "low", "hd", "standard"], 
                   help="Image quality. For gpt-image-1: auto/high/medium/low. For dall-e-3: hd/standard. For dall-e-2: standard only")
    ap.add_argument("--size", 
                   help="Image size. For gpt-image-1: 1024x1024/1536x1024/1024x1536/auto. For dall-e-2: 256x256/512x512/1024x1024. For dall-e-3: 1024x1024/1792x1024/1024x1792")
    ap.add_argument("--style", choices=["vivid", "natural"], 
                   help="Image style (dall-e-3 only). Default: vivid")
    
    # Add API configuration arguments
    ap.add_argument("--api-base", default="https://api.openai.com",
                   help="OpenAI API base URL (default: https://api.openai.com)")
    ap.add_argument("--api-path", default="/v1/images/generations",
                   help="OpenAI API path (default: /v1/images/generations)")
    ap.add_argument("--api-key", help="OpenAI API key")
    
    ns = ap.parse_args(argv)

    # Validate output-compression range
    if ns.output_compression is not None and not 0 <= ns.output_compression <= 100:
        ap.error("output-compression must be between 0 and 100")

    cli_cfg = {k: v for k, v in vars(ns).items() if v is not None and k in ALLOWED_TAGS | {"api_base", "api_path", "api_key"}}
    return ns, cli_cfg


def main(argv=None):
    ns, cfg_cli = parse_cli(argv)
    generate(ns.spec, ns.output_dir, ns.count, cfg_cli)


if __name__ == "__main__":
    main()
