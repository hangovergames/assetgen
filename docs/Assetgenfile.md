### Default Behaviors & Requirements for Assetgenfile

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
  | `OUTPUT_FORMAT`      | `png`                | (gpt-image-1 only)                                                    |
  | `QUALITY`            | *(API default)*      | gpt-image-1: `auto`<br>dall-e-3: `hd`<br>dall-e-2: `standard`          |
  | `STYLE`              | `vivid`              | (dall-e-3 only)                                                       |
  | `USER`               | *(none)*             | No user identifier will be sent if omitted.                           |

- **Reproducibility Best Practice**
  Where possible, explicitly specify each directive in your spec file so that future API-default changes won’t alter your generated assets.

