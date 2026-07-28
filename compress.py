#!/usr/bin/env python3

import argparse
import io
import os
import sys
from pathlib import Path

from PIL import Image, ImageOps


def parse_size(value: str) -> int:
    """Convert 500KB, 2MB, 1048576, etc. to bytes."""
    value = value.strip().upper()

    units = {
        "GB": 1024 ** 3,
        "MB": 1024 ** 2,
        "KB": 1024,
        "B": 1,
    }

    for unit, multiplier in units.items():
        if value.endswith(unit):
            number = value[:-len(unit)].strip()
            try:
                return int(float(number) * multiplier)
            except ValueError:
                break

    try:
        return int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Invalid size: {value}. Examples: 500KB, 2MB, 1048576"
        )


def format_size(size: int) -> str:
    """Human-readable file size."""
    if size < 1024:
        return f"{size} B"

    if size < 1024 ** 2:
        return f"{size / 1024:.2f} KB"

    if size < 1024 ** 3:
        return f"{size / (1024 ** 2):.2f} MB"

    return f"{size / (1024 ** 3):.2f} GB"


def encode_jpeg(image: Image.Image, quality: int) -> bytes:
    """Encode image as optimised progressive JPEG."""
    if image.mode not in ("RGB", "L"):
        if "A" in image.getbands():
            # JPEG doesn't support transparency.
            background = Image.new("RGB", image.size, "white")
            background.paste(image, mask=image.getchannel("A"))
            image = background
        else:
            image = image.convert("RGB")

    buffer = io.BytesIO()

    image.save(
        buffer,
        format="JPEG",
        quality=quality,
        optimize=True,
        progressive=True,
        subsampling="4:2:0",
    )

    return buffer.getvalue()


def encode_webp(image: Image.Image, quality: int) -> bytes:
    """Encode image as optimised WebP."""
    buffer = io.BytesIO()

    image.save(
        buffer,
        format="WEBP",
        quality=quality,
        method=6,
        lossless=False,
    )

    return buffer.getvalue()


def find_best_quality(
    image: Image.Image,
    target_bytes: int,
    encoder,
    min_quality: int = 1,
    max_quality: int = 95,
):
    """
    Binary-search the highest quality that fits the target size.
    """
    best_data = None
    best_quality = None

    low = min_quality
    high = max_quality

    while low <= high:
        quality = (low + high) // 2

        data = encoder(image, quality)
        size = len(data)

        if size <= target_bytes:
            best_data = data
            best_quality = quality
            low = quality + 1
        else:
            high = quality - 1

    return best_data, best_quality


def resize_image(image: Image.Image, scale: float) -> Image.Image:
    """Resize while maintaining aspect ratio."""
    width = max(1, int(image.width * scale))
    height = max(1, int(image.height * scale))

    return image.resize(
        (width, height),
        Image.Resampling.LANCZOS,
    )


def compress(
    input_path: Path,
    output_path: Path,
    target_bytes: int,
    output_format: str = "jpeg",
    allow_resize: bool = True,
):
    original_size = input_path.stat().st_size

    with Image.open(input_path) as original:
        # Correct phone/camera EXIF rotation.
        image = ImageOps.exif_transpose(original)

        # Fully load before closing the source file.
        image.load()

        original_dimensions = image.size

    encoder = encode_jpeg if output_format == "jpeg" else encode_webp

    # ---------------------------------------------------------
    # First attempt: preserve original dimensions.
    # ---------------------------------------------------------
    data, quality = find_best_quality(
        image,
        target_bytes,
        encoder,
    )

    # ---------------------------------------------------------
    # If target is too aggressive, gradually resize.
    # ---------------------------------------------------------
    scale = 1.0

    if data is None and allow_resize:
        current_image = image

        for _ in range(20):
            scale *= 0.90
            current_image = resize_image(image, scale)

            data, quality = find_best_quality(
                current_image,
                target_bytes,
                encoder,
            )

            if data is not None:
                image = current_image
                break

    if data is None:
        raise RuntimeError(
            "Unable to reach the requested target size. "
            "Try a larger target size."
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "wb") as f:
        f.write(data)

    final_size = len(data)

    return {
        "original_size": original_size,
        "final_size": final_size,
        "quality": quality,
        "original_dimensions": original_dimensions,
        "final_dimensions": image.size,
        "scale": scale,
    }


def main():
    parser = argparse.ArgumentParser(
        description="High-quality image compressor with target file size."
    )

    parser.add_argument(
        "input",
        help="Input image path",
    )

    parser.add_argument(
        "--size",
        required=True,
        type=parse_size,
        help="Target size, e.g. 500KB, 2MB, 1.5MB",
    )

    parser.add_argument(
        "-o",
        "--output",
        help="Output image path",
    )

    parser.add_argument(
        "--format",
        choices=["jpeg", "webp"],
        default="jpeg",
        help="Output format (default: jpeg)",
    )

    parser.add_argument(
        "--no-resize",
        action="store_true",
        help="Never resize the image",
    )

    args = parser.parse_args()

    input_path = Path(args.input)

    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)

    if args.size <= 0:
        print("Error: Target size must be greater than 0.")
        sys.exit(1)

    # Default output name.
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.with_name(
            f"{input_path.stem}_compressed.{args.format}"
        )

    try:
        result = compress(
            input_path=input_path,
            output_path=output_path,
            target_bytes=args.size,
            output_format=args.format,
            allow_resize=not args.no_resize,
        )

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    print()
    print("Compression complete")
    print("-" * 40)
    print(f"Input:       {input_path}")
    print(f"Output:      {output_path}")
    print()
    print(f"Original:    {format_size(result['original_size'])}")
    print(f"Target:      {format_size(args.size)}")
    print(f"Output:      {format_size(result['final_size'])}")
    print(
        f"Reduction:   "
        f"{100 * (1 - result['final_size'] / result['original_size']):.1f}%"
    )
    print()
    print(
        f"Dimensions:  "
        f"{result['original_dimensions'][0]}x"
        f"{result['original_dimensions'][1]}"
        f" -> "
        f"{result['final_dimensions'][0]}x"
        f"{result['final_dimensions'][1]}"
    )
    print(f"Quality:     {result['quality']}")
    print("-" * 40)


if __name__ == "__main__":
    main()