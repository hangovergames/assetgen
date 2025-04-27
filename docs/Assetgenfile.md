## `Assetgenfile` Format Documentation

### File Structure

- **Global Directives**
  All global settings (everything except `ASSET`) must appear before any `ASSET` entries.
- **Order Sensitivity**
  - You may include multiple `PROMPT` lines; each line will be concatenated in order to form the full prompt.
  - All other global directives (`MODEL`, `SIZE`, etc.) may appear only once.
- **Asset Directives**
  All `ASSET` lines must come after every global directive. Each one defines a filename and its specific prompt.

---

### Default Behaviors & Requirements

- **Required Directives**
  - At least one `ASSET` line is **mandatory**.
  - `PROMPT` lines are **optional** but strongly recommended—they establish shared context for all assets and help ensure reproducible results.

- **Syntax Validation**
  - Any directive not listed in this documentation will trigger a syntax error and abort processing.

- **Global Directive Defaults**
  If a global directive is omitted, it is simply not sent to the OpenAI API, and the API’s own default behavior applies. CLI defaults (when you do set them) are:

  | Directive            | Default Value        | Notes                                                                 |
  |----------------------|----------------------|-----------------------------------------------------------------------|
  | `MODEL`              | `dall-e-2`           |                                                                       |
  | `SIZE`               | *(API default)*      | DALL·E-2: `256x256`<br>gpt-image-1: `auto`                            |
  | `BACKGROUND`         | `auto`               | (gpt-image-1 only)                                                    |
  | `MODERATION`         | `auto`               | (gpt-image-1 only)                                                    |
  | `OUTPUT_COMPRESSION` | `100`                | (gpt-image-1 only; applies to JPEG/WEBP)                              |
  | `QUALITY`            | *(API default)*      | gpt-image-1: `auto`<br>dall-e-3: `hd`<br>dall-e-2: `standard`          |
  | `STYLE`              | `vivid`              | (dall-e-3 only)                                                       |

- **Reproducibility Best Practice**
  Where possible, explicitly specify each directive in your spec file so that future API-default changes won’t alter your generated assets.

---

### Asset-Specific Overrides

- **ASSET Directives**
  Each asset is declared with an `ASSET` line in the form:
  ```
  ASSET <filename> <asset-specific prompt>
  ```

- **Prompt Composition**
  - The effective prompt sent to the API is the concatenation of all global `PROMPT` lines (in order) followed by the asset-specific prompt text.

- **Filename Guidelines**
  - Filenames **must not** contain any whitespace characters.
  - The file extension (e.g. `.png`, `.jpeg`, `.webp`) is used to auto-detect the output format.

- **Error Handling**
  - Any `ASSET` line without a valid filename or prompt will trigger a syntax error.
  - Any filename containing whitespace or an unsupported extension will trigger a validation error.

---

### Directive Details

#### `MODEL`

Choose which OpenAI image-generation model to use.

- **Valid Values**: `dall-e-2`, `dall-e-3`, `gpt-image-1`
- **Recommendations**:
  - `gpt-image-1` for highest quality (most expensive)
  - `dall-e-3` for strong balance of quality & cost
  - `dall-e-2` for basic assets or cost-sensitive needs
- **Model-Specific Constraints**:
  - **Size**
    - DALL·E-2: `256x256`, `512x512`, `1024x1024`
    - DALL·E-3: `1024x1024`, `1792x1024`, `1024x1792`
    - GPT-Image-1: `1024x1024`, `1536x1024`, `1024x1536`, `auto`
  - **Quality**
    - DALL·E-2: `standard`
    - DALL·E-3: `hd`, `standard`
    - GPT-Image-1: `auto`, `high`, `medium`, `low`
  - **Style**: only for DALL·E-3 (`vivid`, `natural`)
  - **Background/Moderation/Compression**: only for GPT-Image-1

#### `SIZE`

Specifies image dimensions (maps to the API’s `size` parameter).

- **Valid Values** (by model):
  - DALL·E-2: `256x256`, `512x512`, `1024x1024`
  - DALL·E-3: `1024x1024`, `1792x1024`, `1024x1792`
  - GPT-Image-1: `1024x1024`, `1536x1024`, `1024x1536`, `auto`
- **Notes**:
  - Omitted → API default (`256x256` for DALL·E-2)
  - `auto` (GPT-Image-1) lets the API choose

#### `BACKGROUND`

Controls transparency (GPT-Image-1 only).

- **Valid Values**: `transparent`, `opaque`, `auto`
- **Notes**:
  - Omitted → `auto`
  - Use `transparent` for compositing, `opaque` for full scenes

#### `MODERATION`

Sets content moderation level (GPT-Image-1 only).

- **Valid Values**: `low`, `auto`
- **Notes**:
  - Omitted → `auto`
  - `low` for benign game assets, `auto` for general safety

#### `OUTPUT_COMPRESSION`

JPEG/WEBP compression level (GPT-Image-1 only).

- **Valid Values**: `0`–`100`
- **Notes**:
  - Omitted → `100`
  - Lower → smaller size, lower fidelity

#### `QUALITY`

Rendering fidelity.

- **Valid Values**:
  - DALL·E-2: `standard`
  - DALL·E-3: `hd`, `standard`
  - GPT-Image-1: `auto`, `high`, `medium`, `low`
- **Notes**:
  - Omitted → API default
  - Higher → better detail, higher cost

#### `STYLE`

Stylistic bias (DALL·E-3 only).

- **Valid Values**: `vivid`, `natural`
- **Notes**:
  - Omitted → `vivid`
  - `vivid` for cartoons, `natural` for realism

---

### Example Spec

```text
PROMPT A clean top-down 2-D sprite on a transparent background.
PROMPT Include subtle shadows for depth.
MODEL gpt-image-1
SIZE 1024x1024
BACKGROUND transparent
MODERATION low
OUTPUT_COMPRESSION 80
QUALITY high

ASSET road_straight_ns.png A seamless 256×256 asphalt road segment running north–south.
ASSET tree.png A stylized pine tree with dark green needles.
ASSET icon.webp A glowing energy orb with electric sparks.
```
