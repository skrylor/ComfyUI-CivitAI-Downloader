#!/usr/bin/env python3
import os.path
import sys
import argparse
import time
import urllib.request
import json
import re
import signal
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote
import configparser


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
    
    print("\n" + "=" * 60)
    print("🔧 First-time configuration for ComfyUI CivitAI Downloader 🔧")
    print("=" * 60)
    
    # Get API key
    print("\n📌 You'll need a CivitAI API key to download models.")
    print("   Get one at: https://civitai.com/user/account")
    
    while True:
        api_key = input("\nEnter your CivitAI API key: ").strip()
        if not api_key:
            print("API key cannot be empty. Please try again.")
            continue
        
        # Validate the API key by making a test request
        if validate_api_key(api_key):
            config['DEFAULT']['api_key'] = api_key
            break
        else:
            print("❌ Invalid API key. Please check and try again.")
    
    # Get ComfyUI path
    print("\n📌 Now, let's set up the path to your ComfyUI installation.")
    print("   This is where models will be downloaded.")
    
    while True:
        default_path = str(Path.home() / 'ComfyUI')
        comfyui_path = input(f"\nEnter your ComfyUI path [{default_path}]: ").strip()
        
        if not comfyui_path:
            comfyui_path = default_path
        
        comfyui_path = os.path.expanduser(comfyui_path)
        
        # Validate the ComfyUI path
        if validate_comfyui_path(comfyui_path):
            config['DEFAULT']['comfyui_path'] = comfyui_path
            break
        else:
            retry = input("❌ Invalid ComfyUI path. Would you like to try again? (y/n): ").lower()
            if retry != 'y':
                print("Using the path anyway. You can change it later in the config file.")
                config['DEFAULT']['comfyui_path'] = comfyui_path
                break
    
    # Save the config
    with open(CONFIG_FILE, 'w') as f:
        config.write(f)
    
    print("\n✅ Configuration saved successfully!")
    print(f"   Config file: {CONFIG_FILE}")
    print("   You can edit this file manually if needed.\n")


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
        print(f"Path does not exist: {path}")
        create = input("Would you like to create this directory? (y/n): ").lower()
        if create == 'y':
            try:
                os.makedirs(path, exist_ok=True)
                return True
            except Exception as e:
                print(f"Error creating directory: {e}")
                return False
        return False
    
    # Check if it's a directory
    if not comfyui_path.is_dir():
        print(f"Path is not a directory: {path}")
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
        print(f"This doesn't appear to be a ComfyUI installation.")
        print("Missing expected files/directories like: main.py, models/, web/, comfy/")
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
    print("\nYour CivitAI API token is not set or is invalid.")
    api_key = input('Please enter your CivitAI API token: ').strip()
    
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
        print("❌ Invalid API key. Please check and try again.")
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
        else:
            return 'Other'
    elif extension == '.vae.pt' or extension == '.vae.safetensors':
        return 'VAE'
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


def display_versions(model_info):
    """Display available versions and let user select one"""
    if not model_info or 'modelVersions' not in model_info:
        print("Error: No model versions found")
        return None
    
    versions = model_info['modelVersions']
    
    # Sort versions by their creation date (newest first)
    versions.sort(key=lambda x: x.get('createdAt', ''), reverse=True)
    
    print(f"\n📋 Available versions for {model_info['name']}:")
    print("─" * 50)
    
    for i, version in enumerate(versions):
        name = version.get('name', f"Version {i+1}")
        
        # Extract file info
        file_info = ""
        if 'files' in version and version['files']:
            files = version['files']
            if len(files) == 1:
                file_size = files[0].get('sizeKB', 0) / 1024  # Convert to MB
                file_info = f"({file_size:.1f} GB)"
            else:
                file_info = f"({len(files)} files)"
        
        # Check if trained/fine-tuned
        trained_info = ""
        if version.get('trainedWords'):
            trained_words = len(version.get('trainedWords', []))
            trained_info = f"[{trained_words} trained words]"
        
        # Get download count
        downloads = version.get('downloadCount', 0)
        download_info = f"💾 {downloads:,} downloads"
        
        status = "✅" if version.get('baseModelType') else "◯"
        
        print(f"{i+1}. {status} {name} {file_info} {download_info} {trained_info}")
    
    print("─" * 50)
    
    while True:
        try:
            choice = input("Enter number to download (or 'q' to quit): ")
            if choice.lower() == 'q':
                return None
            
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(versions):
                return versions[choice_idx]
            else:
                print(f"Please enter a number between 1 and {len(versions)}")
        except ValueError:
            print("Please enter a valid number")
        except KeyboardInterrupt:
            print("\nOperation canceled.")
            sys.exit(0)


