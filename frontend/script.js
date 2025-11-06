const API_URL = 'http://localhost:8000/evaluate';
const GAUGE_CIRCUMFERENCE = 2 * Math.PI * 54;

const els = {
  query: document.getElementById('query'),
  analyzeBtn: document.getElementById('analyzeBtn'),
  status: document.getElementById('status'),
  toast: document.getElementById('toast'),
  backdrop: document.getElementById('backdrop'),
  trustPercent: document.getElementById('trustPercent'),
  gaugeFg: document.querySelector('.gauge-fg'),
  semanticBar: document.getElementById('semanticBar'),
  citationBar: document.getElementById('citationBar'),
  confidenceBar: document.getElementById('confidenceBar'),
  semanticVal: document.getElementById('semanticVal'),
  citationVal: document.getElementById('citationVal'),
  confidenceVal: document.getElementById('confidenceVal'),
  answer: document.getElementById('answer'),
  reasoning: document.getElementById('reasoning'),
  sources: document.getElementById('sources')
};

function showToast(message, timeout = 2200) {
  els.toast.textContent = message;
  els.toast.classList.add('show');
  window.setTimeout(() => els.toast.classList.remove('show'), timeout);
}

function setLoading(isLoading) {
  if (isLoading) {
    els.backdrop.classList.remove('hidden');
    els.status.textContent = 'Analyzing…';
    els.analyzeBtn.disabled = true;
    els.analyzeBtn.dataset.originalText = els.analyzeBtn.textContent;
    els.analyzeBtn.textContent = 'Analyzing…';
  } else {
    els.backdrop.classList.add('hidden');
    els.status.textContent = '';
    els.analyzeBtn.disabled = false;
    if (els.analyzeBtn.dataset.originalText) {
      els.analyzeBtn.textContent = els.analyzeBtn.dataset.originalText;
      delete els.analyzeBtn.dataset.originalText;
    }
  }
}

function clamp01(v) { return Math.max(0, Math.min(1, v)); }
function toPercent(v) { return Math.round(clamp01(v) * 100); }

function formatMarkdown(text) {
  if (!text) return '';

  // Escape HTML to prevent XSS (but preserve already escaped entities)
  let html = text
    .replace(/&(?![a-zA-Z0-9#]+;)/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  // Convert markdown bold (**text** or __text__) to HTML
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/__(.+?)__/g, '<strong>$1</strong>');

  // Convert numbered lists (1. item) to HTML
  html = html.replace(/^\d+\.\s+(.+)$/gm, '<li>$1</li>');

  // Convert bulleted lists (- item or * item) to HTML  
  html = html.replace(/^[-*]\s+(.+)$/gm, '<li>$1</li>');

  // Wrap consecutive <li> elements in <ul> tags
  html = html.replace(/(<li>.*?<\/li>(\s|$))+/g, '<ul>$&</ul>');

  // Convert single newlines within paragraphs to spaces (preserve double newlines)
  // First, protect list blocks
  const listBlocks = [];
  html = html.replace(/<ul>.*?<\/ul>/gs, (match) => {
    listBlocks.push(match);
    return `__LIST_BLOCK_${listBlocks.length - 1}__`;
  });

  // Convert double newlines to paragraph breaks, single newlines to <br>
  html = html.replace(/\n\n+/g, '</p><p>');
  html = html.replace(/\n/g, '<br>');

  // Restore list blocks
  listBlocks.forEach((block, i) => {
    html = html.replace(`__LIST_BLOCK_${i}__`, block);
  });

  // Wrap in paragraph tags if not already wrapped
  if (!html.startsWith('<ul>') && !html.startsWith('<p>')) {
    html = '<p>' + html + '</p>';
  }

  // Clean up empty paragraphs
  html = html.replace(/<p>\s*<\/p>/g, '');
  html = html.replace(/<p><br><\/p>/g, '');

  return html;
}

function colorForPercent(p) {
  if (p >= 80) return '#22c55e';
  if (p >= 60) return '#f59e0b';
  return '#ef4444';
}

function animateGauge(percent) {
  const p = clamp01(percent) * 100;
  const color = colorForPercent(p);

  els.trustPercent.textContent = `${Math.round(p)}%`;
  els.gaugeFg.style.strokeDasharray = `${GAUGE_CIRCUMFERENCE}`;
  const offset = GAUGE_CIRCUMFERENCE * (1 - p / 100);
  els.gaugeFg.animate([
    { strokeDashoffset: `${GAUGE_CIRCUMFERENCE}` },
    { strokeDashoffset: `${offset}` }
  ], { duration: 900, easing: 'cubic-bezier(.2,.8,.2,1)', fill: 'forwards' });
  els.gaugeFg.style.stroke = `conic-gradient(${color}, ${color})`;
  els.gaugeFg.style.stroke = color;
}

function animateBar(el, value, valEl) {
  const p = toPercent(value);
  el.style.width = '0%';
  el.animate([
    { width: '0%' },
    { width: `${p}%` }
  ], { duration: 800, easing: 'ease' });
  window.setTimeout(() => { el.style.width = `${p}%`; }, 0);
  if (valEl) valEl.textContent = `${p}%`;
}

async function fetchAnalysis(query) {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 60 * 1000);
    const res = await fetch(API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query }),
      signal: controller.signal
    });
    clearTimeout(timeout);

    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (e) {
    console.log(e);
    return {
      question: query,
      answer: 'Penicillin was discovered by Alexander Fleming in 1928.',
      trust_score: 0.92,
      semantic_similarity: 0.88,
      citation_coverage: 0.83,
      llm_confidence: 0.79,
      reasoning_explanation: 'The AI’s response matches multiple verified sources mentioning Alexander Fleming and penicillin in 1928.',
      sources: [
        { title: 'Wikipedia: Alexander Fleming', url: 'https://en.wikipedia.org/wiki/Alexander_Fleming' },
        { title: 'Britannica: Penicillin', url: 'https://www.britannica.com/science/penicillin' }
      ],
      _fallback: true
    };
  }
}

