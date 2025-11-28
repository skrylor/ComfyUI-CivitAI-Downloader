#!/usr/bin/env python3
import os.path
import sys
import argparse
import time
import urllib.request
import urllib.error
import json
import re
import signal
import hashlib
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote, quote
import configparser
try:
    import yaml
except ImportError:
    yaml = None

try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn, TransferSpeedColumn
    from rich.table import Table
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich import print as rprint
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    # Fallback for basic console if rich is not available (though requirements should ensure it is)
    class Console:
        def print(self, *args, **kwargs):
            print(*args)
        def rule(self, *args, **kwargs):
            print("-" * 50)

console = Console()

CHUNK_SIZE = 1638400
CONFIG_DIR = Path.home() / '.comfyui-civitai'
CONFIG_FILE = CONFIG_DIR / 'config.ini'
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'

# Model type to folder mapping for ComfyUI
MODEL_FOLDERS = {
    'Checkpoint': 'models/checkpoints',
    'LORA': 'models/loras',
    'LoCon': 'models/loras',
    'Controlnet': 'models/controlnet',
    'Upscaler': 'models/upscale_models',
    'VAE': 'models/vae',
    'TextualInversion': 'models/embeddings',
    'Hypernetwork': 'models/hypernetworks',
    'AestheticGradient': 'models/classifiers',
    'Poses': 'poses',
    'Wildcards': 'wildcards',
    'Workflows': 'workflows',
    'MotionModule': 'models/motion_module',
    'Other': 'models/other'
}

def calculate_sha256(file_path):
    """Calculate SHA256 hash of a file"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest().upper()

def create_config_if_not_exists():
    """Creates a config file if it doesn't exist, asking for API key and ComfyUI path"""
    if CONFIG_FILE.exists():
        return
    
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    config = configparser.ConfigParser()
    config['DEFAULT'] = {
        'api_key': '',
        'comfyui_path': ''
    }
    
    console.print(Panel.fit("[bold blue]First-time configuration for ComfyUI CivitAI Downloader[/bold blue]", border_style="blue"))
    
    # Get API key
    console.print("\n[bold yellow]You'll need a CivitAI API key to download models.[/bold yellow]")
    console.print("Get one at: [link=https://civitai.com/user/account]https://civitai.com/user/account[/link]")
    
    while True:
        api_key = Prompt.ask("\nEnter your CivitAI API key").strip()
        if not api_key:
            console.print("[red]API key cannot be empty. Please try again.[/red]")
            continue
        
        # Validate the API key by making a test request
        if validate_api_key(api_key):
            config['DEFAULT']['api_key'] = api_key
            break
        else:
            console.print("[red]Invalid API key. Please check and try again.[/red]")
    
    # Get ComfyUI path
    console.print("\n[bold yellow]Now, let's set up the path to your ComfyUI installation.[/bold yellow]")
    console.print("This is where models will be downloaded.")
    
    while True:
        default_path = str(Path.home() / 'ComfyUI')
        comfyui_path = Prompt.ask(f"\nEnter your ComfyUI path", default=default_path).strip()
        
        comfyui_path = os.path.expanduser(comfyui_path)
        
        # Validate the ComfyUI path
        if validate_comfyui_path(comfyui_path):
            config['DEFAULT']['comfyui_path'] = comfyui_path
            break
        else:
            if not Confirm.ask("[red]Invalid ComfyUI path. Would you like to try again?[/red]"):
                console.print("Using the path anyway. You can change it later in the config file.")
                config['DEFAULT']['comfyui_path'] = comfyui_path
                break
    
    # Save the config
    with open(CONFIG_FILE, 'w') as f:
        config.write(f)
    
    console.print("\n[bold green]Configuration saved successfully![/bold green]")
    console.print(f"Config file: [cyan]{CONFIG_FILE}[/cyan]")
    console.print("You can edit this file manually if needed.\n")


def validate_api_key(api_key):
    """Validates the API key by making a test request"""
    if not api_key:
        return False
    
    try:
        headers = {
            'Authorization': f'Bearer {api_key}',
            'User-Agent': USER_AGENT,
        }
        
        # Make a simple request to check if the API key is valid
        url = "https://civitai.com/api/v1/models?limit=1"
        request = urllib.request.Request(url, headers=headers)
        
        with urllib.request.urlopen(request) as response:
            if response.getcode() == 200:
                return True
            else:
                return False
    except Exception as e:
        print(f"Error validating API key: {e}")
        return False


