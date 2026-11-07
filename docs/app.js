import { TOOLS, formatBytes } from './tools.js';
import { compressImage } from './tools/image-compress.js';
import { compressPdf } from './tools/pdf-compress.js';
import { removePassword } from './tools/pdf-password.js';

const toolActions = {
    compressImage,
    compressPdf,
    removePassword
};

const toolList = document.getElementById('tool-list');
const workspace = document.getElementById('workspace');
const backButton = document.getElementById('back-button');
const toolIcon = document.getElementById('tool-icon');
const toolTitle = document.getElementById('tool-title');
const toolDescription = document.getElementById('tool-description');
const fileInput = document.getElementById('file-input');
const dropZone = document.getElementById('drop-zone');
const fileName = document.getElementById('file-name');
const options = document.getElementById('options');
const processButton = document.getElementById('process-button');
const progress = document.getElementById('progress');
const progressText = document.getElementById('progress-text');
const errorBox = document.getElementById('error');
const result = document.getElementById('result');
const resultInfo = document.getElementById('result-info');
const downloadButton = document.getElementById('download-button');

let currentTool = null;
let selectedFile = null;
let activeObjectUrl = null;
let isProcessing = false;

function renderTools() {
    toolList.innerHTML = '';

    for (const tool of TOOLS) {
        const card = document.createElement('button');
        card.type = 'button';
        card.className = 'tool-card';
        card.setAttribute('aria-label', `Open ${tool.name}`);
        card.innerHTML = `
            <div class="tool-icon" aria-hidden="true">${tool.icon}</div>
            <h2>${tool.name}</h2>
            <p>${tool.description}</p>
            <span class="tool-link">Open Tool →</span>
        `;
        card.addEventListener('click', () => openTool(tool));
        toolList.appendChild(card);
    }
}

function openTool(tool) {
    currentTool = tool;
    toolList.classList.add('hidden');
    workspace.classList.remove('hidden');
    toolIcon.textContent = tool.icon;
    toolTitle.textContent = tool.name;
    toolDescription.textContent = tool.description;
    fileInput.accept = tool.accept;
    reset();
    renderOptions(tool);
    updateProcessButtonState();
}

function renderOptions(tool) {
    options.innerHTML = '';

    if (tool.options?.targetSize) {
        const group = document.createElement('div');
        group.className = 'option-group';
        group.innerHTML = `
            <label for="target-size">Target Size</label>
            <select id="target-size" aria-label="Target size">
                <option value="200KB">200 KB</option>
                <option value="500KB" selected>500 KB</option>
                <option value="1MB">1 MB</option>
                <option value="2MB">2 MB</option>
                <option value="5MB">5 MB</option>
            </select>
        `;
        options.appendChild(group);
    }

    if (tool.options?.outputFormat) {
        const group = document.createElement('div');
        group.className = 'option-group';
        group.innerHTML = `
            <label for="output-format">Output Format</label>
            <select id="output-format" aria-label="Output format">
                <option value="jpeg">JPEG</option>
                <option value="webp">WebP</option>
            </select>
        `;
        options.appendChild(group);
    }

    if (tool.options?.password) {
        const group = document.createElement('div');
        group.className = 'option-group';
        group.innerHTML = `
            <label for="pdf-password">PDF Password</label>
            <input id="pdf-password" type="password" placeholder="Enter password" autocomplete="current-password" />
        `;
        options.appendChild(group);
    }
}

function setFile(file) {
    selectedFile = file;
    const sizeText = formatBytes(file.size);
    fileName.textContent = `${file.name} (${sizeText})`;
    result.classList.add('hidden');
    errorBox.classList.add('hidden');
    updateProcessButtonState();
}

function updateProcessButtonState() {
    processButton.disabled = !selectedFile || isProcessing;
}

function setProcessing(processing) {
    isProcessing = processing;
    processButton.disabled = !selectedFile || processing;
    progress.classList.toggle('hidden', !processing);
    if (processing) {
        progressText.textContent = 'Processing...';
    }
}

function showError(message) {
    errorBox.textContent = message;
    errorBox.classList.remove('hidden');
}

function clearDownloadUrl() {
    if (activeObjectUrl) {
        URL.revokeObjectURL(activeObjectUrl);
        activeObjectUrl = null;
    }
    downloadButton.removeAttribute('href');
    downloadButton.removeAttribute('download');
}

function showResult(resultData) {
    clearDownloadUrl();
    activeObjectUrl = URL.createObjectURL(resultData.blob);
    downloadButton.href = activeObjectUrl;
    downloadButton.download = resultData.filename;
    resultInfo.textContent = resultData.info;
    result.classList.remove('hidden');
    errorBox.classList.add('hidden');
}

function reset() {
    clearDownloadUrl();
    selectedFile = null;
    fileInput.value = '';
    fileName.textContent = '';
    processButton.disabled = true;
    progress.classList.add('hidden');
    result.classList.add('hidden');
    errorBox.classList.add('hidden');
}

fileInput.addEventListener('change', () => {
    if (fileInput.files && fileInput.files.length) {
        setFile(fileInput.files[0]);
    }
});

dropZone.addEventListener('dragover', (event) => {
    event.preventDefault();
    dropZone.classList.add('dragging');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragging');
});

dropZone.addEventListener('drop', (event) => {
    event.preventDefault();
    dropZone.classList.remove('dragging');
    const file = event.dataTransfer.files[0];
    if (file) {
        setFile(file);
    }
});

backButton.addEventListener('click', () => {
    currentTool = null;
    workspace.classList.add('hidden');
    toolList.classList.remove('hidden');
    reset();
});

processButton.addEventListener('click', async () => {
    if (!selectedFile || !currentTool) {
        return;
    }

    const toolFunction = toolActions[currentTool.action];
    if (!toolFunction) {
        showError('This tool is not available yet.');
        return;
    }

    try {
        setProcessing(true);
        const params = {};
        if (currentTool.options?.targetSize) {
            params.targetSize = document.getElementById('target-size').value;
        }
        if (currentTool.options?.outputFormat) {
            params.outputFormat = document.getElementById('output-format').value;
        }
        if (currentTool.options?.password) {
            params.password = document.getElementById('pdf-password').value;
        }

        const resultData = await toolFunction(selectedFile, params);
        showResult(resultData);
    } catch (error) {
        console.error(error);
        showError(error?.message || 'Unable to process this file. Please make sure the file is valid and try again.');
    } finally {
        setProcessing(false);
    }
});

renderTools();
