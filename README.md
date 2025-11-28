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

## Configuration & Files

This tool is designed to be flexible. Here's what you need to know about the files:

- **`download.py`**: The main script. **Required**.
- **`requirements.txt`**: List of dependencies. **Required** for installation.
- **`config.ini`**: Stores your API key and ComfyUI path. **Optional**.
    - Automatically created in your home directory (`~/.comfyui-civitai/`) on first run.
    - You can skip this by using Environment Variables (`CIVITAI_API_TOKEN`, `COMFYUI_PATH`) or a batch file.
- **`batch.yaml`** (or any name): Your list of models to download. **Optional**.
    - Highly recommended for serverless/cloud setups to define your environment.

## Serverless / Vast.ai Workflow

This tool is perfect for ephemeral environments like Vast.ai, RunPod, or Google Colab where you need to set up your workspace quickly.

1.  **Prepare your `models.yaml`**:
    Create a YAML file with all your favorite models (see `example_config.yaml`).
    ```yaml
    config:
      comfyui_path: /workspace/ComfyUI
    models:
      - 12345 # Model ID
      - https://civitai.com/models/67890
    ```

2.  **Upload & Run**:
    Upload the script and your yaml file, then run:
    ```bash
    # Set token (securely)
    export CIVITAI_API_TOKEN="your_token"
    
    # Install & Restore
    pip install -r requirements.txt
    python download.py --batch-file models.yaml
    ```

    *The tool will check hashes and only download files that are missing or changed.*

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

## Installation & Quick Start

Requires Python 3.10+.

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/Skrylor/comfyui-civitai-downloader.git
    cd comfyui-civitai-downloader
    ```

2.  **Run the starter script**:
    *   **Windows**: Double-click `start.bat` or run `start.bat` in terminal.
    *   **Linux/Mac**: Run `./start.sh`.

    *These scripts will automatically check for Python and install required dependencies (`requirements.txt`) if missing.*

    Alternatively, you can install manually:
    ```bash
    pip install -r requirements.txt
    python download.py
    ```

## Usage

### Interactive Mode
Run without arguments to search or enter URLs interactively:
```bash
# Windows
start.bat

# Linux/Mac
./start.sh

# Manual
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