def select_file(files):
    """If multiple files exist, let user select which to download"""
    if not files:
        return None
    
    if len(files) == 1:
        return files[0]
    
    print("\n📋 Available files for this version:")
    print("─" * 50)
    
    for i, file in enumerate(files):
        name = file.get('name', f"File {i+1}")
        size = file.get('sizeKB', 0) / 1024  # Convert to MB
        file_type = file.get('type', 'Unknown')
        format_type = file.get('format', 'Unknown')
        
        print(f"{i+1}. {name} ({size:.2f} GB) [{file_type} - {format_type}]")
    
    print("─" * 50)
    
    while True:
        try:
            choice = input("Enter number to download (or 'q' to quit): ")
            if choice.lower() == 'q':
                return None
            
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(files):
                return files[choice_idx]
            else:
                print(f"Please enter a number between 1 and {len(files)}")
        except ValueError:
            print("Please enter a valid number")
        except KeyboardInterrupt:
            print("\nOperation canceled.")
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


def download_file(url: str, output_path: str, token: str, force=False, version_name=None):
    headers = {
        'Authorization': f'Bearer {token}',
        'User-Agent': USER_AGENT,
    }

    # If URL is a model ID or a model page, convert to download URL
    model_id = extract_model_id(url)
    if not model_id:
        print(f"Error: Could not extract model ID from {url}")
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
            print(f"Error: Could not fetch model info for ID {model_id}")
            return
        
        print(f"\n🔍 Found model: {model_info['name']}")
        
        if version_name:
            # User specified a version
            if version_name.lower() == 'latest':
                selected_version = model_info['modelVersions'][0]
                print(f"Using latest version: {selected_version['name']}")
            else:
                selected_version = find_version_by_name(model_info['modelVersions'], version_name)
                if not selected_version:
                    print(f"Error: Could not find version matching '{version_name}'")
                    print("Available versions:")
                    for v in model_info['modelVersions']:
                        print(f"- {v.get('name', 'Unknown')}")
                    return
                print(f"Using specified version: {selected_version['name']}")
        else:
            # Interactive selection
            selected_version = display_versions(model_info)
            if not selected_version:
                print("Download canceled.")
                return
        
        # Check if version has files
        if 'files' not in selected_version or not selected_version['files']:
            print(f"Error: No files found for version {selected_version['name']}")
            return
        
        # Select file if multiple exist
        selected_file = select_file(selected_version['files'])
        if not selected_file:
            print("Download canceled.")
            return
        
        # Create download URL
        download_url = f"https://civitai.com/api/download/models/{selected_version['id']}"
        if selected_file.get('id'):
            download_url += f"?fileId={selected_file['id']}"
    
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
        print(f"Error accessing URL: {e}")
        return

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
                raise Exception('Unable to determine filename')
    elif response.status == 404:
        raise Exception('File not found')
    else:
        raise Exception(f'Unexpected response status: {response.status}')

    if not redirect_url or not filename:
        raise Exception('Failed to get download information')

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
        print(f"⚠️ File already exists: {output_file}")
        while True:
            overwrite = input("Overwrite? (y/n): ").lower()
            if overwrite == 'y':
                break
            elif overwrite == 'n':
                print("Download canceled.")
                return
    
    # Now download from the redirect URL
    try:
        with urllib.request.urlopen(redirect_url) as response:
            total_size = response.getheader('Content-Length')

            if total_size is not None:
                total_size = int(total_size)
                total_mb = total_size / (1024 * 1024)
                print(f"\n🚀 Starting download: {filename} ({total_mb:.2f} MB)")
                print(f"📁 Model type: {model_type} → {model_folder}")
                print(f"💾 Output path: {full_output_path}")
            else:
                print(f"\n🚀 Starting download: {filename} (Unknown size)")

            with open(output_file, 'wb') as f:
                downloaded = 0
                start_time = time.time()
                last_update_time = start_time

                while True:
                    chunk_start_time = time.time()
                    buffer = response.read(CHUNK_SIZE)
                    chunk_end_time = time.time()

                    if not buffer:
                        break

                    downloaded += len(buffer)
                    f.write(buffer)
                    chunk_time = chunk_end_time - chunk_start_time

                    # Calculate current speeds and ETAs
                    current_time = time.time()
                    elapsed = current_time - start_time
                    
                    # Update progress at most once per 0.25 seconds to avoid console spam
                    if current_time - last_update_time > 0.25:
                        if chunk_time > 0:
                            speed = len(buffer) / chunk_time / (1024 ** 2)  # Speed in MB/s
                        else:
                            speed = 0

                        if total_size is not None:
                            progress = downloaded / total_size
                            eta_seconds = (total_size - downloaded) / (downloaded / elapsed) if downloaded > 0 else 0
                            
                            # Calculate ETA string
                            eta_str = ""
                            if eta_seconds > 0:
                                eta_min, eta_sec = divmod(int(eta_seconds), 60)
                                eta_hour, eta_min = divmod(eta_min, 60)
                                if eta_hour > 0:
                                    eta_str = f"ETA: {eta_hour}h {eta_min}m {eta_sec}s"
                                elif eta_min > 0:
                                    eta_str = f"ETA: {eta_min}m {eta_sec}s"
                                else:
                                    eta_str = f"ETA: {eta_sec}s"
                            
                            bar_length = 30
                            filled_length = int(bar_length * progress)
                            bar = '█' * filled_length + '░' * (bar_length - filled_length)
                            
                            # Advanced progress display
                            sys.stdout.write(f'\r[{bar}] {progress*100:.1f}% | {downloaded/(1024**2):.1f}/{total_mb:.1f} MB | {speed:.2f} MB/s | {eta_str}')
                            sys.stdout.flush()
                        else:
                            # For unknown sizes
                            elapsed_str = ""
                            elapsed_min, elapsed_sec = divmod(int(elapsed), 60)
                            elapsed_hour, elapsed_min = divmod(elapsed_min, 60)
                            if elapsed_hour > 0:
                                elapsed_str = f"{elapsed_hour}h {elapsed_min}m {elapsed_sec}s"
                            elif elapsed_min > 0:
                                elapsed_str = f"{elapsed_min}m {elapsed_sec}s"
                            else:
                                elapsed_str = f"{elapsed_sec}s"
                                
                            sys.stdout.write(f'\rDownloaded: {downloaded/(1024**2):.2f} MB | {speed:.2f} MB/s | Time: {elapsed_str}')
                            sys.stdout.flush()
                            
                        last_update_time = current_time

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

        sys.stdout.write('\n')
        print(f'✅ Download completed in {time_str}')
        print(f'📁 File saved to: {output_file}')
        
        return output_file
    except KeyboardInterrupt:
        print("\n⚠️ Download canceled by user.")
        # If file was partially downloaded, remove it
        if os.path.exists(output_file):
            os.remove(output_file)
            print(f"Partially downloaded file was removed.")
        return None
    except Exception as e:
        print(f"\n❌ Error during download: {e}")
        # If file was partially downloaded, remove it
        if os.path.exists(output_file):
            os.remove(output_file)
            print(f"Partially downloaded file was removed.")
        return None


