import { state } from './state.js';
import { formatBytes, formatDate, escapeHTML } from './helpers.js';

export function showToast(message, type = 'success') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icon = type === 'success' ? '<i data-lucide="check-circle"></i>' : '<i data-lucide="alert-circle"></i>';
    toast.innerHTML = `${icon} <span>${escapeHTML(message)}</span>`;
    
    container.appendChild(toast);
    if (window.lucide) window.lucide.createIcons();
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(10px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

export function renderDocumentList(onSelect, onDelete) {
    const container = document.getElementById('document-list');
    container.innerHTML = '';
    
    if (state.documents.length === 0) {
        container.innerHTML = `
            <div style="padding: 32px 16px; text-align: center; color: var(--text-secondary); display: flex; flex-direction: column; align-items: center; gap: 16px;">
                <div style="width: 48px; height: 48px; border-radius: 50%; background-color: var(--border-color); display: flex; align-items: center; justify-content: center; color: var(--text-tertiary);">
                    <i data-lucide="file-x" style="width: 24px; height: 24px;"></i>
                </div>
                <div>
                    <div style="font-weight: 500; color: var(--text-primary); margin-bottom: 4px;">No documents yet</div>
                    <div style="font-size: var(--font-size-xs);">Upload your first PDF to start chatting.</div>
                </div>
            </div>
        `;
        if (window.lucide) window.lucide.createIcons();
        return;
    }
    
    state.documents.forEach(doc => {
        const card = document.createElement('div');
        const isActive = state.currentDocumentId === doc.id;
        card.className = `doc-card ${isActive ? 'active' : ''}`;
        card.onclick = () => onSelect(doc.id);
        
        let statusClass = 'badge-processing';
        if (doc.status === 'Ready') statusClass = 'badge-ready';
        if (doc.status === 'Failed') statusClass = 'badge-failed';
        
        card.innerHTML = `
            <div class="doc-title" title="${escapeHTML(doc.filename)}">
                <i data-lucide="file-text" style="min-width: 18px; height: 18px; color: ${isActive ? 'var(--accent-primary)' : 'var(--text-secondary)'};"></i>
                <span style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${escapeHTML(doc.filename)}</span>
            </div>
            
            <div class="doc-meta">
                <span>${formatBytes(doc.size_bytes)}</span>
                <span>${doc.page_count} pages</span>
            </div>
            
            <div class="doc-footer">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span class="badge ${statusClass}">${doc.status}</span>
                    <span style="font-size: 11px; color: var(--text-tertiary);">${formatDate(doc.created_at)}</span>
                </div>
                <button class="delete-btn" data-id="${doc.id}" title="Delete document">
                    <i data-lucide="trash-2" style="width: 16px; height: 16px;"></i>
                </button>
            </div>
        `;
        
        container.appendChild(card);
    });
    
    // Add delete listeners
    container.querySelectorAll('.delete-btn').forEach(btn => {
        btn.onclick = (e) => {
            e.stopPropagation();
            onDelete(btn.dataset.id);
        };
    });
    
    if (window.lucide) window.lucide.createIcons();
}

export function renderChatHeader() {
    const headerContent = document.getElementById('chat-header-content');
    const doc = state.getCurrentDocument();
    
    if (!doc) {
        headerContent.innerHTML = `
            <div style="display: flex; flex-direction: column;">
                <span style="font-size: 11px; color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600;">Document</span>
                <span style="color: var(--text-secondary); font-weight: 500; font-size: var(--font-size-md);">No document selected</span>
            </div>
        `;
    } else {
        headerContent.innerHTML = `
            <i data-lucide="file-text" style="color: var(--accent-primary); width: 24px; height: 24px;"></i>
            <span style="font-weight: 600; font-size: var(--font-size-lg); color: var(--text-primary); letter-spacing: -0.01em;">${escapeHTML(doc.filename)}</span>
            <span class="badge badge-ready" style="margin-left: 12px; background-color: transparent;">Ready</span>
        `;
    }
    
    if (window.lucide) window.lucide.createIcons();
}

export function toggleEmptyState(show) {
    document.getElementById('chat-empty-state').classList.toggle('hidden', !show);
    document.getElementById('chat-history').classList.toggle('hidden', show);
}

export function appendUserMessage(text) {
    const container = document.getElementById('chat-history');
    const msg = document.createElement('div');
    msg.className = 'message user';
    msg.innerHTML = `
        <div class="message-bubble">
            ${escapeHTML(text)}
        </div>
    `;
    container.appendChild(msg);
    container.scrollTop = container.scrollHeight;
}

export function appendAssistantMessage(answer, sources) {
    const container = document.getElementById('chat-history');
    const msg = document.createElement('div');
    msg.className = 'message assistant';
    
    const parsedAnswer = window.marked ? window.marked.parse(answer) : escapeHTML(answer);
    
    let sourcesHTML = '';
    if (sources && sources.length > 0) {
        sourcesHTML = `
            <div class="sources-container">
                <div style="font-size: var(--font-size-xs); color: var(--text-secondary); margin-bottom: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">
                    <i data-lucide="library" style="width: 14px; height: 14px; display: inline-block; vertical-align: middle; margin-right: 4px;"></i> Sources
                </div>
                ${sources.map((s, i) => `
                    <div class="source-card">
                        <div class="source-header" onclick="this.parentElement.classList.toggle('open')">
                            <div class="source-meta">
                                <span>Page ${s.page}</span>
                                <span class="source-score">Relevance: ${Math.round(s.score * 100)}%</span>
                            </div>
                            <i data-lucide="chevron-down" class="source-icon" style="width: 16px; height: 16px;"></i>
                        </div>
                        <div class="source-body">
                            ${escapeHTML(s.content)}
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }
    
    msg.innerHTML = `
        <div class="message-bubble">
            ${parsedAnswer}
            ${sourcesHTML}
        </div>
    `;
    
    const skeleton = document.getElementById('chat-skeleton');
    if (skeleton) skeleton.remove();
    
    container.appendChild(msg);
    container.scrollTop = container.scrollHeight;
    if (window.lucide) window.lucide.createIcons();
}

export function appendSkeletonLoader() {
    const container = document.getElementById('chat-history');
    const msg = document.createElement('div');
    msg.className = 'message assistant';
    msg.id = 'chat-skeleton';
    msg.innerHTML = `
        <div class="message-bubble">
            <div class="skeleton skeleton-text"></div>
            <div class="skeleton skeleton-text"></div>
            <div class="skeleton skeleton-text short"></div>
        </div>
    `;
    container.appendChild(msg);
    container.scrollTop = container.scrollHeight;
}



export function resetUploadButton(btn) {
    btn.disabled = false;
    btn.innerHTML = `
        <i data-lucide="plus" id="upload-icon"></i>
        New Document
    `;
    if (window.lucide) window.lucide.createIcons();
}
