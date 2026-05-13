// PATH: static/js/main.js
/**
 * Agora AI — Global JavaScript Yardımcıları
 * Doküman Bölüm 2.2: Bootstrap 5 + Vanilla JS — React veya framework yok.
 *
 * İçerik:
 *   1. CSRF token yardımcısı (fetch için)
 *   2. Kavram tooltip API entegrasyonu (/glossary/api/)
 *   3. Zaman formatı (relative time)
 *   4. Flash mesaj yardımcıları
 *   5. Genel UI başlatıcı
 */

'use strict';

/* ─────────────────────────────────────────────────────────────────
   1. CSRF Token Yardımcısı
   ───────────────────────────────────────────────────────────────── */

/**
 * Django CSRF token'ını döndürür.
 * Meta etiketi veya cookie'den okur.
 * @returns {string}
 */
function getCsrfToken() {
    // Önce meta etiketinden dene
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    if (metaTag) return metaTag.getAttribute('content');

    // Fallback: cookie'den oku
    const cookies = document.cookie.split(';');
    for (const cookie of cookies) {
        const [key, value] = cookie.trim().split('=');
        if (key === 'csrftoken') return decodeURIComponent(value);
    }
    return '';
}

/**
 * CSRF token başlıklı fetch yardımcısı.
 * @param {string} url
 * @param {object} options - fetch options
 * @returns {Promise<Response>}
 */
async function agoraFetch(url, options = {}) {
    const defaults = {
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken(),
            ...options.headers,
        },
    };
    return fetch(url, { ...defaults, ...options });
}


/* ─────────────────────────────────────────────────────────────────
   2. Kavram Tooltip Sistemi (Glossary API entegrasyonu)
   ───────────────────────────────────────────────────────────────── */

const ConceptTooltip = (function () {
    let tooltipEl = null;
    let debounceTimer = null;
    const DEBOUNCE_MS = 400;
    const MIN_WORD_LENGTH = 4;

    function createTooltipElement() {
        const el = document.createElement('div');
        el.id = 'concept-tooltip';
        el.setAttribute('role', 'tooltip');
        Object.assign(el.style, {
            position:      'fixed',
            zIndex:        '9999',
            maxWidth:      '300px',
            padding:       '0.75rem 1rem',
            borderRadius:  '10px',
            background:    'var(--agora-dark-3)',
            border:        '1px solid var(--agora-border)',
            boxShadow:     '0 8px 24px rgba(0,0,0,0.5)',
            fontSize:      '0.83rem',
            color:         'var(--agora-text)',
            lineHeight:    '1.55',
            display:       'none',
            pointerEvents: 'none',
            fontFamily:    'var(--font-body)',
        });
        document.body.appendChild(el);
        return el;
    }

    function showTooltip(concept, x, y) {
        if (!tooltipEl) tooltipEl = createTooltipElement();

        const nameHtml = `<strong style="color:var(--agora-parchment);font-family:var(--font-serif);">${concept.name}</strong>`;
        const origHtml = concept.original_term
            ? `<em style="color:var(--agora-gold);font-size:0.75rem;"> — ${concept.original_term}</em>`
            : '';
        const defHtml  = `<p style="margin:0.4rem 0 0;">${concept.short_definition}</p>`;
        const linkHtml = `<a href="/glossary/${concept.slug}/" style="font-size:0.75rem;color:var(--agora-gold);display:block;margin-top:0.4rem;">Detaylı açıklama →</a>`;

        tooltipEl.innerHTML = nameHtml + origHtml + defHtml + linkHtml;
        tooltipEl.style.display = 'block';

        // Ekran sınırlarına göre konumlandır
        const rect = tooltipEl.getBoundingClientRect();
        const vw = window.innerWidth;
        const vh = window.innerHeight;
        let left = x + 12;
        let top  = y + 12;
        if (left + 300 > vw) left = x - 310;
        if (top + rect.height > vh) top = y - rect.height - 8;
        tooltipEl.style.left = Math.max(8, left) + 'px';
        tooltipEl.style.top  = Math.max(8, top)  + 'px';
    }

    function hideTooltip() {
        if (tooltipEl) tooltipEl.style.display = 'none';
    }

    async function lookupConcept(word) {
        if (!word || word.length < MIN_WORD_LENGTH) return null;
        try {
            const resp = await fetch(`/glossary/api/?q=${encodeURIComponent(word)}`);
            if (!resp.ok) return null;
            const data = await resp.json();
            return data.results && data.results.length > 0 ? data.results[0] : null;
        } catch (_) {
            return null;
        }
    }

    function getWordAtPoint(event) {
        if (!document.caretRangeFromPoint) return '';
        const range = document.caretRangeFromPoint(event.clientX, event.clientY);
        if (!range) return '';
        const node = range.startContainer;
        if (node.nodeType !== Node.TEXT_NODE) return '';
        const text  = node.textContent;
        const offset = range.startOffset;
        const before = text.slice(0, offset).search(/\S+$/);
        const after  = text.slice(offset).search(/\s/);
        const start  = before >= 0 ? before : 0;
        const end    = after >= 0 ? offset + after : text.length;
        return text.slice(start, end).replace(/[^a-zA-ZğüşıöçĞÜŞİÖÇ]/g, '');
    }

    function init() {
        // Yalnızca sohbet mesaj alanında tooltip göster
        document.addEventListener('mouseover', function (e) {
            const target = e.target;
            if (!target.closest('.message-bubble, .turn-bubble')) return;

            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(async () => {
                const word = getWordAtPoint(e);
                if (!word || word.length < MIN_WORD_LENGTH) return;

                const concept = await lookupConcept(word);
                if (concept) showTooltip(concept, e.clientX, e.clientY);
            }, DEBOUNCE_MS);
        });

        document.addEventListener('mouseout', function (e) {
            if (!e.target.closest('.message-bubble, .turn-bubble')) return;
            clearTimeout(debounceTimer);
            hideTooltip();
        });
    }

    return { init };
})();


