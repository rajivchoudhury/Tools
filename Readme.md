# Tools

This repository includes both command-line utilities and a static browser application for GitHub Pages.

## CLI usage

```bash
source venv/bin/activate
```

```bash
# Compress an image
python3 compress.py <Input.Image.path> --size <Like 500KB, 200KB, 2MB> -o <Output.image.path>

# Remove a password from a PDF
python3 remove-passwd.py <Input.PDF.path> -o <Output.PDF.path>

# Convert from HEIC to JPEG
python convert.py <inputfile/folderpath> -o <outputfolder/file path>
```

## Dependencies for Python tools

- For image compression: `pip install Pillow`, `pip install PyMuPDF`
- For PDF password removal: `pip install pypdf`


## Web Tools (not ready)

A browser-based interface is available through GitHub Pages.

The web application processes files locally in the browser. No uploaded files are sent to a server.

### Available tools

- Compress Image
- Compress PDF
- Remove PDF Password

### Structure

```text
docs/
├── index.html
├── app.js
├── tools.js
├── style.css
├── tools/
│   ├── image-compress.js
│   ├── pdf-compress.js
│   └── pdf-password.js
├── lib/
│   └── qpdf/
│       ├── qpdf.js
│       └── qpdf.wasm
└── ...
```

Adding a new web tool requires only:

1. Create a new implementation file under `docs/tools/`
2. Export a function such as `export async function myTool(file, options) { ... }`
3. Add a registry entry to `docs/tools.js`

The homepage reads the tool list from the registry automatically, so no HTML edits are required for new tools.

## GitHub Pages

The static site is published from the `docs/` directory.

GitHub Actions can deploy it automatically from the repository root using a Pages workflow. The app is intended to run from a project site like:

```text
https://rajivchoudhury.github.io/Tools/
```

Relative paths are used throughout so the site works correctly under the `/Tools/` base path.

## Security and privacy

- Files stay in the browser memory
- No files are uploaded to a server
- No browser file contents are logged
- No arbitrary commands are executed by the web app
- Output files are downloaded directly to the user

## Notes

The Python CLI tools remain fully functional and are not replaced by the browser app. The browser versions are a local, static counterpart designed for users who want to run the utilities directly in GitHub Pages without any backend or server-side processing.
