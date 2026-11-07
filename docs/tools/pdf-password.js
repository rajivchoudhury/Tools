import initQpdf from '../lib/qpdf/qpdf.js';
import { removeExtension, sanitizeFileName } from '../tools.js';

export async function removePassword(file, options = {}) {
    if (!file) {
        throw new Error('Please choose a PDF file first.');
    }

    const fileName = file.name.toLowerCase();
    if (!fileName.endsWith('.pdf') && !file.type.includes('pdf')) {
        throw new Error('Please select a valid PDF file.');
    }

    const password = (options.password || '').trim();
    if (!password) {
        throw new Error('Please enter the PDF password.');
    }

    const inputBytes = new Uint8Array(await file.arrayBuffer());
    const outputBytes = await runQpdfUnlock(inputBytes, password);

    return {
        blob: new Blob([outputBytes], { type: 'application/pdf' }),
        filename: sanitizeFileName(`${removeExtension(file.name)}-unlocked.pdf`),
        info: 'Password removed successfully.'
    };
}

async function runQpdfUnlock(inputBytes, password) {
    const qpdfModule = await initQpdf({
        locateFile: (fileName) => new URL(`../lib/qpdf/${fileName}`, import.meta.url).href
    });

    const inputPath = '/input.pdf';
    const outputPath = '/output.pdf';

    qpdfModule.FS.writeFile(inputPath, inputBytes);

    try {
        qpdfModule.callMain(['--password=' + password, '--decrypt', inputPath, outputPath]);
    } catch (error) {
        const message = error && error.message ? error.message : String(error);
        if (message.includes('password') || message.includes('decrypt')) {
            throw new Error('The password is incorrect or the PDF could not be decrypted.');
        }
        throw new Error('Unable to unlock this PDF. Please make sure it is a valid password-protected PDF.');
    }

    const data = qpdfModule.FS.readFile(outputPath);
    return new Uint8Array(data);
}