/* ─────────────────────────────────────────────────────────────────
   3. Zaman Formatı (Relative Time)
   ───────────────────────────────────────────────────────────────── */

/**
 * ISO tarih stringini "X dakika önce" formatına çevirir.
 * @param {string} isoString - ISO 8601 tarih string'i
 * @returns {string}
 */
function relativeTime(isoString) {
    if (!isoString) return '';
    const date  = new Date(isoString);
    const now   = new Date();
    const diff  = Math.floor((now - date) / 1000);  // saniye

    if (diff < 60)     return 'Az önce';
    if (diff < 3600)   return `${Math.floor(diff / 60)} dakika önce`;
    if (diff < 86400)  return `${Math.floor(diff / 3600)} saat önce`;
    if (diff < 604800) return `${Math.floor(diff / 86400)} gün önce`;

    return date.toLocaleDateString('tr-TR', {
        day: 'numeric', month: 'long', year: 'numeric'
    });
}

/**
 * [data-relative-time] niteliğine sahip tüm elementleri günceller.
 */
function updateRelativeTimes() {
    document.querySelectorAll('[data-relative-time]').forEach(el => {
        const iso = el.dataset.relativeTime;
        if (iso) el.textContent = relativeTime(iso);
    });
}


/* ─────────────────────────────────────────────────────────────────
   4. Flash Mesaj Yardımcıları
   ───────────────────────────────────────────────────────────────── */

/**
 * Programatik olarak flash mesaj gösterir.
 * @param {string} message  - Mesaj metni
 * @param {'success'|'error'|'warning'|'info'} type - Mesaj tipi
 * @param {number} duration - Otomatik kapanma süresi (ms), 0 = kapatma yok
 */
function showFlash(message, type = 'info', duration = 5000) {
    const container = document.getElementById('flash-messages')
        || (() => {
            const div = document.createElement('div');
            div.id = 'flash-messages';
            div.className = 'container mt-3';
            document.querySelector('main.agora-main')?.prepend(div);
            return div;
        })();

    const iconMap = {
        success: 'fa-circle-check',
        error:   'fa-circle-xmark',
        warning: 'fa-triangle-exclamation',
        info:    'fa-circle-info',
    };

    const alert = document.createElement('div');
    alert.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show agora-alert`;
    alert.setAttribute('role', 'alert');
    alert.innerHTML = `
        <i class="fas ${iconMap[type] || iconMap.info} me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Kapat"></button>`;

    container.prepend(alert);

    if (duration > 0) {
        setTimeout(() => {
            if (typeof bootstrap !== 'undefined') {
                bootstrap.Alert.getOrCreateInstance(alert)?.close();
            } else {
                alert.remove();
            }
        }, duration);
    }
}


/* ─────────────────────────────────────────────────────────────────
   5. Genel UI Başlatıcı
   ───────────────────────────────────────────────────────────────── */

document.addEventListener('DOMContentLoaded', function () {

    // Kavram tooltip sistemini başlat
    ConceptTooltip.init();

    // Göreli zamanları güncelle
    updateRelativeTimes();
    // Her dakika yenile
    setInterval(updateRelativeTimes, 60_000);

    // Bootstrap tooltip'leri başlat (varsa)
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
            new bootstrap.Tooltip(el);
        });
    }

    // Navbar scroll efekti
    const navbar = document.getElementById('mainNav');
    if (navbar) {
        window.addEventListener('scroll', function () {
            navbar.style.boxShadow = window.scrollY > 20
                ? '0 2px 20px rgba(0,0,0,0.4)'
                : 'none';
        }, { passive: true });
    }

    // Confirm dialog'lu form submit butonları
    document.querySelectorAll('[data-confirm]').forEach(el => {
        el.addEventListener('click', function (e) {
            const msg = this.dataset.confirm || 'Emin misiniz?';
            if (!confirm(msg)) e.preventDefault();
        });
    });

});

// Global namespace
window.Agora = {
    getCsrfToken,
    agoraFetch,
    showFlash,
    relativeTime,
};
