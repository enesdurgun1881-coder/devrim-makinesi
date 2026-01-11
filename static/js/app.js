/**
 * CHP Devrim Makinesi - Dashboard JavaScript
 * Real-time updates with WebSocket
 */

// ================================
// INITIALIZATION
// ================================
let socket;
let isScanning = false;

document.addEventListener('DOMContentLoaded', () => {
    initSocket();
    initTabs();
    initButtons();
    loadInitialData();
});

// ================================
// WEBSOCKET CONNECTION
// ================================
function initSocket() {
    socket = io();

    socket.on('connect', () => {
        updateConnectionStatus(true);
        addLog('🔌 Sunucuya bağlandı!', 'success');
    });

    socket.on('disconnect', () => {
        updateConnectionStatus(false);
        addLog('⚠️ Bağlantı koptu!', 'error');
    });

    socket.on('log', (data) => {
        addLog(data.mesaj, data.tip);
    });

    socket.on('progress', (data) => {
        updateProgress(data.percent, data.message);
    });

    socket.on('scan_status', (data) => {
        isScanning = data.active;
        updateScanButtons();

        if (!data.active) {
            hideProgress();
        }
    });

    socket.on('scan_complete', (data) => {
        addLog(`✅ Tarama tamamlandı! ${data.sonuclar.length} post üretildi.`, 'success');
        loadStats();
        loadGallery();
        hideProgress();
    });
}

function updateConnectionStatus(connected) {
    const statusEl = document.getElementById('connectionStatus');
    const dot = statusEl.querySelector('.status-dot');
    const text = statusEl.querySelector('.status-text');

    if (connected) {
        dot.className = 'status-dot connected';
        text.textContent = 'Bağlı';
    } else {
        dot.className = 'status-dot disconnected';
        text.textContent = 'Bağlantı Yok';
    }
}

// ================================
// TABS
// ================================
function initTabs() {
    const tabs = document.querySelectorAll('.nav-tab');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const targetId = tab.dataset.tab;

            // Update active tab
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            // Show target content
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            document.getElementById(targetId).classList.add('active');

            // Load data for specific tabs
            if (targetId === 'gallery') loadGallery();
            if (targetId === 'settings') loadSettings();
            if (targetId === 'archive') loadArchive();
        });
    });
}

// ================================
// BUTTONS
// ================================
function initButtons() {
    // Scan buttons
    document.getElementById('btnStartScan').addEventListener('click', startScan);
    document.getElementById('btnStopScan').addEventListener('click', stopScan);

    // Log clear
    document.getElementById('btnClearLog').addEventListener('click', clearLog);

    // Gallery refresh
    document.getElementById('btnRefreshGallery').addEventListener('click', loadGallery);

    // Settings save
    document.getElementById('btnSaveSettings').addEventListener('click', saveSettings);

    // Archive clear
    document.getElementById('btnClearArchive').addEventListener('click', clearArchive);

    // Modal close
    document.getElementById('modalClose').addEventListener('click', closeModal);
    document.getElementById('postModal').addEventListener('click', (e) => {
        if (e.target.id === 'postModal') closeModal();
    });

    // Editor buttons
    initEditor();
}

// ================================
// SCAN CONTROL
// ================================
function startScan() {
    if (isScanning) return;

    showProgress();
    socket.emit('start_scan');
    addLog('🚀 Tarama başlatılıyor...', 'info');
}

function stopScan() {
    socket.emit('stop_scan');
}

function updateScanButtons() {
    const startBtn = document.getElementById('btnStartScan');
    const stopBtn = document.getElementById('btnStopScan');

    startBtn.disabled = isScanning;
    stopBtn.disabled = !isScanning;

    if (isScanning) {
        startBtn.innerHTML = `
            <svg class="spinner" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"></circle>
            </svg>
            Taranıyor...
        `;
    } else {
        startBtn.innerHTML = `
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polygon points="5 3 19 12 5 21 5 3"></polygon>
            </svg>
            Taramayı Başlat
        `;
    }
}

// ================================
// PROGRESS
// ================================
function showProgress() {
    document.getElementById('progressContainer').style.display = 'block';
}

function hideProgress() {
    document.getElementById('progressContainer').style.display = 'none';
    document.getElementById('progressFill').style.width = '0%';
}

function updateProgress(percent, message) {
    document.getElementById('progressFill').style.width = `${percent}%`;
    document.getElementById('progressText').textContent = message;
}

