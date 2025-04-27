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
MODEL gpt-image-1
SIZE 1024x1024
BACKGROUND transparent
ASSET road_straight_ns.png A seamless 256×256 asphalt road …
ASSET road_corner_ne.png  A 256×256 90‑degree bend …
```

Then run:

```bash
assetgen Assetgenfile
```

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
- `OPENAI_API_PATH`: API path (default: /v1/images/generations)

### Spec File Format

Each line (ignoring leading whitespace) must begin with one of these tokens (case-insensitive):

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

## License

MIT License - see LICENSE file for details
