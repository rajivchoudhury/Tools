from PIL import Image
from pillow_heif import register_heif_opener
from pathlib import Path
import argparse

register_heif_opener()


def convert_heic_to_jpeg(input_path, output_dir=None, quality=95):
    input_path = Path(input_path)

    if output_dir is None:
        output_dir = input_path.parent
    else:
        output_dir = Path(output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / (input_path.stem + ".jpg")

    with Image.open(input_path) as img:
        img = img.convert("RGB")
        img.save(output_path, "JPEG", quality=quality)

    print(f"Converted: {input_path} -> {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Convert HEIC images to JPEG"
    )

    parser.add_argument("input", help="HEIC file or directory")
    parser.add_argument(
        "-o", "--output",
        help="Output directory"
    )
    parser.add_argument(
        "-q", "--quality",
        type=int,
        default=95,
        help="JPEG quality (1-100)"
    )

    args = parser.parse_args()
    input_path = Path(args.input)

    if input_path.is_file():
        convert_heic_to_jpeg(
            input_path, args.output, args.quality
        )

    elif input_path.is_dir():
        files = [
            p for p in input_path.iterdir()
            if p.suffix.lower() == ".heic"
        ]

        for file in files:
            convert_heic_to_jpeg(
                file, args.output, args.quality
            )

        print(f"Converted {len(files)} images.")

    else:
        print("Invalid input path")


if __name__ == "__main__":
    main()