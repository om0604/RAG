import { state } from './state.js';
import * as api from './api.js';
import * as ui from './ui.js';

let uploadSimulationInterval;

async function loadDocuments() {
    try {
        const docs = await api.fetchDocuments();
        state.setDocuments(docs);
        ui.renderDocumentList(handleSelectDocument, handleDeleteDocument);
        
        if (!state.currentDocumentId && docs.length > 0) {
            const readyDoc = docs.find(d => d.status === 'Ready');
            if (readyDoc) {
                handleSelectDocument(readyDoc.id);
            }
        }
    } catch (e) {
        ui.showToast(e.message, 'error');
    }
}

function startUploadSimulation(btn) {
    const states = [
        "Uploading…",
        "Extracting text…",
        "Generating embeddings…",
        "Indexing…"
    ];
    let i = 0;
    btn.disabled = true;
    
    // Initial state
    btn.innerHTML = `<div class="upload-status flex items-center justify-center gap-sm" style="animation: slideIn 200ms ease;"><i data-lucide="loader" class="spinner"></i>${states[0]}</div>`;
    if (window.lucide) window.lucide.createIcons();
    
    uploadSimulationInterval = setInterval(() => {
        i++;
        if (i < states.length) {
            btn.innerHTML = `<div class="upload-status flex items-center justify-center gap-sm" style="animation: slideIn 200ms ease;"><i data-lucide="loader" class="spinner"></i>${states[i]}</div>`;
            if (window.lucide) window.lucide.createIcons();
        }
    }, 2000);
}

function stopUploadSimulation(btn) {
    clearInterval(uploadSimulationInterval);
    ui.resetUploadButton(btn);
}

async function handleUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    e.target.value = '';
    const btn = document.getElementById('upload-btn');
    startUploadSimulation(btn);
    
    try {
        await api.uploadDocument(file);
        ui.showToast("Document successfully processed!", 'success');
        await loadDocuments();
    } catch (e) {
        ui.showToast(e.message, 'error');
    } finally {
        stopUploadSimulation(btn);
    }
}

async function handleDeleteDocument(id) {
    if (!confirm("Are you sure you want to delete this document?")) return;
    
    try {
        await api.deleteDocument(id);
        ui.showToast("Document deleted.", 'success');
        
        if (state.currentDocumentId === id) {
            state.setCurrentDocument(null);
            ui.renderChatHeader();
            ui.toggleEmptyState(true);
        }
        
        await loadDocuments();
    } catch (e) {
        ui.showToast(e.message, 'error');
    }
}

function handleSelectDocument(id) {
    state.setCurrentDocument(id);
    ui.renderDocumentList(handleSelectDocument, handleDeleteDocument);
    ui.renderChatHeader();
    ui.toggleEmptyState(false);
    
    document.getElementById('chat-history').innerHTML = '';
}

async function handleSendMessage() {
    if (!state.currentDocumentId) {
        ui.showToast("Please select a document first.", 'error');
        return;
    }
    
    const input = document.getElementById('chat-input');
    const question = input.value.trim();
    if (!question) return;
    
    input.value = '';
    ui.appendUserMessage(question);
    ui.appendSkeletonLoader();
    
    try {
        const data = await api.askQuestion(state.currentDocumentId, question);
        ui.appendAssistantMessage(data.answer, data.sources);
    } catch (e) {
        const skeleton = document.getElementById('chat-skeleton');
        if (skeleton) skeleton.remove();
        ui.showToast(e.message, 'error');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('file-upload').addEventListener('change', handleUpload);
    document.getElementById('upload-btn').addEventListener('click', () => document.getElementById('file-upload').click());
    
    document.getElementById('chat-send-btn').addEventListener('click', handleSendMessage);
    document.getElementById('chat-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSendMessage();
    });
    
    document.getElementById('doc-search-input').addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase();
        const cards = document.querySelectorAll('.doc-card');
        cards.forEach(card => {
            const title = card.querySelector('.doc-title').textContent.toLowerCase();
            if (title.includes(query)) {
                card.style.display = 'flex';
            } else {
                card.style.display = 'none';
            }
        });
    });
    
    document.getElementById('mobile-menu-btn').addEventListener('click', () => {
        document.getElementById('sidebar').classList.toggle('open');
    });
    
    if (window.lucide) window.lucide.createIcons();
    loadDocuments();
});
