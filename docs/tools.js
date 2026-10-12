export const TOOLS = [
    {
        id: "compress-image",
        name: "Compress Image",
        description: "Reduce image size while maintaining good quality.",
        icon: "🖼️",
        accept: "image/*",
        action: "compressImage",
        options: {
            targetSize: true,
            outputFormat: true
        }
    },
    {
        id: "compress-pdf",
        name: "Compress PDF",
        description: "Reduce PDF file size while keeping the pages intact.",
        icon: "📄",
        accept: ".pdf,application/pdf",
        action: "compressPdf",
        options: {
            targetSize: true
        }
    },
    {
        id: "remove-password",
        name: "Remove PDF Password",
        description: "Create an unlocked copy of a PDF in the browser.",
        icon: "🔓",
        accept: ".pdf,application/pdf",
        action: "removePassword",
        options: {
            password: true
        }
    }
];

export function parseSize(value) {
    if (!value || typeof value !== 'string') {
        throw new Error('Invalid target size.');
    }

    const match = value.trim().toUpperCase().match(/^([\d.]+)\s*(KB|MB|GB|B)$/);
    if (!match) {
        throw new Error('Invalid target size. Use values such as 200KB, 500KB, 1MB, or 2MB.');
    }

    const amount = Number.parseFloat(match[1]);
    const units = {
        B: 1,
        KB: 1024,
        MB: 1024 * 1024,
        GB: 1024 * 1024 * 1024
    };

    return Math.round(amount * units[match[2]]);
}

export function formatBytes(bytes) {
    const value = Number(bytes) || 0;
    if (value < 1024) {
        return `${value} B`;
    }
    if (value < 1024 * 1024) {
        return `${(value / 1024).toFixed(1)} KB`;
    }
    if (value < 1024 * 1024 * 1024) {
        return `${(value / (1024 * 1024)).toFixed(2)} MB`;
    }
    return `${(value / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

export function removeExtension(fileName) {
    return fileName.replace(/\.[^/.]+$/, '');
}

export function sanitizeFileName(value) {
    return String(value || 'download')
        .replace(/[\\/:*?"<>|]+/g, '-')
        .replace(/\s+/g, '-')
        .replace(/-+/g, '-')
        .trim();
}