def interactive_mode():
    """Interactive mode to guide users through the download process"""
    print("\n" + "=" * 60)
    print("🚀 ComfyUI CivitAI Model Downloader - Interactive Mode 🚀")
    print("=" * 60)
    
    while True:
        try:
            url = input("\nEnter model ID or URL (or 'q' to quit): ")
            if url.lower() == 'q':
                break
                
            if not url:
                continue
                
            # Remove any @ prefix that might have been added
            if url.startswith('@'):
                url = url[1:]
                
            # Get the model ID and proceed with download
            model_id = extract_model_id(url)
            if not model_id:
                print(f"❌ Could not extract a valid model ID from '{url}'")
                print("Please enter a valid CivitAI URL or model ID")
                continue
                
            token = get_token()
            output_file = download_file(model_id, None, token, False, None)
            
            if output_file:
                print(f"✅ Model is ready to use in ComfyUI!")
                
            print("\n" + "─" * 60)
            continue_download = input("Download another model? (y/n): ").lower()
            if continue_download != 'y':
                break
                
        except KeyboardInterrupt:
            print("\nOperation canceled. Exiting...")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            continue
    
    print("\nThanks for using the ComfyUI CivitAI Model Downloader. Goodbye! 👋")


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
    
    # If no URL is provided, go into interactive mode
    if not args.url or args.interactive:
        interactive_mode()
        return
    
    # Use provided token, or the one from args, or the default
    token = args.token or get_token()

    if not token:
        token = prompt_for_civitai_token()
        if not token:
            print("No valid API token provided. Exiting.")
            sys.exit(1)

    try:
        # Remove @ prefix if it exists
        url = args.url
        if url.startswith('@'):
            url = url[1:]
            
        output_file = download_file(url, args.output_path, token, args.force, args.version)
        if output_file:
            print(f"✅ Model ready to use in ComfyUI!")
    except KeyboardInterrupt:
        print("\nOperation canceled. Exiting...")
        sys.exit(0)
    except Exception as e:
        print(f'❌ ERROR: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