def validate_comfyui_path(path):
    """Validates if the given path is a ComfyUI installation"""
    comfyui_path = Path(path)
    
    # Check if the path exists
    if not comfyui_path.exists():
        console.print(f"[yellow]Path does not exist: {path}[/yellow]")
        if Confirm.ask("Would you like to create this directory?"):
            try:
                os.makedirs(path, exist_ok=True)
                return True
            except Exception as e:
                console.print(f"[red]Error creating directory: {e}[/red]")
                return False
        return False
    
    # Check if it's a directory
    if not comfyui_path.is_dir():
        console.print(f"[red]Path is not a directory: {path}[/red]")
        return False
    
    # Check for some common ComfyUI files/directories
    # This is a heuristic check, not a strict validation
    comfyui_markers = [
        'main.py',
        'models',
        'web',
        'comfy'
    ]
    
    found_markers = [marker for marker in comfyui_markers if (comfyui_path / marker).exists()]
    
    if found_markers:
        return True
    else:
        console.print(f"[yellow]This doesn't appear to be a ComfyUI installation.[/yellow]")
        console.print("Missing expected files/directories like: main.py, models/, web/, comfy/")
        return False


def get_config():
    """Gets the configuration from the config file, creating it if it doesn't exist"""
    create_config_if_not_exists()
    
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    
    return config['DEFAULT']


# Handle SIGINT (Ctrl+C) gracefully
def signal_handler(sig, frame):
    print("\nDownload canceled. Exiting...")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)


def get_args():
    parser = argparse.ArgumentParser(
        description='Enhanced CivitAI Downloader for ComfyUI',
    )

    parser.add_argument(
        'url',
        type=str,
        nargs='?',
        help='CivitAI Download URL or Model ID/URL, eg: https://civitai.com/api/download/models/46846 or 46846 or https://civitai.com/models/12345'
    )

    parser.add_argument(
        '-o', '--output_path',
        type=str,
        help='Custom output path (by default uses model type detection for ComfyUI folders)'
    )
    
    parser.add_argument(
        '-t', '--token',
        type=str,
        help='CivitAI API token (overrides config file)'
    )
    
    parser.add_argument(
        '-f', '--force',
        action='store_true',
        help='Force download even if file exists'
    )
    
    parser.add_argument(
        '--model_type',
        type=str,
        choices=list(MODEL_FOLDERS.keys()),
        help='Manually specify model type if auto-detection fails'
    )
    
    parser.add_argument(
        '-i', '--interactive',
        action='store_true',
        help='Interactive mode (default if no URL provided)'
    )
    
    parser.add_argument(
        '-v', '--version',
        type=str,
        help='Specify version to download (e.g., "v2.2" or "latest")'
    )
    
    parser.add_argument(
        '--reset-config',
        action='store_true',
        help='Reset configuration (API key and ComfyUI path)'
    )

    parser.add_argument(
        '--batch-file',
        type=str,
        help='Path to YAML config file for batch downloading'
    )

    return parser.parse_args()


def get_token():
    """Get API token from config file"""
    config = get_config()
    return config.get('api_key', '')


def get_comfyui_path():
    """Get ComfyUI path from config file"""
    config = get_config()
    return config.get('comfyui_path', str(Path.home() / 'ComfyUI'))


def prompt_for_civitai_token():
    """Prompt for API token and save to config"""
    console.print("\n[yellow]Your CivitAI API token is not set or is invalid.[/yellow]")
    api_key = Prompt.ask('Please enter your CivitAI API token').strip()
    
    if validate_api_key(api_key):
        # Update the config file
        config = configparser.ConfigParser()
        if os.path.exists(CONFIG_FILE):
            config.read(CONFIG_FILE)
        
        if 'DEFAULT' not in config:
            config['DEFAULT'] = {}
        
        config['DEFAULT']['api_key'] = api_key
        
        with open(CONFIG_FILE, 'w') as f:
            config.write(f)
        
        return api_key
    else:
        console.print("[red]Invalid API key. Please check and try again.[/red]")
        return None


def get_file_extension(filename):
    return os.path.splitext(filename)[1].lower()


