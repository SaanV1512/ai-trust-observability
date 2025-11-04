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
  } else {
    els.backdrop.classList.add('hidden');
    els.status.textContent = '';
  }
}

function clamp01(v) { return Math.max(0, Math.min(1, v)); }
function toPercent(v) { return Math.round(clamp01(v) * 100); }

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
    const timeout = setTimeout(() => controller.abort(), 7000);
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
    return {
      question: query,
      answer: 'Penicillin was discovered by Alexander Fleming in 1928.',
      trust_score: 0.92,
      semantic_similarity: 0.88,
      citation_coverage: 0.83,
      llm_confidence: 0.79,
      reasoning_explanation: 'The AI’s response matches multiple verified sources mentioning Alexander Fleming and penicillin in 1928.',
      sources: [
        'Wikipedia: Alexander Fleming discovered penicillin in 1928.',
        'Britannica: Penicillin discovery credited to Alexander Fleming.'
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

  els.answer.textContent = data.answer || '';
  els.reasoning.textContent = data.reasoning_explanation || '';

  els.sources.innerHTML = '';
  (data.sources || []).forEach((s) => {
    const li = document.createElement('li');
    li.textContent = s;
    els.sources.appendChild(li);
  });
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


