# Hangover Games Asset Generator

A command-line tool for generating game graphics using OpenAI's image generation APIs.

## Installation

### Option 1: Clone from Repository
```bash
# Clone the repository
git clone https://github.com/hangovergames/assetgen.git
cd assetgen

# Initialize and update the assets submodule
git submodule init
git submodule update
```

### Option 2: Install via pip
```bash
pip install hangovergames-assetgen
```

## Usage

Create [a spec file (e.g., `Assetgenfile`)](https://hangovergames.github.io/assetgen/Assetgenfile) with your image generation instructions:

```text
PROMPT Create a clean top‑down 2‑D sprite on a transparent background.
MODEL gpt-5.2
SIZE 1024x1024
BACKGROUND transparent
ASSET road_straight_ns.png A seamless 256×256 asphalt road …
ASSET road_corner_ne.png  A 256×256 90‑degree bend …
```

Then run:

```bash
assetgen Assetgenfile
```

Note: `--output-dir` is interpreted relative to the spec file location. For example, if your spec is
`assets/gpt52_sample/Assetgenfile` and you want output under that folder, pass `-o out` (not `-o assets/gpt52_sample/out`).

### Command Line Options

- `-c, --count`: Maximum number of images to generate this run (default: 1)
- `-o, --output-dir`: Output directory (relative to spec file location)
- `--continue-on-error`: Continue processing on API errors
- `-v, --verbose`: Show detailed API response information

### API Configuration

You can configure the API using environment variables:

- `OPENAI_API_KEY`: Your OpenAI API key (required)
- `OPENAI_ORGANIZATION`: Your OpenAI organization ID
- `OPENAI_PROJECT`: Your OpenAI project ID
- `OPENAI_API_BASE`: API base URL (default: https://api.openai.com)
- `OPENAI_API_PATH`: API path (default depends on model: `/v1/images/generations` for images models, `/v1/responses` for GPT‑5.2 image tool)

This tool also supports loading a local `.env` file (via `python-dotenv`) so you can
store `OPENAI_API_KEY=...` without exporting it in your shell.

### Spec File Format

Each line (ignoring leading whitespace) must begin with one of these tokens (case-insensitive):

```
PROMPT <text …>
ASSET  <filename> <asset‑specific prompt>
MODEL  <dall-e-2|dall-e-3|gpt-image-1>
MODEL  <gpt-5.2>  (image generation via Responses API tool)
BACKGROUND <transparent|opaque|auto>
MODERATION <low|auto>
OUTPUT_COMPRESSION <0‑100>
OUTPUT_FORMAT <png|jpeg|webp>
QUALITY <auto|high|medium|low|hd|standard>
SIZE <WxH|auto>
STYLE <vivid|natural>
USER <identifier>
```

## License

MIT License - see LICENSE file for details