def detect_model_type(filename, metadata=None):
    """Detect model type based on filename and extension"""
    extension = get_file_extension(filename)
    
    # Try to detect from metadata if provided
    if metadata and 'type' in metadata:
        model_type = metadata['type']
        if model_type in MODEL_FOLDERS:
            return model_type
    
    # Detect based on file extension and name patterns
    if filename.lower().endswith('.vae.pt') or filename.lower().endswith('.vae.safetensors'):
        return 'VAE'
    
    if extension == '.safetensors' or extension == '.ckpt':
        if 'lora' in filename.lower():
            return 'LORA'
        elif 'locon' in filename.lower():
            return 'LoCon'
        elif 'vae' in filename.lower():
            return 'VAE'
        elif 'control' in filename.lower():
            return 'Controlnet'
        else:
            return 'Checkpoint'
    elif extension == '.pt' or extension == '.pth':
        if 'upscale' in filename.lower() or 'esrgan' in filename.lower():
            return 'Upscaler'
        elif 'vae' in filename.lower():
             return 'VAE'
        else:
            return 'Other'
    elif extension == '.bin':
        return 'Embedding'
    elif extension == '.json' and 'workflow' in filename.lower():
        return 'Workflows'
    elif extension == '.pose' or extension == '.json' and 'pose' in filename.lower():
        return 'Poses'
    
    # Default fallback
    return 'Other'


def get_model_folder(model_type):
    """Get the appropriate folder for the model type"""
    return MODEL_FOLDERS.get(model_type, MODEL_FOLDERS['Other'])


def extract_model_id(url):
    """Extract model ID from a CivitAI URL"""
    # Handle direct download URLs
    if 'civitai.com/api/download/models/' in url:
        model_id = url.split('models/')[1].split('?')[0].split('/')[0]
        return model_id
    
    # Handle regular model page URLs
    match = re.search(r'civitai\.com/models/(\d+)', url)
    if match:
        return match.group(1)
    
    # Handle model version URLs
    match = re.search(r'civitai\.com/models/\d+/[^/]+/(\d+)', url)
    if match:
        return match.group(1)
    
    # If it's just a number, assume it's the model ID
    if url.isdigit():
        return url
    
    return None


def search_models(query, token):
    """Search for models on CivitAI"""
    try:
        headers = {
            'User-Agent': USER_AGENT,
        }
        if token:
            headers['Authorization'] = f'Bearer {token}'
            
        encoded_query = quote(query)
        url = f"https://civitai.com/api/v1/models?query={encoded_query}&limit=10&sort=Most%20Downloaded"
        
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request) as response:
            data = json.loads(response.read().decode())
            return data.get('items', [])
    except Exception as e:
        console.print(f"[red]Error searching models: {e}[/red]")
        return []


def get_model_info(model_id, token):
    """Fetch model info from CivitAI API"""
    try:
        headers = {
            'Authorization': f'Bearer {token}',
            'User-Agent': USER_AGENT,
        }
        
        url = f"https://civitai.com/api/v1/models/{model_id}"
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request) as response:
            data = json.loads(response.read().decode())
            return data
    except Exception as e:
        print(f"Warning: Could not fetch model info: {e}")
        return None


def check_generation_only(version):
    """Check if a version is likely generation-only"""
    description = version.get('description', '').lower()
    if 'generation only' in description or 'not available for download' in description:
        return True
    
    # Check files - if only training data is available for a checkpoint
    files = version.get('files', [])
    if files:
        # If all files are Training Data or very small (placeholder)
        all_training_data = all(f.get('type') == 'Training Data' for f in files)
        if all_training_data:
            return True
            
    return False

def check_generation_only(version):
    """Check if a version is likely Generation-Only"""
    # Check description for keywords
    description = version.get('description', '')
    if description and ('generation only' in description.lower() or 'not available for download' in description.lower()):
        return True
        
    # Check files
    files = version.get('files', [])
    if not files:
        return True
        
    # If only Training Data is available, it's likely not downloadable as a model
    has_model = False
    for f in files:
        if f.get('type') in ['Model', 'Pruned Model', 'VAE', 'LoCon', 'LORA']:
            has_model = True
            break
            
    if not has_model and files:
        # If we have files but none are models (e.g. only Training Data), treat as gen-only
        return True
        
    return False


