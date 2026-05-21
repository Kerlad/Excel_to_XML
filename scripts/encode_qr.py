"""
Utility: Convert a QR code image to a base64 Python constant.

Usage:
    python scripts/encode_qr.py path/to/qr.jpg

Output:
    Prints the base64 string that can be pasted into donation_dialog.py
    to replace the placeholder QR constant _PLACEHOLDER_QR_B64.

Recommended image size: 220x220 PNG.
"""
import sys
import base64
from pathlib import Path


def encode_qr(image_path: str) -> str:
    data = Path(image_path).read_bytes()
    return base64.b64encode(data).decode('ascii')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python scripts/encode_qr.py <path_to_qr_image>")
        sys.exit(1)

    img_path = sys.argv[1]
    if not Path(img_path).exists():
        print(f"File not found: {img_path}")
        sys.exit(1)

    b64 = encode_qr(img_path)
    print("\nReplace the _PLACEHOLDER_QR_B64 constant in donation_dialog.py with this:\n")
    print(f'_PLACEHOLDER_QR_B64 = (\n    "{b64}"\n)')