// ================================
// LOGGING
// ================================
function addLog(message, type = 'info') {
    const container = document.getElementById('logContainer');
    const time = new Date().toLocaleTimeString('tr-TR');

    const entry = document.createElement('div');
    entry.className = `log-entry ${type}`;
    entry.innerHTML = `
        <span class="log-time">[${time}]</span>
        <span class="log-message">${message}</span>
    `;

    container.appendChild(entry);
    container.scrollTop = container.scrollHeight;

    // Limit log entries
    while (container.children.length > 100) {
        container.removeChild(container.firstChild);
    }
}

function clearLog() {
    const container = document.getElementById('logContainer');
    container.innerHTML = '';
    addLog('Log temizlendi.', 'info');
}

// ================================
// DATA LOADING
// ================================
function loadInitialData() {
    loadStats();
    loadSettings();
}

async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const stats = await response.json();

        document.getElementById('statPosts').textContent = stats.toplam_post;
        document.getElementById('statArchive').textContent = stats.arsiv_sayisi;
        document.getElementById('statRss').textContent = stats.rss_kaynak_sayisi;
        document.getElementById('statKeywords').textContent = stats.anahtar_kelime_sayisi;
        document.getElementById('targetCount').textContent = stats.hedef_haber_sayisi;
    } catch (error) {
        console.error('Stats loading error:', error);
    }
}