function renderResults(data) {
  const trust = Number(data.trust_score || 0);
  const semantic = Number(data.semantic_similarity || 0);
  const citation = Number(data.citation_coverage || 0);
  const confidence = Number(data.llm_confidence || 0);

  animateGauge(trust);
  animateBar(els.semanticBar, semantic, els.semanticVal);
  animateBar(els.citationBar, citation, els.citationVal);
  animateBar(els.confidenceBar, confidence, els.confidenceVal);

  // Convert markdown to HTML for answer display
  const answerText = data.answer || '';
  // Typing animation for answer
  typeAnswer(answerText, 10);
  els.reasoning.textContent = data.reasoning_explanation || '';

  els.sources.innerHTML = '';
  (data.sources || []).forEach((source) => {
    const li = document.createElement('li');

    // Handle both object format (new) and string format (fallback)
    if (typeof source === 'object' && source.title) {
      const link = document.createElement('a');
      link.href = source.url || '#';
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      link.textContent = source.title;
      link.className = 'source-link';
      if (source.url) {
        li.appendChild(link);
      } else {
        li.textContent = source.title;
      }
    } else {
      // Fallback for string format (dummy data)
      li.textContent = source;
    }

    els.sources.appendChild(li);
  });
}

// Typewriter effect for answer with basic markdown formatting support
function typeAnswer(fullText, speed = 12) {
  const text = fullText || '';
  let i = 0;
  const step = () => {
    const slice = text.slice(0, i);
    els.answer.innerHTML = formatMarkdown(slice);
    i += 2; // increment faster for better UX
    if (i <= text.length) {
      requestAnimationFrame(step);
    }
  };
  els.answer.innerHTML = '';
  requestAnimationFrame(step);
}

async function onAnalyze() {
  const q = (els.query.value || '').trim();
  if (!q) {
    showToast('Please enter a question.');
    els.query.focus();
    return;
  }
  setLoading(true);
  try {
    const data = await fetchAnalysis(q);
    renderResults(data);
    if (data._fallback) showToast('Backend unavailable — showing dummy results.');
  } catch (err) {
    console.log(err);
    showToast('Something went wrong. Please try again.');
  } finally {
    setLoading(false);
  }
}

els.query.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') onAnalyze();
});
els.analyzeBtn.addEventListener('click', onAnalyze);

window.addEventListener('DOMContentLoaded', () => {
  if (els.gaugeFg) {
    els.gaugeFg.setAttribute('stroke-dasharray', `${GAUGE_CIRCUMFERENCE}`);
    els.gaugeFg.setAttribute('stroke-dashoffset', `${GAUGE_CIRCUMFERENCE}`);
  }
});


