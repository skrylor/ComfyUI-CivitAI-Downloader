# ComfyUI CivitAI Downloader

A CLI tool to download models from CivitAI and automatically organize them into your ComfyUI folder structure.

## Features

- **Smart Organization**: Automatically detects model types (Checkpoint, LoRA, VAE, etc.) and places them in the correct ComfyUI folders.
- **Installation Detection**: Visual indicators show if a model or specific file is already installed.
- **Smart Hash Verification**: Verifies existing files against CivitAI hashes to skip unnecessary downloads.
- **Interactive & Search**: Search for models by name or paste URLs/IDs directly.
- **Batch Processing**: Download multiple models via YAML configuration.
- **Resumable**: Supports resuming interrupted downloads.
- **Serverless Ready**: Configurable via Environment Variables or embedded YAML config.

## Smart File Management

The tool helps you manage your library efficiently:
- **Status Indicators**: Shows `[Installed]` or `[Partial]` next to versions and files you already have.
- **Duplicate Prevention**: If a file already exists, it calculates the SHA256 hash. If it matches the server's hash, the download is skipped automatically.
- **Update Checks**: If the hash doesn't match (e.g., you have an old version or corrupted file), it prompts you to overwrite.

## Smart Folder Organization

The tool automatically detects the model type and downloads it to the appropriate folder in your ComfyUI installation:

| Model Type | Target Folder |
|------------|---------------|
| Checkpoint | `models/checkpoints/` |
| LoRA / LoCon | `models/loras/` |
| VAE | `models/vae/` |
| ControlNet | `models/controlnet/` |
| Upscaler | `models/upscale_models/` |
| Embedding | `models/embeddings/` |
| Workflow | `models/workflows/` |

*Note: You can customize these paths in the batch configuration file.*

## Installation

Requires Python 3.6+.

```bash
git clone https://github.com/Skrylor/comfyui-civitai-downloader.git
cd comfyui-civitai-downloader
pip install -r requirements.txt
```

## Usage

### Interactive Mode
Run without arguments to search or enter URLs interactively:
```bash
python download.py
```

### CLI Mode
Download by URL or ID:
```bash
python download.py https://civitai.com/models/12345
python download.py 12345 --version "v1.0"
```

**Options:**
- `-o PATH`: Custom output path.
- `-t TOKEN`: CivitAI API token.
- `-f`: Force overwrite.
- `--batch-file FILE`: Run in batch mode.

### Batch & Automation

Create a `batch.yaml` file to define environment settings and a list of models. This is useful for restoring environments (e.g., Vast.ai).

```yaml
config:
  comfyui_path: /workspace/ComfyUI
  token: your_api_token
  model_paths:
    LORA: models/my_loras

models:
  - https://civitai.com/models/12345
  - id: 67890
    version: v1.0
  - id: 1656375
    file: workflow_KJ.zip  # Select specific file by name or ID
```

Run the batch:
```bash
python download.py --batch-file batch.yaml
```

### Configuration

The tool will prompt for your API Key and ComfyUI path on first run, saving them to `~/.comfyui-civitai/config.ini`.

**Environment Variables:**
Override config settings using `CIVITAI_API_TOKEN` and `COMFYUI_PATH`.

## License
[MIT](LICENSE)