def display_versions(model_info, interactive=True):
    """Display available versions and let user select one"""
    if not model_info or 'modelVersions' not in model_info:
        console.print("[red]Error: No model versions found[/red]")
        return None
    
    versions = model_info['modelVersions']
    
    # Sort versions by their creation date (newest first)
    versions.sort(key=lambda x: x.get('createdAt', ''), reverse=True)
    
    if not interactive:
        return [versions[0]]
    
    console.print(f"\n[bold]Available versions for {model_info['name']}:[/bold]")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim", width=4)
    table.add_column("Status", width=12)
    table.add_column("Name")
    table.add_column("Files")
    table.add_column("Downloads")
    table.add_column("Trained Words")

    for i, version in enumerate(versions):
        name = version.get('name', f"Version {i+1}")
        
        # Extract file info
        file_info = ""
        if 'files' in version and version['files']:
            files = version['files']
            if len(files) == 1:
                file_size_mb = files[0].get('sizeKB', 0) / 1024
                if file_size_mb > 1024:
                    file_info = f"({file_size_mb/1024:.1f} GB)"
                else:
                    file_info = f"({file_size_mb:.1f} MB)"
            else:
                file_info = f"({len(files)} files)"
        
        # Check if trained/fine-tuned
        trained_info = ""
        if version.get('trainedWords'):
            trained_words = len(version.get('trainedWords', []))
            trained_info = f"[{trained_words} words]"
        
        # Get download count
        downloads = version.get('downloadCount', 0)
        download_info = f"{downloads:,}"
        
        # Determine status
        is_gen_only = check_generation_only(version)
        
        if is_gen_only:
            status = "[red]Gen-Only[/red]"
        elif version.get('baseModelType'):
            status = "[green]Base[/green]"
        else:
            status = "[dim]Other[/dim]"
        
        table.add_row(str(i+1), status, name, file_info, download_info, trained_info)
    
    console.print(table)
    console.print("[dim]Tip: You can select multiple versions by separating numbers with commas (e.g. 1,3)[/dim]")
    
    while True:
        try:
            choice = Prompt.ask("Enter number(s) to download", default="1")
            if choice.lower() == 'q':
                return None
            
            # Handle multi-selection
            selected_versions = []
            parts = [p.strip() for p in choice.split(',')]
            
            valid_selection = True
            for part in parts:
                try:
                    idx = int(part) - 1
                    if 0 <= idx < len(versions):
                        selected = versions[idx]
                        if check_generation_only(selected):
                            console.print(f"[red]⚠️ Warning: Version '{selected['name']}' appears to be Generation-Only.[/red]")
                            if not Confirm.ask("Try to download anyway?"):
                                continue
                        selected_versions.append(selected)
                    else:
                        console.print(f"[red]Invalid number: {part}[/red]")
                        valid_selection = False
                except ValueError:
                    console.print(f"[red]Invalid input: {part}[/red]")
                    valid_selection = False
            
            if valid_selection and selected_versions:
                return selected_versions
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Operation canceled.[/yellow]")
            sys.exit(0)


def select_file(files, interactive=True):
    """If multiple files exist, let user select which to download"""
    if not files:
        return None
    
    if len(files) == 1:
        return [files[0]]
        
    if not interactive:
        # In non-interactive mode, try to find the primary file
        for file in files:
            if file.get('primary'):
                return [file]
        # If no primary file, return the first one
        return [files[0]]
    
    console.print("\n[bold]Available files for this version:[/bold]")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim", width=4)
    table.add_column("Name")
    table.add_column("Size")
    table.add_column("Type")
    table.add_column("Format")

    for i, file in enumerate(files):
        name = file.get('name', f"File {i+1}")
        size_mb = file.get('sizeKB', 0) / 1024
        if size_mb > 1024:
            size_str = f"{size_mb/1024:.2f} GB"
        else:
            size_str = f"{size_mb:.2f} MB"
            
        file_type = file.get('type', 'Unknown')
        format_type = file.get('format', 'Unknown')
        
        table.add_row(str(i+1), name, size_str, file_type, format_type)
    
    console.print(table)
    console.print("[dim]Tip: You can select multiple files by separating numbers with commas (e.g. 1,2)[/dim]")
    
    while True:
        try:
            choice = Prompt.ask("Enter number(s) to download", default="1")
            if choice.lower() == 'q':
                return None
            
            selected_files = []
            parts = [p.strip() for p in choice.split(',')]
            
            valid_selection = True
            for part in parts:
                try:
                    idx = int(part) - 1
                    if 0 <= idx < len(files):
                        selected_files.append(files[idx])
                    else:
                        console.print(f"[red]Invalid number: {part}[/red]")
                        valid_selection = False
                except ValueError:
                    console.print(f"[red]Invalid input: {part}[/red]")
                    valid_selection = False
            
            if valid_selection and selected_files:
                return selected_files
                
        except KeyboardInterrupt:
            console.print("\n[yellow]Operation canceled.[/yellow]")
            sys.exit(0)





