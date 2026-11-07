import { PDFDocument } from 'https://cdn.jsdelivr.net/npm/pdf-lib@1.17.1/+esm';
import { formatBytes, parseSize, removeExtension, sanitizeFileName } from '../tools.js';

export async function compressPdf(file, options = {}) {
    if (!file) {
        throw new Error('Please choose a PDF file first.');
    }

    const fileName = file.name.toLowerCase();
    if (!fileName.endsWith('.pdf') && !file.type.includes('pdf')) {
        throw new Error('Please select a valid PDF file.');
    }

    const targetSize = options.targetSize || '500KB';
    const targetBytes = parseSize(targetSize);
    const inputBytes = new Uint8Array(await file.arrayBuffer());
    const pdfjsLib = await loadPdfJs();
    const pdf = await pdfjsLib.getDocument({ data: inputBytes }).promise;

    const scales = [1.8, 1.4, 1.0, 0.8, 0.6, 0.5, 0.4];
    let bestPdfBytes = null;

    for (const scale of scales) {
        const pageImages = [];

        for (let pageNumber = 1; pageNumber <= pdf.numPages; pageNumber += 1) {
            const page = await pdf.getPage(pageNumber);
            const viewport = page.getViewport({ scale });
            const canvas = document.createElement('canvas');
            canvas.width = viewport.width;
            canvas.height = viewport.height;
            const context = canvas.getContext('2d');
            await page.render({ canvasContext: context, viewport }).promise;
            pageImages.push(canvas);
        }

        for (const quality of [0.95, 0.85, 0.75, 0.65, 0.55, 0.45, 0.35]) {
            const pdfDoc = await PDFDocument.create();

            for (const canvas of pageImages) {
                const blob = await canvasToBlob(canvas, 'image/jpeg', quality);
                const imageBytes = new Uint8Array(await blob.arrayBuffer());
                const image = await pdfDoc.embedJpg(imageBytes);
                const page = pdfDoc.addPage([image.width, image.height]);
                page.drawImage(image, {
                    x: 0,
                    y: 0,
                    width: image.width,
                    height: image.height
                });
            }

            const bytes = await pdfDoc.save();
            if (bytes.length <= targetBytes) {
                bestPdfBytes = bytes;
                break;
            }
        }

        if (bestPdfBytes) {
            break;
        }
    }

    if (!bestPdfBytes) {
        throw new Error('Unable to reach the requested target size without excessive quality loss. Try a larger target.');
    }

    return {
        blob: new Blob([bestPdfBytes], { type: 'application/pdf' }),
        filename: sanitizeFileName(`${removeExtension(file.name)}-compressed.pdf`),
        info: `${formatBytes(file.size)} → ${formatBytes(bestPdfBytes.length)}`
    };
}

async function loadPdfJs() {
    const lib = await import('https://cdn.jsdelivr.net/npm/pdfjs-dist@4.10.38/+esm');
    lib.GlobalWorkerOptions.workerSrc = 'https://cdn.jsdelivr.net/npm/pdfjs-dist@4.10.38/build/pdf.worker.min.mjs';
    return lib;
}

function canvasToBlob(canvas, type, quality) {
    return new Promise((resolve) => {
        canvas.toBlob((blob) => resolve(blob), type, quality);
    });
}
