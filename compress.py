#!/usr/bin/env python3

import argparse
import io
import sys
from pathlib import Path

from PIL import Image, ImageOps

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None


# ============================================================
# SIZE UTILITIES
# ============================================================

def parse_size(value: str) -> int:
    """
    Convert sizes such as:
        500KB
        2MB
        1.5MB
        1GB
        1048576
    into bytes.
    """
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
                raise argparse.ArgumentTypeError(
                    f"Invalid size: {value}. "
                    f"Examples: 500KB, 1.5MB, 2GB, 1048576"
                )

    try:
        return int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Invalid size: {value}. "
            f"Examples: 500KB, 1.5MB, 2GB, 1048576"
        )


def format_size(size: int) -> str:
    """Return a human-readable file size."""

    if size < 1024:
        return f"{size} B"

    if size < 1024 ** 2:
        return f"{size / 1024:.2f} KB"

    if size < 1024 ** 3:
        return f"{size / (1024 ** 2):.2f} MB"

    return f"{size / (1024 ** 3):.2f} GB"


# ============================================================
# IMAGE ENCODERS
# ============================================================

def encode_jpeg(image: Image.Image, quality: int) -> bytes:
    """Encode image as optimized progressive JPEG."""

    if image.mode not in ("RGB", "L"):
        if "A" in image.getbands():
            # JPEG does not support transparency.
            background = Image.new("RGB", image.size, "white")
            background.paste(
                image,
                mask=image.getchannel("A")
            )
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
    """Encode image as optimized WebP."""

    buffer = io.BytesIO()

    image.save(
        buffer,
        format="WEBP",
        quality=quality,
        method=6,
        lossless=False,
    )

    return buffer.getvalue()


# ============================================================
# IMAGE QUALITY SEARCH
# ============================================================

