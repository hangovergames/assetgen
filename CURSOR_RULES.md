# Cursor Rules for assetgen

This document outlines the key rules and patterns for working with the assetgen codebase in Cursor.

## 1. File Structure and Imports
```python
#!/usr/bin/env python3
from __future__ import annotations
import argparse, base64, os, re, sys, textwrap
from pathlib import Path
from typing import Dict, List, Tuple
```

## 2. Constants and Configuration
```python
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
```

## 3. Regex Patterns
```python
_PROMPT_RE = re.compile(r"^\s*PROMPT\s+(.+)$", re.IGNORECASE)
_ASSET_RE = re.compile(r"^\s*ASSET\s+(\S+)\s+(.+)$", re.IGNORECASE)
_CONFIG_RE = re.compile(r"^\s*([A-Z_]+)\s+(.+)$")
```

## 4. Key Functions and Their Rules

### a. Spec Parsing
- Must use strict parsing
- Each non-blank line must start with a whitelisted keyword
- Unknown keywords cause fatal errors
- Returns tuple of (global_prompt, assets, config)

### b. API Integration
- Handles both base64 and URL image responses
- Supports multiple OpenAI models (dall-e-2, dall-e-3, gpt-image-1)
- Configurable API base URL and path

### c. Generation Rules
- Skips existing files
- Creates companion .md files with prompts
- Supports batch processing with count limit
- Follows config precedence: CLI > ENV > spec file

## 5. Command Line Interface Rules
- Required argument: spec file path
- Optional arguments:
  - `-n/--count`: Max images per run (default: 1)
  - `-o/--output-dir`: Output directory (default: current directory)
  - Various `--<tag>` overrides for configuration

## 6. Error Handling Rules
- Fails fast on spec parsing errors
- Graceful handling of API errors
- Clear error messages for missing dependencies

## 7. Output Rules
- Creates image files in specified format (PNG/JPEG/WebP)
- Creates companion .md files with prompts
- Prints progress: "Created X; Y remaining; Z total"

## 8. Configuration Precedence
```
CLI flag > Environment variable > Spec file value > OpenAI default
```

## 9. File Naming Rules
- Asset filenames must not contain spaces
- Output files use original filename with appropriate extension
- Companion .md files use same base name

## 10. API Request Rules
- Timeout set to 120 seconds
- Proper headers for authentication
- JSON payload formatting
- Error handling for API responses

These rules ensure consistent behavior and reliable operation of the asset generation process. The code is designed to be strict and fail-fast to prevent ambiguous or incorrect asset generation. 