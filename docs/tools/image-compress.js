import { formatBytes, parseSize, removeExtension, sanitizeFileName } from '../tools.js';

export async function compressImage(file, options = {}) {
    if (!file) {
        throw new Error('Please choose an image file first.');
    }

    if (!file.type.startsWith('image/')) {
        throw new Error('Please select a valid image file.');
    }

    const targetSize = options.targetSize || '500KB';
    const outputFormat = options.outputFormat || 'jpeg';
    const targetBytes = parseSize(targetSize);

    if (targetBytes >= file.size) {
        return {
            blob: file,
            filename: sanitizeFileName(`${removeExtension(file.name)}-compressed.${outputFormat === 'webp' ? 'webp' : 'jpg'}`),
            info: `${formatBytes(file.size)} → ${formatBytes(file.size)} (already within target)`
        };
    }

    const bitmap = await createImageBitmap(file);
    const scales = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2];
    const mimeType = outputFormat === 'webp' ? 'image/webp' : 'image/jpeg';
    const extension = outputFormat === 'webp' ? 'webp' : 'jpg';

    let bestBlob = null;
    let bestQuality = 0.92;

    for (const scale of scales) {
        const width = Math.max(1, Math.round(bitmap.width * scale));
        const height = Math.max(1, Math.round(bitmap.height * scale));
        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;

        const context = canvas.getContext('2d');
        context.drawImage(bitmap, 0, 0, width, height);

        let low = 0.05;
        let high = 0.95;
        let candidate = null;

        for (let iteration = 0; iteration < 10; iteration += 1) {
            const quality = (low + high) / 2;
            const blob = await canvasToBlob(canvas, mimeType, quality);

            if (!blob) {
                break;
            }

            if (blob.size <= targetBytes) {
                candidate = blob;
                bestQuality = quality;
                low = quality + 0.02;
            } else {
                high = quality - 0.02;
            }
        }

        if (candidate) {
            bestBlob = candidate;
            break;
        }
    }

    if (!bestBlob) {
        throw new Error('Unable to reach the requested target size without excessive quality loss. Try a larger target.');
    }

    return {
        blob: bestBlob,
        filename: sanitizeFileName(`${removeExtension(file.name)}-compressed.${extension}`),
        info: `${formatBytes(file.size)} → ${formatBytes(bestBlob.size)} at ${bestQuality.toFixed(2)} quality`
    };
}

function canvasToBlob(canvas, type, quality) {
    return new Promise((resolve) => {
        canvas.toBlob((blob) => resolve(blob), type, quality);
    });
}