async function loadGallery() {
    try {
        const response = await fetch('/api/posts/detailed');
        const posts = await response.json();

        const grid = document.getElementById('galleryGrid');

        if (posts.length === 0) {
            grid.innerHTML = `
                <div class="gallery-empty">
                    <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
                        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                        <circle cx="8.5" cy="8.5" r="1.5"></circle>
                        <polyline points="21 15 16 10 5 21"></polyline>
                    </svg>
                    <p>Henüz post üretilmemiş.</p>
                </div>
            `;
            return;
        }

        grid.innerHTML = posts.map(post => `
            <div class="gallery-item" data-filename="${post.dosya}" data-caption="${encodeURIComponent(post.caption || '')}" data-baslik="${encodeURIComponent(post.baslik || '')}">
                <img src="/posts/${post.dosya}" alt="${post.dosya}" loading="lazy" onclick="openPostModal('${post.dosya}', this.parentElement)">
                <div class="gallery-overlay">
                    <p class="gallery-title">${post.baslik ? post.baslik.substring(0, 60) + '...' : post.dosya}</p>
                    <p class="gallery-date">${post.tarih}</p>
                    <div class="gallery-actions">
                        <button class="gallery-btn copy" onclick="event.stopPropagation(); copyCaption(this.closest('.gallery-item'))" title="Caption Kopyala">
                            📋 Kopyala
                        </button>
                        <button class="gallery-btn instagram" onclick="event.stopPropagation(); shareFromGallery(this.closest('.gallery-item'))" title="Instagram'a Paylaş">
                            📷
                        </button>
                        <a href="/posts/${post.dosya}" download class="gallery-btn" onclick="event.stopPropagation()">
                            ⬇️ İndir
                        </a>
                        <button class="gallery-btn delete" onclick="event.stopPropagation(); deletePost('${post.dosya}')">
                            🗑️
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Gallery loading error:', error);
    }
}

async function loadSettings() {
    try {
        const response = await fetch('/api/settings');
        const settings = await response.json();

        document.getElementById('settingTarget').value = settings.hedef_haber_sayisi || 3;
        document.getElementById('settingTextModel').value = settings.text_model || 'gemini-1.5-flash';
        document.getElementById('settingImageModel').value = settings.image_model || 'imagen-3.0-generate-001';
        document.getElementById('settingKeywords').value = (settings.anahtar_kelimeler || []).join('\n');
        document.getElementById('settingRss').value = (settings.rss_kaynaklari || []).join('\n');
    } catch (error) {
        console.error('Settings loading error:', error);
    }
}

async function loadArchive() {
    try {
        const response = await fetch('/api/archive');
        const archive = await response.json();

        document.getElementById('archiveCount').textContent = archive.length;

        const list = document.getElementById('archiveList');

        if (archive.length === 0) {
            list.innerHTML = '<p style="text-align: center; color: var(--text-muted); padding: 40px;">Arşiv boş.</p>';
            return;
        }

        list.innerHTML = archive.map(link => `
            <a href="${link}" target="_blank" class="archive-item">${link}</a>
        `).join('');
    } catch (error) {
        console.error('Archive loading error:', error);
    }
}

// ================================
// ACTIONS
// ================================
async function saveSettings() {
    const settings = {
        hedef_haber_sayisi: parseInt(document.getElementById('settingTarget').value),
        text_model: document.getElementById('settingTextModel').value,
        image_model: document.getElementById('settingImageModel').value,
        anahtar_kelimeler: document.getElementById('settingKeywords').value.split('\n').filter(k => k.trim()),
        rss_kaynaklari: document.getElementById('settingRss').value.split('\n').filter(k => k.trim())
    };

    try {
        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });

        if (response.ok) {
            addLog('✅ Ayarlar kaydedildi!', 'success');
            loadStats();
        }
    } catch (error) {
        addLog('❌ Ayarlar kaydedilemedi!', 'error');
    }
}

async function deletePost(filename) {
    if (!confirm(`${filename} silinsin mi?`)) return;

    try {
        const response = await fetch(`/api/post/${filename}`, { method: 'DELETE' });

        if (response.ok) {
            addLog(`🗑️ ${filename} silindi.`, 'warning');
            loadGallery();
            loadStats();
        }
    } catch (error) {
        addLog('❌ Silme hatası!', 'error');
    }
}

async function clearArchive() {
    if (!confirm('Tüm arşiv silinsin mi? Bu işlem geri alınamaz!')) return;

    try {
        const response = await fetch('/api/archive', { method: 'DELETE' });

        if (response.ok) {
            addLog('🗑️ Arşiv temizlendi!', 'warning');
            loadArchive();
            loadStats();
        }
    } catch (error) {
        addLog('❌ Arşiv temizlenemedi!', 'error');
    }
}

// ================================
// CAPTION COPY
// ================================
function copyCaption(galleryItem) {
    const caption = decodeURIComponent(galleryItem.dataset.caption || '');

    if (!caption) {
        showToast('⚠️ Bu post için caption bulunamadı', 'warning');
        return;
    }

    navigator.clipboard.writeText(caption).then(() => {
        showToast('✅ Caption kopyalandı!', 'success');
        addLog('📋 Caption panoya kopyalandı.', 'success');
    }).catch(err => {
        // Fallback for older browsers
        const textarea = document.createElement('textarea');
        textarea.value = caption;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        showToast('✅ Caption kopyalandı!', 'success');
    });
}

function showToast(message, type = 'info') {
    // Remove existing toast
    const existingToast = document.querySelector('.toast');
    if (existingToast) existingToast.remove();

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    toast.style.cssText = `
        position: fixed;
        bottom: 30px;
        left: 50%;
        transform: translateX(-50%);
        padding: 12px 24px;
        background: ${type === 'success' ? '#00d26a' : type === 'warning' ? '#ffcc00' : '#0099ff'};
        color: ${type === 'warning' ? '#000' : '#fff'};
        border-radius: 8px;
        font-weight: 500;
        z-index: 10000;
        animation: slideUp 0.3s ease;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    `;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'fadeOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 2500);
}

// ================================
// MODAL
// ================================
let currentPostData = null;

function openPostModal(filename, galleryItem) {
    const caption = decodeURIComponent(galleryItem.dataset.caption || '');
    const baslik = decodeURIComponent(galleryItem.dataset.baslik || '');

    currentPostData = { filename, caption, baslik };

    document.getElementById('modalImage').src = `/posts/${filename}`;
    document.getElementById('modalCaption').innerHTML = caption ?
        `<strong>📝 Caption:</strong><br>${caption.replace(/\n/g, '<br>')}` :
        '<em>Caption bulunamadı</em>';
    document.getElementById('postModal').classList.add('active');
}

function openModal(imageSrc) {
    document.getElementById('modalImage').src = imageSrc;
    document.getElementById('modalCaption').innerHTML = '';
    document.getElementById('postModal').classList.add('active');
}

function closeModal() {
    document.getElementById('postModal').classList.remove('active');
    currentPostData = null;
}

function copyModalCaption() {
    if (currentPostData && currentPostData.caption) {
        navigator.clipboard.writeText(currentPostData.caption).then(() => {
            showToast('✅ Caption kopyalandı!', 'success');
        });
    }
}

// Close modal with Escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
});

// Add CSS animation
const style = document.createElement('style');
style.textContent = `
    @keyframes slideUp {
        from { opacity: 0; transform: translateX(-50%) translateY(20px); }
        to { opacity: 1; transform: translateX(-50%) translateY(0); }
    }
    @keyframes fadeOut {
        from { opacity: 1; }
        to { opacity: 0; }
    }
    .gallery-title {
        font-weight: 600;
        font-size: 0.9rem;
        margin-bottom: 4px;
    }
    .gallery-date {
        font-size: 0.75rem;
        opacity: 0.7;
        margin-bottom: 10px;
    }
    .gallery-btn.copy {
        background: rgba(0, 210, 106, 0.3);
    }
    .gallery-btn.copy:hover {
        background: rgba(0, 210, 106, 0.5);
    }
`;
document.head.appendChild(style);

// ================================
// PHOTO EDITOR
// ================================
let editorCanvas, editorCtx;
let editorImage = null;
let currentTemplate = 'haber';
let logoImage = null;

function initEditor() {
    editorCanvas = document.getElementById('editorCanvas');
    editorCtx = editorCanvas.getContext('2d');

    // Load logo (ana dizinden)
    logoImage = new Image();
    logoImage.src = '/logo.png';
    logoImage.onerror = () => { logoImage = null; };

    // Image upload
    document.getElementById('imageUpload').addEventListener('change', handleImageUpload);

    // Template selection
    document.querySelectorAll('.template-item').forEach(item => {
        item.addEventListener('click', () => {
            document.querySelectorAll('.template-item').forEach(i => i.classList.remove('active'));
            item.classList.add('active');
            currentTemplate = item.dataset.template;
            renderEditor();
        });
    });

    // Text changes
    document.getElementById('editorTitle').addEventListener('input', renderEditor);
    document.getElementById('editorSubtitle').addEventListener('input', renderEditor);
    document.getElementById('editorFontSize').addEventListener('input', renderEditor);
    document.getElementById('editorTextPosition').addEventListener('change', renderEditor);

    // Checkboxes
    document.getElementById('editorShowLogo').addEventListener('change', renderEditor);
    document.getElementById('editorShowBrand').addEventListener('change', renderEditor);
    document.getElementById('editorShowGradient').addEventListener('change', renderEditor);

    // Filters
    document.getElementById('filterBrightness').addEventListener('input', renderEditor);
    document.getElementById('filterContrast').addEventListener('input', renderEditor);
    document.getElementById('filterSaturation').addEventListener('input', renderEditor);
    document.getElementById('filterBlur').addEventListener('input', renderEditor);
    document.getElementById('btnResetFilters').addEventListener('click', resetFilters);

    // Color pickers
    document.getElementById('colorText').addEventListener('input', renderEditor);
    document.getElementById('colorShadow').addEventListener('input', renderEditor);
    document.getElementById('colorAccent').addEventListener('input', renderEditor);

    // Buttons
    document.getElementById('btnApplyTemplate').addEventListener('click', renderEditor);
    document.getElementById('btnResetEditor').addEventListener('click', resetEditor);
    document.getElementById('btnDownloadDesign').addEventListener('click', downloadDesign);
    document.getElementById('btnSaveDesign').addEventListener('click', saveDesignAsPost);
    document.getElementById('btnGenerateAI').addEventListener('click', generateAIImage);
    document.getElementById('btnSelectFromGallery').addEventListener('click', openGallerySelectModal);

    // Gallery selection modal
    document.getElementById('gallerySelectClose').addEventListener('click', closeGallerySelectModal);
    document.getElementById('gallerySelectModal').addEventListener('click', (e) => {
        if (e.target.id === 'gallerySelectModal') closeGallerySelectModal();
    });

    // Instagram share from editor
    const shareBtn = document.getElementById('btnShareInstagram');
    if (shareBtn) shareBtn.addEventListener('click', shareEditorToInstagram);
}

function handleImageUpload(e) {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
        editorImage = new Image();
        editorImage.onload = () => {
            showCanvas();
            renderEditor();
        };
        editorImage.src = event.target.result;
    };
    reader.readAsDataURL(file);
}

function showCanvas() {
    document.getElementById('previewPlaceholder').style.display = 'none';
    editorCanvas.style.display = 'block';
}

function renderEditor() {
    if (!editorImage) return;

    const size = 1080;
    editorCanvas.width = size;
    editorCanvas.height = size;

    // Get filter values
    const brightness = document.getElementById('filterBrightness').value;
    const contrast = document.getElementById('filterContrast').value;
    const saturation = document.getElementById('filterSaturation').value;
    const blur = document.getElementById('filterBlur').value;

    // Apply CSS filters
    editorCtx.filter = `brightness(${brightness}%) contrast(${contrast}%) saturate(${saturation}%) blur(${blur}px)`;

    // Draw base image
    const imgRatio = editorImage.width / editorImage.height;
    let sx = 0, sy = 0, sw = editorImage.width, sh = editorImage.height;

    if (imgRatio > 1) {
        sx = (editorImage.width - editorImage.height) / 2;
        sw = editorImage.height;
    } else if (imgRatio < 1) {
        sy = (editorImage.height - editorImage.width) / 2;
        sh = editorImage.width;
    }

    editorCtx.drawImage(editorImage, sx, sy, sw, sh, 0, 0, size, size);

    // Reset filter for overlays
    editorCtx.filter = 'none';

    // Apply template overlay
    applyTemplate(currentTemplate);

    // Draw text
    drawText();

    // Draw logo (sağ alt köşe, eşit mesafe)
    if (document.getElementById('editorShowLogo').checked && logoImage) {
        const logoSize = size * 0.22;  // %22 - dengeli boyut
        const margin = 40;  // Kenarlardan eşit mesafe
        const logoRatio = logoImage.width / logoImage.height;
        const lw = logoSize;
        const lh = logoSize / logoRatio;
        editorCtx.drawImage(logoImage, size - lw - margin, size - lh - margin, lw, lh);
    }

    // Draw brand with accent color
    if (document.getElementById('editorShowBrand').checked) {
        const accentColor = document.getElementById('colorAccent').value;
        editorCtx.font = 'bold 24px Inter, sans-serif';
        editorCtx.fillStyle = accentColor;
        editorCtx.fillText('DAILY CHP', 50, 50);
    }
}

function applyTemplate(template) {
    const size = 1080;
    const showGradient = document.getElementById('editorShowGradient').checked;

    if (!showGradient && template === 'haber') return;

    switch (template) {
        case 'haber':
            // Bottom gradient
            const gradBottom = editorCtx.createLinearGradient(0, size * 0.4, 0, size);
            gradBottom.addColorStop(0, 'rgba(0,0,0,0)');
            gradBottom.addColorStop(1, 'rgba(0,0,0,0.85)');
            editorCtx.fillStyle = gradBottom;
            editorCtx.fillRect(0, 0, size, size);

            // Top gradient
            const gradTop = editorCtx.createLinearGradient(0, 0, 0, 120);
            gradTop.addColorStop(0, 'rgba(0,0,0,0.7)');
            gradTop.addColorStop(1, 'rgba(0,0,0,0)');
            editorCtx.fillStyle = gradTop;
            editorCtx.fillRect(0, 0, size, 120);
            break;

        case 'duyuru':
            const gradDuyuru = editorCtx.createLinearGradient(0, 0, size, size);
            gradDuyuru.addColorStop(0, 'rgba(227,10,23,0.7)');
            gradDuyuru.addColorStop(1, 'rgba(0,51,102,0.7)');
            editorCtx.fillStyle = gradDuyuru;
            editorCtx.fillRect(0, 0, size, size);
            break;

        case 'alinti':
            editorCtx.fillStyle = 'rgba(0,0,0,0.6)';
            editorCtx.fillRect(0, 0, size, size);

            // Quote mark
            editorCtx.font = 'bold 200px serif';
            editorCtx.fillStyle = 'rgba(227,10,23,0.3)';
            editorCtx.fillText('"', 50, 200);
            break;

        case 'minimal':
            // Just a subtle vignette
            const gradVig = editorCtx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size * 0.7);
            gradVig.addColorStop(0, 'rgba(0,0,0,0)');
            gradVig.addColorStop(1, 'rgba(0,0,0,0.5)');
            editorCtx.fillStyle = gradVig;
            editorCtx.fillRect(0, 0, size, size);
            break;
    }
}

function drawText() {
    const size = 1080;
    const title = document.getElementById('editorTitle').value;
    const subtitle = document.getElementById('editorSubtitle').value;
    const fontSize = parseInt(document.getElementById('editorFontSize').value);
    const position = document.getElementById('editorTextPosition').value;

    // Get colors from pickers
    const textColor = document.getElementById('colorText').value;
    const shadowColor = document.getElementById('colorShadow').value;
    const accentColor = document.getElementById('colorAccent').value;

    if (!title) return;

    editorCtx.font = `bold ${fontSize}px Inter, sans-serif`;
    editorCtx.textBaseline = 'top';

    const maxWidth = size - 100;
    const lines = wrapText(title, maxWidth);
    const lineHeight = fontSize + 10;

    let startY;
    switch (position) {
        case 'top':
            startY = 100;
            break;
        case 'center':
            startY = (size - lines.length * lineHeight) / 2;
            break;
        case 'bottom':
        default:
            startY = size - lines.length * lineHeight - 180;
    }

    // Accent line with picked color
    if (currentTemplate === 'haber') {
        editorCtx.fillStyle = accentColor;
        editorCtx.fillRect(50, startY - 20, 100, 4);
    }

    // Draw text with shadow using picked colors
    lines.forEach((line, i) => {
        const y = startY + i * lineHeight;
        // Shadow
        editorCtx.fillStyle = shadowColor + '80';  // 50% opacity
        editorCtx.fillText(line, 52, y + 2);
        // Main text
        editorCtx.fillStyle = textColor;
        editorCtx.fillText(line, 50, y);
    });

    // Subtitle
    if (subtitle) {
        editorCtx.font = '20px Inter, sans-serif';
        editorCtx.fillStyle = textColor + 'B3';  // 70% opacity
        editorCtx.fillText(subtitle, 50, startY + lines.length * lineHeight + 10);
    }
}

function wrapText(text, maxWidth) {
    const words = text.split(' ');
    const lines = [];
    let line = '';

    words.forEach(word => {
        const testLine = line + (line ? ' ' : '') + word;
        const metrics = editorCtx.measureText(testLine);

        if (metrics.width > maxWidth && line) {
            lines.push(line);
            line = word;
        } else {
            line = testLine;
        }
    });

    if (line) lines.push(line);
    return lines;
}

function resetEditor() {
    editorImage = null;
    document.getElementById('previewPlaceholder').style.display = 'flex';
    editorCanvas.style.display = 'none';
    document.getElementById('editorTitle').value = '';
    document.getElementById('editorSubtitle').value = '';
    document.getElementById('imageUpload').value = '';
    showToast('🔄 Editör sıfırlandı', 'info');
}

function downloadDesign() {
    if (!editorImage) {
        showToast('⚠️ Önce bir görsel yükleyin', 'warning');
        return;
    }

    const link = document.createElement('a');
    link.download = `design_${Date.now()}.jpg`;
    link.href = editorCanvas.toDataURL('image/jpeg', 0.95);
    link.click();
    showToast('⬇️ Tasarım indirildi!', 'success');
}

async function saveDesignAsPost() {
    if (!editorImage) {
        showToast('⚠️ Önce bir görsel yükleyin', 'warning');
        return;
    }

    const dataUrl = editorCanvas.toDataURL('image/jpeg', 0.95);
    const title = document.getElementById('editorTitle').value;

    try {
        const response = await fetch('/api/editor/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: dataUrl, title: title })
        });

        const result = await response.json();
        if (result.success) {
            showToast('💾 Post olarak kaydedildi!', 'success');
            addLog(`💾 Editör tasarımı kaydedildi: ${result.filename}`, 'success');
            loadStats();
        }
    } catch (error) {
        showToast('❌ Kayıt hatası', 'error');
    }
}

async function generateAIImage() {
    showToast('🤖 AI görsel oluşturuluyor...', 'info');
    addLog('🤖 AI görsel isteniyor...', 'info');

    try {
        const response = await fetch('/api/editor/generate-ai');
        const result = await response.json();

        if (result.success && result.image) {
            editorImage = new Image();
            editorImage.onload = () => {
                showCanvas();
                renderEditor();

                if (result.fallback) {
                    showToast('⚠️ ' + result.message, 'warning');
                    addLog('⚠️ AI hatası, mevcut görsel kullanıldı', 'warning');
                } else {
                    showToast('✅ AI görsel hazır!', 'success');
                    addLog('✅ AI görsel oluşturuldu!', 'success');
                }
            };
            // JPEG için farklı prefix kullan
            const prefix = result.fallback ? 'data:image/jpeg;base64,' : 'data:image/png;base64,';
            editorImage.src = prefix + result.image;
        } else {
            showToast('❌ ' + (result.error || 'AI görsel oluşturulamadı'), 'error');
            addLog('❌ AI Hatası: ' + result.error, 'error');
        }
    } catch (error) {
        showToast('❌ AI bağlantı hatası', 'error');
        addLog('❌ AI bağlantı hatası: ' + error.message, 'error');
    }
}

function selectFromGallery() {
    // Switch to gallery tab and add selection mode
    document.querySelector('[data-tab="gallery"]').click();
    showToast('📸 Bir görsel seçin, sonra editöre dönün', 'info');
}

// ================================
// GALLERY SELECTION MODAL
// ================================
async function openGallerySelectModal() {
    const modal = document.getElementById('gallerySelectModal');
    const grid = document.getElementById('gallerySelectGrid');

    try {
        const response = await fetch('/api/posts');
        const posts = await response.json();

        if (posts.length === 0) {
            grid.innerHTML = '<p style="text-align: center; padding: 40px; color: var(--text-muted);">Galeri boş.</p>';
        } else {
            grid.innerHTML = posts.map(post => `
                <div class="gallery-item" onclick="selectImageForEditor('/posts/${post.dosya}')" style="cursor: pointer;">
                    <img src="/posts/${post.dosya}" alt="${post.dosya}" loading="lazy">
                    <div class="gallery-overlay">
                        <p>${post.dosya}</p>
                    </div>
                </div>
            `).join('');
        }

        modal.classList.add('active');
    } catch (error) {
        showToast('❌ Galeri yüklenemedi', 'error');
    }
}

function closeGallerySelectModal() {
    document.getElementById('gallerySelectModal').classList.remove('active');
}

function selectImageForEditor(imageSrc) {
    closeGallerySelectModal();
    showToast('🖼️ Görsel yükleniyor...', 'info');

    editorImage = new Image();
    editorImage.crossOrigin = 'anonymous';
    editorImage.onload = () => {
        showCanvas();
        renderEditor();
        showToast('✅ Görsel editöre yüklendi!', 'success');
    };
    editorImage.onerror = () => {
        showToast('❌ Görsel yüklenemedi', 'error');
    };
    editorImage.src = imageSrc;
}

// ================================
// FILTER HELPERS
// ================================
function resetFilters() {
    document.getElementById('filterBrightness').value = 100;
    document.getElementById('filterContrast').value = 100;
    document.getElementById('filterSaturation').value = 100;
    document.getElementById('filterBlur').value = 0;
    renderEditor();
    showToast('🔄 Filtreler sıfırlandı', 'info');
}

// ================================
// EDITOR INSTAGRAM SHARE
// ================================
async function shareEditorToInstagram() {
    if (!editorImage) {
        showToast('⚠️ Önce bir görsel yükleyin', 'warning');
        return;
    }

    // Önce kaydet, sonra paylaş
    const dataUrl = editorCanvas.toDataURL('image/jpeg', 0.95);
    const title = document.getElementById('editorTitle').value || 'Editör Tasarımı';

    showToast('💾 Kaydediliyor ve paylaşılıyor...', 'info');

    try {
        // Save first
        const saveResponse = await fetch('/api/editor/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: dataUrl, title: title })
        });

        const saveResult = await saveResponse.json();

        if (saveResult.success) {
            // Now share to Instagram
            const shareResponse = await fetch('/api/instagram/share', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    filename: saveResult.filename,
                    caption: title
                })
            });

            const shareResult = await shareResponse.json();

            if (shareResult.success) {
                showToast('✅ Instagram\'a paylaşıldı!', 'success');
                addLog('📷 Editör tasarımı Instagram\'a paylaşıldı!', 'success');
            } else {
                showToast('❌ ' + shareResult.error, 'error');
            }
        }
    } catch (error) {
        showToast('❌ Paylaşım hatası', 'error');
    }
}

// ================================
// INSTAGRAM INTEGRATION
// ================================
function initInstagram() {
    // Instagram buttons
    const loginBtn = document.getElementById('btnInstaLogin');
    const logoutBtn = document.getElementById('btnInstaLogout');

    if (loginBtn) loginBtn.addEventListener('click', instagramLogin);
    if (logoutBtn) logoutBtn.addEventListener('click', instagramLogout);

    // Check status on load
    checkInstagramStatus();
}

async function checkInstagramStatus() {
    try {
        const response = await fetch('/api/instagram/status');
        const data = await response.json();

        const statusEl = document.getElementById('instagramStatus');
        if (!statusEl) return;

        if (data.connected) {
            statusEl.innerHTML = `
                <span class="status-dot connected"></span>
                <span>@${data.username} bağlı (${data.followers} takipçi)</span>
            `;
        } else {
            statusEl.innerHTML = `
                <span class="status-dot disconnected"></span>
                <span>Bağlı değil</span>
            `;
        }
    } catch (error) {
        console.error('Instagram status error:', error);
    }
}

async function instagramLogin() {
    const username = document.getElementById('settingInstaUser').value;
    const password = document.getElementById('settingInstaPass').value;

    if (!username || !password) {
        showToast('⚠️ Kullanıcı adı ve şifre girin', 'warning');
        return;
    }

    // Önce ayarları kaydet
    const settings = await fetch('/api/settings').then(r => r.json());
    settings.instagram_username = username;
    settings.instagram_password = password;

    await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
    });

    showToast('🔐 Instagram\'a giriş yapılıyor...', 'info');
    addLog('🔐 Instagram\'a giriş yapılıyor...', 'info');

    try {
        const response = await fetch('/api/instagram/login', { method: 'POST' });
        const data = await response.json();

        if (data.success) {
            showToast('✅ ' + data.message, 'success');
            addLog('✅ ' + data.message, 'success');
            checkInstagramStatus();
        } else {
            showToast('❌ ' + data.error, 'error');
            addLog('❌ Instagram giriş hatası: ' + data.error, 'error');
        }
    } catch (error) {
        showToast('❌ Bağlantı hatası', 'error');
    }
}

async function instagramLogout() {
    try {
        await fetch('/api/instagram/logout', { method: 'POST' });
        showToast('🚪 Instagram çıkışı yapıldı', 'info');
        checkInstagramStatus();
    } catch (error) {
        showToast('❌ Çıkış hatası', 'error');
    }
}

async function shareToInstagram(filename, encodedCaption) {
    const caption = decodeURIComponent(encodedCaption || '');

    if (!confirm(`"${filename}" Instagram'a paylaşılsın mı?`)) return;

    showToast('📷 Instagram\'a paylaşılıyor...', 'info');
    addLog(`📷 Instagram'a paylaşılıyor: ${filename}`, 'info');

    try {
        const response = await fetch('/api/instagram/share', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename, caption })
        });

        const data = await response.json();

        if (data.success) {
            showToast('✅ Instagram\'a paylaşıldı!', 'success');
            addLog('✅ ' + data.message, 'success');
        } else {
            showToast('❌ ' + data.error, 'error');
            addLog('❌ Instagram paylaşım hatası: ' + data.error, 'error');
        }
    } catch (error) {
        showToast('❌ Paylaşım hatası', 'error');
    }
}

