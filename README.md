# ComfyUI CivitAI Model Downloader

[![GitHub license](https://img.shields.io/github/license/Skrylor/comfyui-civitai-downloader)](https://github.com/Skrylor/comfyui-civitai-downloader/blob/main/LICENSE)

An interactive command-line tool to easily download models from CivitAI and automatically organize them in your ComfyUI folders structure.


## Features

-  **Interactive Mode**: Browse and select versions and files through a friendly CLI
-  **Automatic Organization**: Places models in the correct ComfyUI folders based on model type
-  **Smart Model Type Detection**: Automatically detects model types (Checkpoint, LORA, VAE, etc.)
-  **Version Management**: Lists all versions of a model for you to choose from
-  **Multiple File Support**: Handles models with multiple file options
-  **Resumable Downloads**: Can resume interrupted downloads where possible

## Installation

### Prerequisites
- Python 3.6 or higher
- A CivitAI account and API key ([Get one here](https://civitai.com/user/account))
- A ComfyUI installation

### Quick Install

1. Clone this repository:
   ```bash
   git clone https://github.com/Skrylor/comfyui-civitai-downloader.git
   cd comfyui-civitai-downloader
   ```

2. Make the scripts executable:
   ```bash
   chmod +x download.py
   chmod +x download_model.sh
   ```

3. Run the script for the first time to set up configuration:
   ```bash
   ./download.py
   ```
   You'll be prompted to enter your CivitAI API key and ComfyUI path.

## Usage

### Interactive Mode (Recommended)

Simply run:
```bash
./download.py
```

This will start the interactive mode where you can paste a CivitAI model URL or ID and follow the prompts.

### Command Line Options

```bash
./download.py [URL or ID] [options]
```

For example:
```bash
./download.py https://civitai.com/models/140272/hassaku-xl-illustrious
```

Or using just the model ID:
```bash
./download.py 140272
```

### Options

```
-o, --output_path PATH   Custom output path
-t, --token TOKEN        CivitAI API token (overrides config file)
-f, --force              Force download even if file exists
--model_type TYPE        Manually specify model type
-i, --interactive        Interactive mode
-v, --version VERSION    Specify version to download (e.g., "v2.2" or "latest")
--reset-config           Reset configuration (API key and ComfyUI path)
```

### Shell Script Shortcut

For even quicker usage, a shell script is provided:
```bash
./download_model.sh https://civitai.com/models/140272
```

## Configuration

On first run, the script will ask for:
1. Your CivitAI API key
2. The path to your ComfyUI installation

These settings are stored in `~/.comfyui-civitai/config.ini` and can be edited manually or reset using:
```bash
./download.py --reset-config
```

## Model Type Detection

The script automatically detects what type of model you're downloading (Checkpoint, LORA, VAE, etc.) and places it in the appropriate folder within your ComfyUI installation.

Supported model types:
- Checkpoints → `models/checkpoints/`
- LORAs → `models/loras/`
- Controlnet → `models/controlnet/`
- VAEs → `models/vae/`
- Upscalers → `models/upscale_models/`
- Embeddings → `models/embeddings/`
- And more!

## Examples

### Download a specific version of a model:
```bash
./download.py https://civitai.com/models/140272 -v "v2.2"
```

### Force redownload of a model:
```bash
./download.py 140272 -f
```

### Specify a custom output path:
```bash
./download.py 140272 -o /path/to/custom/folder
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Author

Created by [Skrylor](https://github.com/skrylor)

---

⭐ If you find this tool useful, please star the repository! ⭐ 