def find_version_by_name(versions, version_name):
    """Find a version by its name"""
    version_name = version_name.lower()
    
    # First try exact match
    for version in versions:
        if version.get('name', '').lower() == version_name:
            return version
    
    # Then try starts with
    for version in versions:
        if version.get('name', '').lower().startswith(version_name):
            return version
    
    # Then try contains
    for version in versions:
        if version_name in version.get('name', '').lower():
            return version
    
    return None


def download_file(url: str, output_path: str, token: str, force=False, version_name=None, interactive=True):
    headers = {
        'Authorization': f'Bearer {token}',
        'User-Agent': USER_AGENT,
    }

    # If URL is a model ID or a model page, convert to download URL
    model_id = extract_model_id(url)
    if not model_id:
        console.print(f"[red]Error: Could not extract model ID from {url}[/red]")
        return
    
    # If it's a direct download URL, just download it
    if url.startswith('https://civitai.com/api/download/'):
        download_url = url
        model_info = None
        selected_version = None
    else:
        # Get model info to determine available versions
        model_info = get_model_info(model_id, token)
        if not model_info:
            console.print(f"[red]Error: Could not fetch model info for ID {model_id}[/red]")
            return
        
        console.print(f"\n[bold cyan]Found model: {model_info['name']}[/bold cyan]")
        
        if version_name:
            # User specified a version
            if version_name.lower() == 'latest':
                selected_versions = [model_info['modelVersions'][0]]
                console.print(f"Using latest version: [green]{selected_versions[0]['name']}[/green]")
            else:
                selected_version = find_version_by_name(model_info['modelVersions'], version_name)
                if not selected_version:
                    console.print(f"[red]Error: Could not find version matching '{version_name}'[/red]")
                    console.print("Available versions:")
                    for v in model_info['modelVersions']:
                        console.print(f"- {v.get('name', 'Unknown')}")
                    return
                selected_versions = [selected_version]
                console.print(f"Using specified version: [green]{selected_version['name']}[/green]")
        else:
            # Interactive selection
            selected_versions = display_versions(model_info, interactive)
            if not selected_versions:
                console.print("[yellow]Download canceled.[/yellow]")
                return
        
        download_success = False
        for selected_version in selected_versions:
            console.print(f"[bold cyan]Processing version: {selected_version['name']}[/bold cyan]")
            
            # Check if version has files
            if 'files' not in selected_version or not selected_version['files']:
                console.print(f"[red]Error: No files found for version {selected_version['name']}[/red]")
                continue
            
            # Select file if multiple exist
            selected_files = select_file(selected_version['files'], interactive)
            if not selected_files:
                console.print("[yellow]Download canceled for this version.[/yellow]")
                continue
            
            for selected_file in selected_files:
                # Create download URL
                # Prefer the explicit downloadUrl from the file object if available
                if selected_file.get('downloadUrl'):
                    download_url = selected_file['downloadUrl']
                else:
                    download_url = f"https://civitai.com/api/download/models/{selected_version['id']}"
                    if selected_file.get('id'):
                        download_url += f"?fileId={selected_file['id']}"
                    else:
                        console.print(f"[yellow]Warning: File '{selected_file.get('name')}' has no ID. Downloading primary file instead.[/yellow]")

                # Add token if needed
                if token:
                    separator = "&" if "?" in download_url else "?"
                    download_url += f"{separator}token={token}"
                
                # Disable automatic redirect handling
                class NoRedirection(urllib.request.HTTPErrorProcessor):
                    def http_response(self, request, response):
                        return response
                    https_response = http_response

                try:
                    request = urllib.request.Request(download_url, headers=headers)
                    opener = urllib.request.build_opener(NoRedirection)
                    response = opener.open(request)
                except Exception as e:
                    console.print(f"[red]Error accessing URL: {e}[/red]")
                    continue

                redirect_url = None
                filename = None

                if response.status in [301, 302, 303, 307, 308]:
                    redirect_url = response.getheader('Location')
                    
                    # Extract filename from the redirect URL
                    parsed_url = urlparse(redirect_url)
                    query_params = parse_qs(parsed_url.query)
                    content_disposition = query_params.get('response-content-disposition', [None])[0]

                    if content_disposition:
                        filename = unquote(content_disposition.split('filename=')[1].strip('"'))
                    else:
                        # Try to extract filename from the path
                        path = parsed_url.path
                        if path:
                            filename = os.path.basename(path)
                        else:
                            # raise Exception('Unable to determine filename')
                            console.print("[red]Unable to determine filename[/red]")
                            continue
                elif response.status == 404:
                    console.print("[red]File not found[/red]")
                    continue
                elif response.status == 401:
                    error_msg = 'Unauthorized: Please check your API token.'
                    try:
                        error_body = response.read().decode('utf-8')
                        if error_body:
                            # Try to parse JSON error if possible
                            try:
                                error_json = json.loads(error_body)
                                if 'error' in error_json:
                                    error_msg += f"\nServer message: {error_json['error']}"
                                elif 'message' in error_json:
                                    error_msg += f"\nServer message: {error_json['message']}"
                                else:
                                    error_msg += f"\nServer details: {error_body}"
                            except:
                                error_msg += f"\nServer details: {error_body}"
                    except:
                        pass
                    error_msg += "\n[yellow]Note: Some models (like Flux Pro) may require a specific subscription or may not be downloadable.[/yellow]"
                    console.print(f"[red]{error_msg}[/red]")
                    continue
                else:
                    console.print(f"[red]Unexpected response status: {response.status}[/red]")
                    continue

                if not redirect_url or not filename:
                    console.print("[red]Failed to get download information[/red]")
                    continue

                # Get model metadata for better folder placement
                model_metadata = None
                if model_info and selected_version:
                    model_metadata = {
                        'type': model_info.get('type', 'Checkpoint')
                    }

                # Detect model type and determine the appropriate folder
                model_type = detect_model_type(filename, model_metadata)
                model_folder = get_model_folder(model_type)
                
                # Create full path
                if output_path:
                    full_output_path = Path(output_path)
                else:
                    comfyui_path = get_comfyui_path()
                    full_output_path = Path(comfyui_path) / model_folder
                
                # Ensure the output directory exists
                os.makedirs(full_output_path, exist_ok=True)
                
                output_file = os.path.join(full_output_path, filename)
                
                # Check if file already exists
                if os.path.exists(output_file) and not force:
                    console.print(f"[yellow]File already exists: {output_file}[/yellow]")
                    if not Confirm.ask("Overwrite?"):
                        console.print("[yellow]Download canceled.[/yellow]")
                        continue
                
                # Resume logic
                part_file = output_file + ".part"
                resume_header = {}
                downloaded = 0
                mode = 'wb'
                
                if os.path.exists(part_file):
                    file_size = os.path.getsize(part_file)
                    if file_size > 0:
                        downloaded = file_size
                        resume_header = {'Range': f'bytes={downloaded}-'}
                        mode = 'ab'
                        console.print(f"[yellow]Resuming download from {downloaded/(1024*1024):.2f} MB[/yellow]")
                        
                        # Safety check: If the existing partial file is significantly larger than the expected file size
                        if selected_file.get('sizeKB'):
                            expected_size_mb = selected_file['sizeKB'] / 1024
                            current_size_mb = downloaded / (1024 * 1024)
                            # Allow some margin (e.g. 10% or 1MB)
                            if current_size_mb > expected_size_mb * 1.1 + 1: 
                                console.print(f"[red]Warning: Existing partial file is larger than expected ({current_size_mb:.2f} MB > {expected_size_mb:.2f} MB).[/red]")
                                console.print("[red]The existing file might be from a different download. Restarting...[/red]")
                                os.remove(part_file)
                                downloaded = 0
                                mode = 'wb'
                                resume_header = {}

                # Prepare headers for download (remove Authorization as it might cause 400 on presigned URLs)
                download_headers = headers.copy()
                if 'Authorization' in download_headers:
                    del download_headers['Authorization']

                # Now download from the redirect URL
                try:
                    req = urllib.request.Request(redirect_url, headers={**download_headers, **resume_header})
                    try:
                        response = urllib.request.urlopen(req)
                    except urllib.error.HTTPError as e:
                        if e.code == 416 or e.code == 400:
                            # Range not satisfiable or Bad Request (often due to invalid range)
                            console.print(f"[yellow]Resume failed (HTTP {e.code}). Restarting download...[/yellow]")
                            if os.path.exists(part_file):
                                os.remove(part_file)
                            downloaded = 0
                            mode = 'wb'
                            req = urllib.request.Request(redirect_url, headers=download_headers)
                            response = urllib.request.urlopen(req)
                        else:
                            raise e

                    with response:
                        total_size = response.getheader('Content-Length')

                        if total_size is not None:
                            total_size = int(total_size) + downloaded
                            total_mb = total_size / (1024 * 1024)
                            console.print(f"\n[bold green]Starting download:[/bold green] {filename} ({total_mb:.2f} MB)")
                            console.print(f"[blue]Model type:[/blue] {model_type} -> {model_folder}")
                            console.print(f"[blue]Output path:[/blue] {full_output_path}")
                        else:
                            console.print(f"\n[bold green]Starting download:[/bold green] {filename} (Unknown size)")

                        with open(part_file, mode) as f:
                            start_time = time.time()
                            
                            if RICH_AVAILABLE:
                                progress = Progress(
                                    SpinnerColumn(),
                                    TextColumn("[progress.description]{task.description}"),
                                    BarColumn(),
                                    TaskProgressColumn(),
                                    TransferSpeedColumn(),
                                    TimeRemainingColumn(),
                                )
                                
                                with progress:
                                    task = progress.add_task(f"[cyan]Downloading {filename}...", total=total_size, completed=downloaded)
                                    
                                    while True:
                                        buffer = response.read(CHUNK_SIZE)
                                        if not buffer:
                                            break
                                        
                                        downloaded += len(buffer)
                                        f.write(buffer)
                                        progress.update(task, advance=len(buffer))
                            else:
                                # Fallback for when rich is not available (should not happen with requirements)
                                while True:
                                    buffer = response.read(CHUNK_SIZE)
                                    if not buffer:
                                        break
                                    downloaded += len(buffer)
                                    f.write(buffer)
                                    if total_size:
                                        percent = downloaded / total_size * 100
                                        sys.stdout.write(f"\rDownloading: {percent:.1f}%")
                                        sys.stdout.flush()
                    
                    # Rename part file to final filename
                    if os.path.exists(output_file):
                        os.remove(output_file)
                    os.rename(part_file, output_file)

                    end_time = time.time()
                    time_taken = end_time - start_time
                    hours, remainder = divmod(time_taken, 3600)
                    minutes, seconds = divmod(remainder, 60)

                    if hours > 0:
                        time_str = f'{int(hours)}h {int(minutes)}m {int(seconds)}s'
                    elif minutes > 0:
                        time_str = f'{int(minutes)}m {int(seconds)}s'
                    else:
                        time_str = f'{int(seconds)}s'

                    console.print(f'\n[bold green]Download completed in {time_str}[/bold green]')
                    console.print(f'[blue]File saved to:[/blue] {output_file}')
                    
                    # Verify Hash
                    if 'hashes' in selected_file and 'SHA256' in selected_file['hashes']:
                        expected_hash = selected_file['hashes']['SHA256'].upper()
                        console.print("[cyan]Verifying hash...[/cyan]")
                        calculated_hash = calculate_sha256(output_file)
                        
                        if calculated_hash == expected_hash:
                            console.print("[bold green]Hash verification passed! ✅[/bold green]")
                        else:
                            console.print(f"[bold red]Hash verification failed! ❌[/bold red]")
                            console.print(f"Expected: {expected_hash}")
                            console.print(f"Got:      {calculated_hash}")
                            console.print("[yellow]The file might be corrupted.[/yellow]")
                    
                    download_success = True
                    # return output_file # Don't return here, continue loop
                except KeyboardInterrupt:
                    console.print("\n[yellow]Download canceled by user.[/yellow]")
                    # Keep partial file for resume support
                    console.print(f"[dim]Partial download saved to {part_file}[/dim]")
                    return None
                except Exception as e:
                    console.print(f"\n[red]Error during download: {e}[/red]")
                    # Keep partial file for resume support
                    console.print(f"[dim]Partial download saved to {part_file}[/dim]")
                    # return None # Don't return here, continue loop
        
        return download_success
    



