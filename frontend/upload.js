const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:8000'
    : window.location.origin;
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const selectFileBtn = document.getElementById('selectFileBtn');
const fileInfo = document.getElementById('fileInfo');
const fileName = document.getElementById('fileName');
const fileSize = document.getElementById('fileSize');
const uploadBtn = document.getElementById('uploadBtn');
const uploadProgress = document.getElementById('uploadProgress');
const successMessage = document.getElementById('successMessage');
const successDetails = document.getElementById('successDetails');
const errorMessage = document.getElementById('errorMessage');
const errorDetails = document.getElementById('errorDetails');
const retryBtn = document.getElementById('retryBtn');
let selectedFile = null;
selectFileBtn.addEventListener('click', () => {
    fileInput.click();
});
fileInput.addEventListener('change', (e) => {
    handleFileSelect(e.target.files[0]);
});
uploadBtn.addEventListener('click', () => {
    if (selectedFile) {
        uploadFile(selectedFile);
    }
});
retryBtn.addEventListener('click', () => {
    resetUploadState();
});
uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('drag-over');
});
uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('drag-over');
});
uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('drag-over');
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFileSelect(files[0]);
    }
});
function handleFileSelect(file) {
    if (!file) return;
    if (!file.name.endsWith('.csv')) {
        showError('Selecteer een geldig CSV-bestand');
        return;
    }
    selectedFile = file;
    fileName.textContent = file.name;
    fileSize.textContent = formatFileSize(file.size);
    uploadArea.style.display = 'none';
    fileInfo.style.display = 'flex';
    successMessage.style.display = 'none';
    errorMessage.style.display = 'none';
}
async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    fileInfo.style.display = 'none';
    uploadProgress.style.display = 'block';
    successMessage.style.display = 'none';
    errorMessage.style.display = 'none';
    try {
        const response = await fetch(`${API_BASE_URL}/api/upload`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            let errorMessage = `Upload failed (status ${response.status})`;
            try {
                const errorData = await response.json();
                errorMessage = errorData.detail || errorMessage;
            } catch {
                const text = await response.text();
                if (text) {
                    errorMessage = `${errorMessage}: ${text.slice(0, 200)}`;
                }
            }
            throw new Error(errorMessage);
        }

        let result;
        try {
            result = await response.json();
        } catch {
            const text = await response.text();
            throw new Error(`Response is not valid JSON (status ${response.status}): ${text.slice(0, 200)}`);
        }

        uploadProgress.style.display = 'none';
        successMessage.style.display = 'block';
        successDetails.innerHTML = `
            <strong>${result.records_processed}</strong> records verwerkt<br>
            Datum range: <strong>${result.date_range.start}</strong> tot <strong>${result.date_range.end}</strong>
        `;
    } catch (error) {
        console.error('Upload error:', error);
        uploadProgress.style.display = 'none';
        errorMessage.style.display = 'block';
        errorDetails.textContent = error.message || 'Er is een fout opgetreden bij het uploaden van het bestand';
    }
}
function resetUploadState() {
    selectedFile = null;
    fileInput.value = '';
    uploadArea.style.display = 'block';
    fileInfo.style.display = 'none';
    uploadProgress.style.display = 'none';
    successMessage.style.display = 'none';
    errorMessage.style.display = 'none';
}
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}
function showError(message) {
    alert(message);
}
