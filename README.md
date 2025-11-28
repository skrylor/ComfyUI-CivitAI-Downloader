# ComfyUI CivitAI Downloader

A command line tool that downloads models from CivitAI and organizes them into the correct ComfyUI folders automatically. It works in interactive mode, normal CLI mode, and batch mode.

## Features

* **Smart organization**: Detects model types (Checkpoint, LoRA, VAE, ControlNet, etc.) and places files in the right ComfyUI subfolders.
* **Installation detection**: Shows whether a model or a specific file is already present.
* **Hash verification**: If a file exists locally, its SHA256 hash is compared with the CivitAI hash. Matching files are skipped to avoid re downloading.
* **Interactive search**: Search by model name or paste a CivitAI URL or ID.
* **Batch downloads**: Download multiple models using a YAML file.
* **Resumable downloads**: Interrupted downloads can continue.
* **Configurable for cloud setups**: Supports Environment Variables or a YAML config, so you can restore a workspace quickly.

## How file handling works

* **Status indicators**: Versions or files you already have are marked as `[Installed]`. If some files from a version exist but others are missing, it shows `[Partial]`.
* **Duplicate prevention**: Existing files are hashed. If the hash matches CivitAI, the download is skipped.
* **Update and corruption handling**: If the hash does not match, you will be asked whether to overwrite the local file.

## Project files

* **`download.py`**: Main script. Required.
* **`requirements.txt`**: Python dependencies. Required.
* **`config.ini`**: Optional local config for your token and ComfyUI path.

  * Created on first run at `~/.comfyui-civitai/config.ini`.
  * You can avoid using this file by setting Environment Variables instead.
* **`batch.yaml`** (any filename is fine): Optional batch configuration.

  * Recommended for serverless or cloud machines where you want reproducible setups.

## Folder organization

Detected model types are stored here by default:

| Model type     | Target folder            |
| -------------- | ------------------------ |
| Checkpoint     | `models/checkpoints/`    |
| LoRA and LoCon | `models/loras/`          |
| VAE            | `models/vae/`            |
| ControlNet     | `models/controlnet/`     |
| Upscaler       | `models/upscale_models/` |
| Embedding      | `models/embeddings/`     |
| Workflow       | `models/workflows/`      |

You can override these paths in your batch YAML.

## Installation and quick start

Requires Python 3.10 or newer.

1. **Clone the repository**

   ```bash
   git clone https://github.com/Skrylor/comfyui-civitai-downloader.git
   cd comfyui-civitai-downloader
   ```

2. **Choose one way to start**

   **Option A, use the starter script (recommended)**
   These scripts check for Python and install dependencies automatically if needed.

   * **Windows**

     ```bash
     start.bat
     ```

     (You can also double click `start.bat`.)

   * **Linux or Mac**

     ```bash
     ./start.sh
     ```

   **Option B, install and run manually**

   ```bash
   pip install -r requirements.txt
   python download.py
   ```

## Usage

### Interactive mode

Run with no arguments to search or paste URLs interactively.

```bash
# Windows
start.bat

# Linux or Mac
./start.sh

# Manual
python download.py
```

### CLI mode

Download a model by URL or ID.

```bash
python download.py https://civitai.com/models/12345
python download.py 12345 --version "v1.0"
```

**Options**

* `-o PATH`
  Custom output folder. If omitted, the ComfyUI path plus the detected model folder is used.

* `-t TOKEN`
  CivitAI API token. Overrides config and environment values.

* `-f`
  Force overwrite without prompting.

* `--batch-file FILE`
  Run batch mode using the given YAML file.

### Batch mode

Create a YAML file that defines your ComfyUI path, token, optional custom target folders, and the list of models to download.

```yaml
config:
  comfyui_path: /workspace/ComfyUI
  token: your_api_token
  model_paths:
    LORA: models/my_loras  # optional override

models:
  - https://civitai.com/models/12345
  - id: 67890
    version: v1.0
  - id: 1656375
    file: workflow_KJ.zip  # download a specific file by name or file ID
```

Run it with:

```bash
python download.py --batch-file batch.yaml
```

### Serverless or cloud workflow (Vast.ai, RunPod, Colab)

Use batch mode plus environment variables for quick, repeatable setups.

1. **Create `models.yaml`**

   ```yaml
   config:
     comfyui_path: /workspace/ComfyUI
   models:
     - 12345
     - https://civitai.com/models/67890
   ```

2. **Upload and run**

   ```bash
   export CIVITAI_API_TOKEN="your_token"

   pip install -r requirements.txt
   python download.py --batch-file models.yaml
   ```

The tool checks hashes first and only downloads files that are missing or different.

## Configuration

On first run, the tool asks for:

* your CivitAI API token
* your ComfyUI installation path

They are saved to `~/.comfyui-civitai/config.ini`.

### Environment Variables

You can override the config file with:

* `CIVITAI_API_TOKEN`
* `COMFYUI_PATH`

These take priority over `config.ini` unless you pass flags like `-t` explicitly.

## License

MIT. See `LICENSE`.