def interactive_mode():
    """Interactive mode to guide users through the download process"""
    console.print(Panel.fit("[bold blue]ComfyUI CivitAI Model Downloader - Interactive Mode[/bold blue]", border_style="blue"))
    
    while True:
        try:
            url = Prompt.ask("\nEnter model ID, URL, or Search Query (or 'q' to quit)")
            if url.lower() == 'q':
                break
                
            if not url:
                continue
                
            # Remove any @ prefix that might have been added
            if url.startswith('@'):
                url = url[1:]
                
            # Get the model ID and proceed with download
            model_id = extract_model_id(url)
            
            # If not a direct ID/URL, try searching
            if not model_id:
                console.print(f"[cyan]Searching for '{url}'...[/cyan]")
                token = get_token()
                results = search_models(url, token)
                
                if not results:
                    console.print(f"[red]No models found for '{url}'[/red]")
                    continue
                
                # Display search results
                table = Table(show_header=True, header_style="bold magenta")
                table.add_column("#", style="dim", width=4)
                table.add_column("Name")
                table.add_column("Type")
                table.add_column("Creator")
                table.add_column("Downloads")
                
                for i, model in enumerate(results):
                    name = model.get('name', 'Unknown')
                    m_type = model.get('type', 'Unknown')
                    creator = model.get('creator', {}).get('username', 'Unknown')
                    downloads = model.get('stats', {}).get('downloadCount', 0)
                    
                    table.add_row(str(i+1), name, m_type, creator, f"{downloads:,}")
                
                console.print(table)
                
                choice = Prompt.ask("Select a model number to download (or 'c' to cancel)")
                if choice.lower() == 'c':
                    continue
                    
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(results):
                        model_id = str(results[idx]['id'])
                    else:
                        console.print("[red]Invalid selection[/red]")
                        continue
                except ValueError:
                    console.print("[red]Invalid input[/red]")
                    continue

            if not model_id:
                console.print(f"[red]Could not extract a valid model ID from '{url}'[/red]")
                console.print("Please enter a valid CivitAI URL or model ID")
                continue
                
            token = get_token()
            success = download_file(model_id, None, token, False, None)
            
            if success:
                console.print(f"[bold green]Model is ready to use in ComfyUI![/bold green]")
                
            console.rule()
            if not Confirm.ask("Download another model?"):
                break
                
        except KeyboardInterrupt:
            console.print("\n[yellow]Operation canceled. Exiting...[/yellow]")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            continue
    
    console.print("\n[bold blue]Thanks for using the ComfyUI CivitAI Model Downloader. Goodbye![/bold blue]")


