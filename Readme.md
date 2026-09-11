# Usage

```
source venv/bin/activate
```

```
# Compress Image
python3 compress.py <Input.Image.path> --size <Like 500KB, 200KB, 2MB> -o <Output.image.path>

# Remove password from PDF
python3 remove-passwd.py <Input.PDF.path> -o <Output.PDF.path>
```

## Dependency required

- For Compression
    `pip install Pillow`, `pip install PyMuPDF`

- For password remove
    `pip install pypdf`