def find_best_quality(
    image: Image.Image,
    target_bytes: int,
    encoder,
    min_quality: int = 1,
    max_quality: int = 95,
):
    """
    Binary-search the highest image quality that fits
    within target_bytes.
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


# ============================================================
# IMAGE RESIZING
# ============================================================

def resize_image(
    image: Image.Image,
    scale: float
) -> Image.Image:
    """Resize image while maintaining aspect ratio."""

    width = max(1, int(image.width * scale))
    height = max(1, int(image.height * scale))

    return image.resize(
        (width, height),
        Image.Resampling.LANCZOS,
    )


# ============================================================
# IMAGE COMPRESSION
# ============================================================

def compress_image(
    input_path: Path,
    output_path: Path,
    target_bytes: int,
    output_format: str = "jpeg",
    allow_resize: bool = True,
):
    """Compress an image to the requested target size."""

    original_size = input_path.stat().st_size

    with Image.open(input_path) as original:

        # Correct phone/camera EXIF rotation.
        image = ImageOps.exif_transpose(original)

        # Fully load before closing source.
        image.load()

        original_dimensions = image.size

    if output_format == "jpeg":
        encoder = encode_jpeg
    else:
        encoder = encode_webp

    # --------------------------------------------------------
    # First attempt:
    # Preserve original dimensions.
    # --------------------------------------------------------

    data, quality = find_best_quality(
        image,
        target_bytes,
        encoder,
    )

    scale = 1.0

    # --------------------------------------------------------
    # If target is too aggressive, resize gradually.
    # --------------------------------------------------------

    if data is None and allow_resize:

        current_image = image

        for _ in range(30):

            scale *= 0.90

            current_image = resize_image(
                image,
                scale
            )

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

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

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


# ============================================================
# PDF UTILITIES
# ============================================================

def render_pdf_pages(
    input_path: Path,
    scale: float
):
    """
    Render every PDF page to a PIL image.

    scale=1.0 approximately corresponds to 72 DPI.
    scale=2.0 approximately corresponds to 144 DPI.
    """

    if fitz is None:
        raise RuntimeError(
            "PyMuPDF is required for PDF compression.\n"
            "Install it with:\n\n"
            "pip install PyMuPDF"
        )

    document = fitz.open(input_path)

    pages = []

    try:
        for page in document:

            matrix = fitz.Matrix(
                scale,
                scale
            )

            pixmap = page.get_pixmap(
                matrix=matrix,
                colorspace=fitz.csRGB,
                alpha=False,
            )

            image = Image.frombytes(
                "RGB",
                [pixmap.width, pixmap.height],
                pixmap.samples,
            )

            pages.append(image)

    finally:
        document.close()

    return pages


def create_pdf_from_images(
    images,
    output_path: Path,
    quality: int,
):
    """
    Create a PDF from PIL images using JPEG compression.

    Each PDF page becomes a JPEG image.
    """

    if not images:
        raise RuntimeError("PDF contains no pages.")

    pdf = fitz.open()

    try:

        for image in images:

            # ------------------------------------------------
            # Encode JPEG.
            # ------------------------------------------------

            jpeg_data = encode_jpeg(
                image,
                quality
            )

            # ------------------------------------------------
            # Create PDF page matching image aspect ratio.
            #
            # 72 points/inch.
            # JPEG dimensions are treated as 72 DPI.
            # ------------------------------------------------

            width = image.width
            height = image.height

            page = pdf.new_page(
                width=width,
                height=height,
            )

            page.insert_image(
                fitz.Rect(
                    0,
                    0,
                    width,
                    height
                ),
                stream=jpeg_data,
            )

        # Save with garbage collection and compression.
        pdf.save(
            output_path,
            garbage=4,
            deflate=True,
            clean=True,
        )

    finally:
        pdf.close()


def create_pdf_bytes_from_images(
    images,
    quality: int,
):
    """
    Create a compressed PDF in memory.
    Used during target-size search.
    """

    if not images:
        raise RuntimeError("PDF contains no pages.")

    pdf = fitz.open()

    try:

        for image in images:

            jpeg_data = encode_jpeg(
                image,
                quality
            )

            width = image.width
            height = image.height

            page = pdf.new_page(
                width=width,
                height=height,
            )

            page.insert_image(
                fitz.Rect(
                    0,
                    0,
                    width,
                    height
                ),
                stream=jpeg_data,
            )

        # Generate PDF bytes.
        data = pdf.tobytes(
            garbage=4,
            deflate=True,
            clean=True,
        )

        return data

    finally:
        pdf.close()


# ============================================================
# PDF QUALITY SEARCH
# ============================================================

def find_best_pdf_quality(
    images,
    target_bytes: int,
    min_quality: int = 1,
    max_quality: int = 95,
):
    """
    Find the highest JPEG quality that produces a PDF
    smaller than or equal to target_bytes.
    """

    best_data = None
    best_quality = None

    low = min_quality
    high = max_quality

    while low <= high:

        quality = (low + high) // 2

        data = create_pdf_bytes_from_images(
            images,
            quality,
        )

        size = len(data)

        if size <= target_bytes:

            best_data = data
            best_quality = quality

            low = quality + 1

        else:

            high = quality - 1

    return best_data, best_quality


# ============================================================
# PDF COMPRESSION
# ============================================================

def compress_pdf(
    input_path: Path,
    output_path: Path,
    target_bytes: int,
    allow_resize: bool = True,
):
    """
    Compress a PDF to the requested target size.

    NOTE:
    The resulting PDF consists of JPEG images.
    Original text/vector information is not preserved.
    """

    original_size = input_path.stat().st_size

    if fitz is None:
        raise RuntimeError(
            "PyMuPDF is required for PDF compression.\n"
            "Install it with:\n\n"
            "pip install PyMuPDF"
        )

    # --------------------------------------------------------
    # Determine page count.
    # --------------------------------------------------------

    with fitz.open(input_path) as document:
        page_count = len(document)

    # --------------------------------------------------------
    # Start at approximately 144 DPI.
    #
    # scale 2.0 = 144 DPI
    # scale 1.5 = 108 DPI
    # scale 1.0 = 72 DPI
    # --------------------------------------------------------

    scale = 2.0

    best_data = None
    best_quality = None
    best_scale = None
    best_dimensions = None

    # --------------------------------------------------------
    # Try multiple rendering resolutions.
    # --------------------------------------------------------

    scales = [
        2.0,
        1.8,
        1.6,
        1.4,
        1.2,
        1.0,
        0.9,
        0.8,
        0.7,
        0.6,
        0.5,
        0.4,
        0.3,
        0.25,
    ]

    if not allow_resize:
        scales = [2.0]

    for scale in scales:

        images = render_pdf_pages(
            input_path,
            scale,
        )

        data, quality = find_best_pdf_quality(
            images,
            target_bytes,
        )

        if data is not None:

            best_data = data
            best_quality = quality
            best_scale = scale

            if images:
                best_dimensions = (
                    images[0].size
                )

            break

    if best_data is None:
        raise RuntimeError(
            "Unable to reach the requested target size.\n"
            "Try a larger target size."
        )

    # --------------------------------------------------------
    # Write final PDF.
    # --------------------------------------------------------

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(output_path, "wb") as f:
        f.write(best_data)

    final_size = len(best_data)

    return {
        "original_size": original_size,
        "final_size": final_size,
        "quality": best_quality,
        "scale": best_scale,
        "page_count": page_count,
        "page_dimensions": best_dimensions,
    }


# ============================================================
# FILE TYPE DETECTION
# ============================================================

def detect_file_type(path: Path):
    """
    Detect whether input is PDF or image.
    """

    extension = path.suffix.lower()

    if extension == ".pdf":
        return "pdf"

    image_extensions = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".bmp",
        ".tif",
        ".tiff",
        ".gif",
    }

    if extension in image_extensions:
        return "image"

    # Try opening as image.
    try:
        with Image.open(path):
            return "image"
    except Exception:
        pass

    raise RuntimeError(
        f"Unsupported file type: {path.suffix or 'unknown'}"
    )


# ============================================================
# MAIN COMPRESSION DISPATCHER
# ============================================================

def compress(
    input_path: Path,
    output_path: Path,
    target_bytes: int,
    output_format: str = "jpeg",
    allow_resize: bool = True,
):
    """
    Automatically compress image or PDF.
    """

    file_type = detect_file_type(
        input_path
    )

    if file_type == "pdf":

        return compress_pdf(
            input_path=input_path,
            output_path=output_path,
            target_bytes=target_bytes,
            allow_resize=allow_resize,
        )

    return compress_image(
        input_path=input_path,
        output_path=output_path,
        target_bytes=target_bytes,
        output_format=output_format,
        allow_resize=allow_resize,
    )


# ============================================================
# ARGUMENT PARSER
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "High-quality image and PDF compressor "
            "with target file size."
        )
    )

    parser.add_argument(
        "input",
        help="Input image or PDF path",
    )

    parser.add_argument(
        "--size",
        required=True,
        type=parse_size,
        help=(
            "Target size, e.g. "
            "500KB, 1.5MB, 2MB"
        ),
    )

    parser.add_argument(
        "-o",
        "--output",
        help="Output file path",
    )

    parser.add_argument(
        "--format",
        choices=["jpeg", "webp"],
        default="jpeg",
        help=(
            "Output image format. "
            "Ignored for PDF input. "
            "Default: jpeg"
        ),
    )

    parser.add_argument(
        "--no-resize",
        action="store_true",
        help=(
            "Never resize images or reduce "
            "PDF rendering resolution."
        ),
    )

    args = parser.parse_args()

    input_path = Path(args.input)

    # --------------------------------------------------------
    # Validate input.
    # --------------------------------------------------------

    if not input_path.exists():

        print(
            f"Error: File not found: {input_path}"
        )

        sys.exit(1)

    if not input_path.is_file():

        print(
            f"Error: Not a file: {input_path}"
        )

        sys.exit(1)

    # --------------------------------------------------------
    # Validate target size.
    # --------------------------------------------------------

    if args.size <= 0:

        print(
            "Error: Target size must be greater than 0."
        )

        sys.exit(1)

    # --------------------------------------------------------
    # Detect file type.
    # --------------------------------------------------------

    try:

        file_type = detect_file_type(
            input_path
        )

    except Exception as e:

        print(f"Error: {e}")
        sys.exit(1)

    # --------------------------------------------------------
    # Default output.
    # --------------------------------------------------------

    if args.output:

        output_path = Path(
            args.output
        )

    else:

        if file_type == "pdf":

            output_path = input_path.with_name(
                f"{input_path.stem}_compressed.pdf"
            )

        else:

            output_path = input_path.with_name(
                f"{input_path.stem}_compressed."
                f"{args.format}"
            )

    # --------------------------------------------------------
    # Compress.
    # --------------------------------------------------------

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

    # ========================================================
    # OUTPUT
    # ========================================================

    print()
    print("Compression complete")
    print("-" * 50)

    print(
        f"Type:        "
        f"{file_type.upper()}"
    )

    print(
        f"Input:       "
        f"{input_path}"
    )

    print(
        f"Output:      "
        f"{output_path}"
    )

    print()

    print(
        f"Original:    "
        f"{format_size(result['original_size'])}"
    )

    print(
        f"Target:      "
        f"{format_size(args.size)}"
    )

    print(
        f"Output:      "
        f"{format_size(result['final_size'])}"
    )

    reduction = (
        100
        * (
            1
            - result["final_size"]
            / result["original_size"]
        )
    )

    print(
        f"Reduction:   "
        f"{reduction:.1f}%"
    )

    print()

    # --------------------------------------------------------
    # Image-specific information.
    # --------------------------------------------------------

    if file_type == "image":

        print(
            f"Dimensions:  "
            f"{result['original_dimensions'][0]}"
            f"x"
            f"{result['original_dimensions'][1]}"
            f" -> "
            f"{result['final_dimensions'][0]}"
            f"x"
            f"{result['final_dimensions'][1]}"
        )

        print(
            f"Quality:     "
            f"{result['quality']}"
        )

        print(
            f"Scale:       "
            f"{result['scale']:.2f}"
        )

    # --------------------------------------------------------
    # PDF-specific information.
    # --------------------------------------------------------

    else:

        print(
            f"Pages:       "
            f"{result['page_count']}"
        )

        print(
            f"Render DPI:  "
            f"{result['scale'] * 72:.0f}"
        )

        print(
            f"JPEG quality:"
            f" {result['quality']}"
        )

        if result["page_dimensions"]:

            width, height = (
                result["page_dimensions"]
            )

            print(
                f"Page image:  "
                f"{width}x{height}px"
            )

        print()
        print(
            "Note: PDF pages were converted "
            "to compressed images."
        )
        print(
            "Original selectable text and "
            "vector elements are not preserved."
        )

    print("-" * 50)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()