// Galeriden paylaşım için yardımcı fonksiyon
function shareFromGallery(galleryItem) {
    const filename = galleryItem.dataset.filename;
    const caption = galleryItem.dataset.caption || '';
    console.log('📷 Sharing from gallery:', filename);
    shareToInstagram(filename, caption);
}

// Add Instagram button style
const instaStyle = document.createElement('style');
instaStyle.textContent = `
    .gallery-btn.instagram {
        background: linear-gradient(45deg, #f09433 0%, #e6683c 25%, #dc2743 50%, #cc2366 75%, #bc1888 100%);
    }
    .gallery-btn.instagram:hover {
        transform: scale(1.1);
    }
    .instagram-status {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 12px;
        background: var(--bg-primary);
        border-radius: var(--radius-md);
        margin-bottom: 16px;
    }
`;
document.head.appendChild(instaStyle);

// Initialize Instagram on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(initInstagram, 100);
});

async function importSession() {
    const jsonContent = document.getElementById('settingSessionJson').value;
    if (!jsonContent) {
        alert("Lütfen JSON içeriğini kutuya yapıştırın!");
        return;
    }

    // Basit JSON formatı kontrolü
    try {
        JSON.parse(jsonContent);
    } catch (e) {
        alert("Yapıştırdığınız veri geçerli bir JSON değil! Lütfen tüm içeriği kopyaladığınızdan emin olun.");
        return;
    }

    // Butonu disable et
    const btn = document.querySelector('button[onclick="importSession()"]');
    const originalText = btn.innerHTML;
    btn.innerHTML = '⏳ Yükleniyor...';
    btn.disabled = true;

    try {
        const res = await fetch('/api/instagram/import_session', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_json: jsonContent })
        });

        const data = await res.json();

        if (data.success) {
            alert("✅ Session başarıyla yüklendi ve giriş yapıldı!");
            location.reload();
        } else {
            alert("❌ Hata: " + data.error);
        }
    } catch (e) {
        alert("⚠️ Bağlantı hatası: " + e);
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}
