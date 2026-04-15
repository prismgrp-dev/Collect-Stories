import requests
import zipfile
import io
import os
from pathlib import Path

def download_extension(extension_id, output_dir):
    # This URL is a common way to download CRX files
    url = f"https://clients2.google.com/service/update2/crx?response=redirect&prodversion=123.0.6312.122&acceptformat=crx2,crx3&x=id%3D{extension_id}%26uc"
    
    print(f"Downloading extension {extension_id}...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
    }
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Failed to download extension. Status code: {response.status_code}")
        return False

    os.makedirs(output_dir, exist_ok=True)
    
    # A CRX file is a Zip file with a small header. 
    # We need to find the Zip header (PK\x03\x04)
    content = response.content
    zip_start = content.find(b'PK\x03\x04')
    
    if zip_start == -1:
        print("Could not find ZIP header in the CRX file.")
        print(f"Content preview: {content[:100]}")
        return False
    
    zip_content = content[zip_start:]
    
    try:
        with zipfile.ZipFile(io.BytesIO(zip_content)) as z:
            z.extractall(output_dir)
        print(f"Extension successfully extracted to {output_dir}")
        return True
    except Exception as e:
        print(f"Error extracting extension: {e}")
        return False

if __name__ == "__main__":
    EXT_ID = "eneonfefeggeljhiohlnbkkdpepikpbp"
    # Determine the target directory relative to this script
    current_dir = Path(__file__).resolve().parent
    TARGET_DIR = current_dir / "extension"
    
    download_extension(EXT_ID, str(TARGET_DIR))