def process_batch_config(batch_file, token, force):
    """Process a batch configuration file for downloading multiple models"""
    if not yaml:
        console.print("[red]PyYAML is not installed. Please install it with: pip install PyYAML[/red]")
        sys.exit(1)
        
    try:
        with open(batch_file, 'r') as f:
            config = yaml.safe_load(f)
            
        if not config or 'models' not in config:
            console.print(f"[red]Invalid batch file format. Missing 'models' list.[/red]")
            return
            
        console.print(f"\n[bold green]Starting batch download from {batch_file}[/bold green]")
        console.print(f"Found {len(config['models'])} models to process.")
        
        for i, item in enumerate(config['models']):
            console.print(f"\n[bold cyan][{i+1}/{len(config['models'])}] Processing item...[/bold cyan]")
            
            url = None
            version = None
            
            if isinstance(item, str) or isinstance(item, int):
                url = str(item)
            elif isinstance(item, dict):
                url = str(item.get('id') or item.get('url'))
                version = item.get('version')
            
            if not url:
                console.print(f"[yellow]Skipping invalid item: {item}[/yellow]")
                continue
                
            # Remove @ prefix if it exists
            if url.startswith('@'):
                url = url[1:]
                
            try:
                download_file(url, None, token, force, version, interactive=False)
            except Exception as e:
                console.print(f"[red]Error downloading {url}: {e}[/red]")
                
        console.print("\n[bold green]Batch processing completed![/bold green]")
        
    except Exception as e:
        console.print(f"[red]Error processing batch file: {e}[/red]")
        sys.exit(1)


