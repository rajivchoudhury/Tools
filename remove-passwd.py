#!/usr/bin/env python3

import argparse
import getpass
from pathlib import Path

from pypdf import PdfReader, PdfWriter


def remove_password(input_path, output_path, password):
    reader = PdfReader(input_path)

    if reader.is_encrypted:
        if not reader.decrypt(password):
            raise ValueError("Incorrect PDF password.")

    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    # Preserve document metadata when available.
    if reader.metadata:
        writer.add_metadata({
            key: value
            for key, value in reader.metadata.items()
            if value is not None
        })

    with open(output_path, "wb") as output_file:
        writer.write(output_file)


def main():
    parser = argparse.ArgumentParser(
        description="Remove password protection from a PDF you are authorized to access."
    )

    parser.add_argument(
        "input",
        help="Input PDF"
    )

    parser.add_argument(
        "-o",
        "--output",
        help="Output PDF"
    )

    parser.add_argument(
        "-p",
        "--password",
        help="PDF password. If omitted, you will be prompted securely."
    )

    args = parser.parse_args()

    input_path = Path(args.input)

    if not input_path.exists():
        raise SystemExit(f"File not found: {input_path}")

    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.with_name(
            f"{input_path.stem}_unlocked.pdf"
        )

    password = args.password

    if password is None:
        password = getpass.getpass("PDF password: ")

    try:
        remove_password(
            input_path,
            output_path,
            password
        )

        print(f"Done: {output_path}")

    except ValueError as e:
        print(f"Error: {e}")
        raise SystemExit(1)

    except Exception as e:
        print(f"Failed: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()