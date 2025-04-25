# assetgen

**assetgen** is a lightweight command‑line helper that converts a plain‑text specification file into a complete set of game sprites using the OpenAI Images API.

---

*GitHub ·* <https://github.com/hangovergames/assetgen>  
*License ·* MIT

---

## ⭐️ Features

* **Spec‑driven:** Write one human‑readable spec and let assetgen create every missing PNG, JPEG, or WebP.
* **Prompt prefix:** One or more `PROMPT` lines define a global style guide automatically prepended to every asset prompt.
* **Batch‑safe:** Generate up to *N* new assets per run; already‑generated files are skipped.
* **Self‑documenting:** Alongside each image, assetgen stores a sibling **`.md`** file containing the exact prompt used.
* **Fail‑fast spec parser:** The grammar is strict; unknown or malformed lines halt with a clear error.
* **Override anywhere:** Config options can come from the spec, environment variables, or CLI flags—CLI always wins.

---

## 🏃‍ Quick start

```bash
# 1 · Install (Python 3.9+) and deps
pip install -r requirements.txt   # only 'requests' for now

# 2 · Export your OpenAI key
export OPENAI_API_KEY="sk‑…"

# 3 · Generate a single missing sprite from your spec
python asset_generator.py assets.spec

# 4 · Create three at a time, swapping the model on the fly
python asset_generator.py assets.spec -n 3 --model gpt-image-1
```

Each run prints progress, e.g.:

```
✓ road_straight_ns.png
✓ building_gas_station.png
Created 2; 27 remaining; 29 total.
```

---

## 📑 Spec file grammar (v2)

Every non‑blank line **must** start with one of these keywords (case‑insensitive):

```
PROMPT <text …>                  # global prefix; can appear multiple times
ASSET  <filename> <prompt …>     # no spaces in filename

# One per line config tags (all optional)
MODEL              <dall-e-2|dall-e-3|gpt-image-1>
BACKGROUND         <transparent|opaque|auto>
MODERATION         <low|auto>
OUTPUT_COMPRESSION <0‑100>
QUALITY            <auto|high|medium|low|hd|standard>
SIZE               <WxH|auto>
STYLE              <vivid|natural>
USER               <identifier>
```

Any unknown word or malformed line aborts parsing.

Example:

```text
PROMPT Render a clean top‑down sprite on transparency.
MODEL gpt-image-1
SIZE 1024x1024
BACKGROUND transparent

ASSET road_straight_ns.png A seamless north–south asphalt stretch …
ASSET road_corner_ne.png  A 256×256 90° bend …
```

---

## 🛠 Command‑line options

| Option | Default | Description |
|--------|---------|-------------|
| `spec` | — | Path to the `.spec` file |
| `-n`, `--count` | `1` | Max images to create this run |
| `-o`, `--output-dir` | `.` | Where to write images + prompts |
| Any `--<tag>` override | — | Override a config tag (`--model`, `--size`, …) |
| `--api-base` | `https://api.openai.com` | Point at a different base URL |
| `--api-path` | `/v1/images/generations` | Endpoint path |
| `--api-key` | — | Overrides `OPENAI_API_KEY` |

---

## 🔄 Config precedence

```
CLI flag   >   Environment variable   >   Spec file value   >   OpenAI default
```

Environment variables mirror tag names (`MODEL`, `SIZE`, …). Unknown env vars are ignored.

---

## 📦 Installation

```bash
# Clone
git clone https://github.com/hangovergames/assetgen.git
cd assetgen

# Install deps
pip install -r requirements.txt

# (Optional) add to PATH
chmod +x asset_generator.py
ln -s "$PWD/asset_generator.py" ~/.local/bin/assetgen
```

---

## 🗺 Roadmap

- 🌐 Parallel generation to speed big batches
- 🚦 Automatic alpha‑edge consistency checks
- 🔌 Pluggable back‑ends (e.g., local Stable Diffusion)
- 📄 Alternative spec formats (CSV / JSON)

Pull requests and issues are very welcome.

---

## 📝 License

assetgen is released under the **MIT License**—see [`LICENSE`](LICENSE) for details.