def reset_config():
    """Reset the configuration file"""
    if os.path.exists(CONFIG_FILE):
        os.remove(CONFIG_FILE)
        print("Configuration has been reset. You will be prompted for new settings on next run.")
    else:
        print("No configuration file found.")


def main():
    args = get_args()
    
    # Check if user wants to reset config
    if args.reset_config:
        reset_config()
        return
    
    # Check for batch file
    if args.batch_file:
        token = args.token or get_token()
        if not token:
            token = prompt_for_civitai_token()
            if not token:
                print("No valid API token provided. Exiting.")
                sys.exit(1)
                
        process_batch_config(args.batch_file, token, args.force)
        return
    
    # If no URL is provided, go into interactive mode
    if not args.url or args.interactive:
        interactive_mode()
        return
    
    # Use provided token, or the one from args, or the default
    token = args.token or get_token()

    if not token:
        token = prompt_for_civitai_token()
        if not token:
            console.print("[red]No valid API token provided. Exiting.[/red]")
            sys.exit(1)

    try:
        # Remove @ prefix if it exists
        url = args.url
        if url.startswith('@'):
            url = url[1:]
            
        output_file = download_file(url, args.output_path, token, args.force, args.version)
        if output_file:
            console.print(f"[bold green]Model ready to use in ComfyUI![/bold green]")
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation canceled. Exiting...[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f'[red]ERROR: {e}[/red]')
        sys.exit(1)


if __name__ == '__main__':
    main()
