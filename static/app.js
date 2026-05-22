/* ─── Discord Lyrics Scroller — Frontend ────────────── */

const API = '';

// ─── DOM Elements ────────────────────────────────────
const statusDot = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');
const currentText = document.getElementById('current-text');
const progressBar = document.getElementById('progress-bar');
const positionInfo = document.getElementById('position-info');
const songTitleEl = document.getElementById('song-title');
const statusCard = document.querySelector('.status-card');

const searchInput = document.getElementById('search-input');
const searchBtn = document.getElementById('search-btn');
const searchResults = document.getElementById('search-results');

const manualTitle = document.getElementById('manual-title');
const manualArtist = document.getElementById('manual-artist');
const manualLyrics = document.getElementById('manual-lyrics');
const manualStartBtn = document.getElementById('manual-start-btn');

const stopBtn = document.getElementById('stop-btn');

const settingWords = document.getElementById('setting-words');
const settingInterval = document.getElementById('setting-interval');
const settingPause = document.getElementById('setting-pause');
const settingEmoji = document.getElementById('setting-emoji');
const saveSettingsBtn = document.getElementById('save-settings-btn');

// ─── API Helpers ─────────────────────────────────────
async function apiGet(path) {
    const resp = await fetch(`${API}${path}`);
    return resp.json();
}

async function apiPost(path, body = {}) {
    const resp = await fetch(`${API}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    return resp.json();
}

async function apiPut(path, body = {}) {
    const resp = await fetch(`${API}${path}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    return resp.json();
}

// ─── Status Polling ──────────────────────────────────
let pollTimer = null;

async function updateStatus() {
    try {
        const data = await apiGet('/api/status');

        if (data.running) {
            statusDot.className = 'dot running';
            statusText.textContent = 'Воспроизведение';
            statusCard.classList.add('running');
        } else {
            statusDot.className = 'dot stopped';
            statusText.textContent = 'Остановлен';
            statusCard.classList.remove('running');
        }

        currentText.textContent = data.current_text || '—';

        const pct = data.progress || 0;
        progressBar.style.width = pct + '%';

        const sentIdx = (data.sentence_index || 0) + 1;
        const totalSent = data.total_sentences || 0;
        const wordIdx = data.word_index || 0;
        positionInfo.textContent = `Предложение ${sentIdx} / ${totalSent} · Слово ${wordIdx}`;

        songTitleEl.textContent = data.song_title || '';
    } catch (e) {
        console.error('Status poll error:', e);
    }
}

function startPolling() {
    if (pollTimer) clearInterval(pollTimer);
    updateStatus();
    pollTimer = setInterval(updateStatus, 2000);
}

// ─── Search ──────────────────────────────────────────
searchBtn.addEventListener('click', doSearch);
searchInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') doSearch();
});

async function doSearch() {
    const q = searchInput.value.trim();
    if (!q) return;

    searchBtn.disabled = true;
    searchBtn.textContent = 'Ищу...';
    searchResults.innerHTML = '';

    try {
        const data = await apiGet(`/api/search?q=${encodeURIComponent(q)}`);
        const results = data.results || [];

        if (results.length === 0) {
            searchResults.innerHTML = '<div class="result-item"><span class="result-title">Ничего не найдено</span></div>';
        } else {
            results.forEach((r) => {
                const el = document.createElement('div');
                el.className = 'result-item';
                el.innerHTML = `
                    <div class="result-title">${escHtml(r.title)}</div>
                    <div class="result-artist">${escHtml(r.artist)}</div>
                    <div class="result-source">Источник: ${r.source}</div>
                `;
                el.addEventListener('click', () => startFromSearch(r));
                searchResults.appendChild(el);
            });
        }
    } catch (e) {
        searchResults.innerHTML = '<div class="result-item"><span class="result-title">Ошибка поиска</span></div>';
    } finally {
        searchBtn.disabled = false;
        searchBtn.textContent = 'Найти';
    }
}

async function startFromSearch(result) {
    try {
        await apiPost('/api/start', {
            lyrics: result.lyrics,
            title: result.title,
            artist: result.artist,
        });
        updateStatus();
    } catch (e) {
        alert('Ошибка запуска: ' + e.message);
    }
}

// ─── Manual Start ────────────────────────────────────
manualStartBtn.addEventListener('click', async () => {
    const lyrics = manualLyrics.value.trim();
    if (!lyrics) {
        alert('Вставьте текст песни');
        return;
    }

    try {
        await apiPost('/api/start', {
            lyrics: lyrics,
            title: manualTitle.value || 'Unknown',
            artist: manualArtist.value || '',
        });
        updateStatus();
    } catch (e) {
        alert('Ошибка запуска: ' + e.message);
    }
});

// ─── Stop ────────────────────────────────────────────
stopBtn.addEventListener('click', async () => {
    try {
        await apiPost('/api/stop');
        updateStatus();
    } catch (e) {
        alert('Ошибка остановки: ' + e.message);
    }
});

// ─── Settings ────────────────────────────────────────
async function loadSettings() {
    try {
        const data = await apiGet('/api/settings');
        settingWords.value = data.words_per_tick;
        settingInterval.value = data.tick_interval;
        settingPause.value = data.pause_after_sentence;
        settingEmoji.value = data.emoji_prefix;
    } catch (e) {}
}

saveSettingsBtn.addEventListener('click', async () => {
    try {
        await apiPut('/api/settings', {
            words_per_tick: parseInt(settingWords.value),
            tick_interval: parseFloat(settingInterval.value),
            pause_after_sentence: parseFloat(settingPause.value),
            emoji_prefix: settingEmoji.value,
        });
        alert('Настройки сохранены');
    } catch (e) {
        alert('Ошибка сохранения: ' + e.message);
    }
});

// ─── Utils ───────────────────────────────────────────
function escHtml(str) {
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
}

// ─── Init ────────────────────────────────────────────
loadSettings();
startPolling();
