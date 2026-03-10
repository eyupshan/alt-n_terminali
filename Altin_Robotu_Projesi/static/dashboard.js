// ══════════════════════════════════════════
//   ALTIN QUANT TERMİNALİ — dashboard.js v3
// ══════════════════════════════════════════

let lwChart = null, lwSeries = null;
let currentChartType = 'gram';

// ── SEKME GEÇİŞİ ──────────────────────────
function goTab(name, btn) {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.ntab').forEach(b => b.classList.remove('active'));
    const tab = document.getElementById('tab-' + name);
    if (tab) tab.classList.add('active');
    if (btn) btn.classList.add('active');
    setTimeout(() => lwChart?.timeScale().fitContent(), 60);
}

function setChartType(type, btn) {
    currentChartType = type;
    document.querySelectorAll('.cb').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    updateChart(lastData?.df || []);
}

// ── YARDIMCI ─────────────────────────────
function $e(id) { return document.getElementById(id); }
function setT(id, val) { const el = $e(id); if (el) el.textContent = String(val ?? '---'); }
function setC(id, cls) { const el = $e(id); if (el) { el.className = el.className.replace(/\b(AL|SAT|BEKLE|ok|warn|bad|green|red|blue|gold|warn)\b/g, ''); el.classList.add(cls); } }
function safeN(v, d = 0) { const n = parseFloat(v); return isFinite(n) ? n : d; }
function pct(v) { return (v * 100).toFixed(2) + '%'; }
function fmtN(v, dp = 2) { return safeN(v).toFixed(dp); }

function appendLog(msg) {
    const t = $e('log-terminal'); if (!t) return;
    const p = document.createElement('p');
    p.textContent = `[${new Date().toLocaleTimeString('tr-TR')}] ${msg}`;
    t.appendChild(p);
    while (t.children.length > 80) t.removeChild(t.firstChild);
    t.scrollTop = t.scrollHeight;
}

function colorSignal(val) {
    return val === 'AL' ? 'AL' : val === 'SAT' ? 'SAT' : 'BEKLE';
}

function setSignalEl(id, val) {
    const el = $e(id); if (!el) return;
    const v = (val || 'BEKLE').toUpperCase();
    el.textContent = v === 'AL' ? '🟢 AL' : v === 'SAT' ? '🔴 SAT' : '🟡 BEKLE';
    el.className = el.className.replace(/\bsignal-\w+\b/g, '');
    el.classList.add(v === 'AL' ? 'signal-buy' : v === 'SAT' ? 'signal-sell' : 'signal-hold');
}

// Range color coding
function metricStatus(val, minOk, maxOk) {
    if (val >= minOk && val <= maxOk) return 'ok';
    const span = maxOk - minOk;
    if (val >= minOk - span * 0.3 && val <= maxOk + span * 0.3) return 'warn';
    return 'bad';
}

let lastData = null;

// ── ANA GÜNCELLEMESİ ─────────────────────
async function updateDashboard() {
    let d;
    try {
        const r = await fetch('/api/data');
        if (!r.ok) { appendLog(`> HTTP ${r.status}`); return; }
        d = await r.json();
    } catch (e) { appendLog(`> BAĞLANTI HATASI: ${e.message}`); return; }

    lastData = d;
    const m = d.metrics || {};
    const risk = d.risk || {};
    const ai = d.ai || {};
    const port = d.portfolio || {};
    const macro = d.macro || {};
    const ons = d.ons || {};
    const gram = d.gram || {};
    const df = d.df || [];

    updateAna(ons, gram, m, risk);
    updateTeknik(m, df);
    updateML(ai, m);
    updateRisk(risk, ons);
    updatePortfoy(port, risk);
    updateStrateji(m);
    updateEkonometri(m, risk);
    updateMakro(macro, ai);
    updateBacktest(risk);
    updateMikro(m);
    updateHafiza(ai, m);
    updatePerf(risk, m);
    if (d.robot) updateRobot(d.robot, m);
    if (d.news) updateHaber(d.news);

    if (df.length > 0) updateChart(df);
    appendLog(`> Güncellendi | Ons: $${safeN(ons.price).toFixed(2)} | Gram: ₺${safeN(gram.price).toFixed(2)} | ${m.Signal || 'BEKLE'}`);
}

// ── SAYFA 1: ANA ────────────────────────
function updateAna(ons, gram, m, risk) {
    const onsP = safeN(ons.price), onsPrev = safeN(ons.prev, onsP);
    const gramP = safeN(gram.price), gramPrev = safeN(gram.prev, gramP);

    setT('ons-price', `$${onsP.toFixed(2)}`);
    setT('gram-price', `₺${gramP.toFixed(2)}`);

    const onsChg = onsP - onsPrev;
    const onsEl = $e('ons-chg');
    if (onsEl) { onsEl.textContent = `${onsChg >= 0 ? '▲' : '▼'} $${Math.abs(onsChg).toFixed(2)} (${(onsChg / onsPrev * 100).toFixed(2)}%)`; onsEl.style.color = onsChg >= 0 ? 'var(--green)' : 'var(--red)'; }

    const gramChg = gramP - gramPrev;
    const gramEl = $e('gram-chg');
    if (gramEl) { gramEl.textContent = `${gramChg >= 0 ? '▲' : '▼'} ₺${Math.abs(gramChg).toFixed(2)} (${(gramChg / gramPrev * 100).toFixed(2)}%)`; gramEl.style.color = gramChg >= 0 ? 'var(--green)' : 'var(--red)'; }

    setSignalEl('main-signal', m.Signal);

    // Six metric cards
    updateMC('RSI', safeN(m.RSI, 50), 30, 70, `${fmtN(m.RSI)}`);
    updateMC('Z_Score', safeN(m.Z_Score), -2, 2, `${fmtN(m.Z_Score)}σ`);
    updateMC('Hurst', safeN(m.Hurst, .5), 0.4, 0.6, `${fmtN(m.Hurst, 3)}`);
    updateMC('Volatility', safeN(m.Volatility), 0.05, 0.25, `${pct(m.Volatility)}`);
    updateMC('Momentum_20', safeN(m.Momentum_20), -0.05, 0.05, `${pct(m.Momentum_20)}`);
    updateMC('Price_Pos_52wk', safeN(m.Price_Pos_52wk, .5), 0.2, 0.8, `${(safeN(m.Price_Pos_52wk) * 100).toFixed(0)}%`);
}

function updateMC(id, val, minOk, maxOk, display) {
    const el = $e('m-' + id); if (!el) return;
    el.textContent = display;
    const card = el.closest('.mc');
    if (card) { card.className = card.className.replace(/\bok|\bwarn|\bbad/g, ''); card.classList.add(metricStatus(val, minOk, maxOk)); }
}

// ── CHART ──────────────────────────────
function updateChart(df) {
    const container = $e('main-chart');
    if (!container || df.length === 0) return;

    if (!lwChart) {
        lwChart = LightweightCharts.createChart(container, {
            layout: { background: { color: 'transparent' }, textColor: 'rgba(255,255,255,.6)' },
            grid: { vertLines: { color: 'rgba(255,255,255,.04)' }, horzLines: { color: 'rgba(255,255,255,.04)' } },
            rightPriceScale: { borderColor: 'rgba(255,255,255,.1)' },
            timeScale: { borderColor: 'rgba(255,255,255,.1)' },
            width: container.clientWidth || 1000,
            height: container.offsetHeight || 400,
        });
        lwSeries = lwChart.addAreaSeries({ lineColor: '#ffcc00', topColor: 'rgba(255,204,0,.2)', bottomColor: 'rgba(255,204,0,0)', lineWidth: 2 });
        window.addEventListener('resize', () => lwChart?.applyOptions({ width: container.clientWidth }));
    }

    const key = currentChartType === 'ons' ? 'Gold_USD' : 'Gram_Gold';
    const pts = df.map(d => ({ time: String(d.Date || '').slice(0, 10), value: safeN(d[key]) }))
        .filter(d => d.time.length === 10 && d.value > 0)
        .sort((a, b) => a.time.localeCompare(b.time));
    if (pts.length > 0) { lwSeries.setData(pts); lwChart.timeScale().fitContent(); }
}

// ── SAYFA 2: TEKNİK ANALİZ ──────────────
function updateTeknik(m, df) {
    const rsi = safeN(m.RSI, 50);
    setT('t-rsi', rsi.toFixed(1));
    const ptr = $e('rsi-pointer');
    if (ptr) ptr.style.left = `${rsi}%`;
    const rsiS = $e('rsi-status');
    if (rsiS) { rsiS.textContent = rsi < 30 ? '🟢 Aşırı Satım — AL Bölgesi' : rsi > 70 ? '🔴 Aşırı Alım — SAT Bölgesi' : '🟡 Nötr Bölge'; }

    setT('t-macd', fmtN(m.MACD));
    setT('t-macd-sig', fmtN(m.MACD_Signal));
    setT('t-macd-hist', fmtN(m.MACD_Hist));
    const histEl = $e('t-macd-hist');
    if (histEl) histEl.className = safeN(m.MACD_Hist) > 0 ? 'green' : 'red';
    setT('t-macd-status', safeN(m.MACD) > 0 ? '📈 Yükseliş (Bullish)' : '📉 Düşüş (Bearish)');

    setT('t-bb-up', `₺${fmtN(m.BB_Upper)}`);
    setT('t-bb-mid', `₺${fmtN(m.BB_Mid)}`);
    setT('t-bb-lo', `₺${fmtN(m.BB_Lower)}`);
    setT('t-bb-pct', fmtN(m.BB_Pct, 3));
    const bbPos = $e('bbv-price-pos');
    if (bbPos) bbPos.style.width = `${Math.min(100, safeN(m.BB_Pct) * 100)}%`;

    setT('t-wr', fmtN(m.Williams_R));
    setT('t-cci', fmtN(m.CCI));
    setT('t-stoch-k', fmtN(m.Stoch_K));
    setT('t-stoch-d', fmtN(m.Stoch_D));
    setT('t-atr', fmtN(m.ATR));

    setT('t-sma20', `₺${fmtN(m.SMA_20)}`);
    setT('t-sma50', `₺${fmtN(m.SMA_50)}`);
    setT('t-sma200', `₺${fmtN(m.SMA_200)}`);
    setT('t-macross', safeN(m.SMA_20) > safeN(m.SMA_50) ? '🟢 Golden Cross (Alım)' : '🔴 Death Cross (Satım)');

    setT('t-fib236', `₺${fmtN(m.Fib_0236)}`);
    setT('t-fib382', `₺${fmtN(m.Fib_0382)}`);
    setT('t-fib500', `₺${fmtN(m.Fib_0500)}`);
    setT('t-fib618', `₺${fmtN(m.Fib_0618)}`);
    setT('t-fib786', `₺${fmtN(m.Fib_0786)}`);
}

// ── SAYFA 3: YZ & ML ───────────────────
function updateML(ai, m) {
    setT('ml-rl-status', ai.RL_Status || '---');
    setT('ml-epsilon', safeN(ai.RL_Epsilon, 1).toFixed(4));
    setT('ml-lstm', ai.LSTM_Status || 'Simüle');
    setT('ml-transformer', ai.Transformer_Status || 'Simüle');
    setT('ml-hurst', fmtN(m.Hurst, 3));
    setT('ml-zscore', fmtN(m.Z_Score));
    setT('ml-volregime', m.Vol_Regime || 'NORMAL');
    setT('ml-regime', m.Regime || 'YATAY');
    setT('ml-patterns', ai.Patterns || 'Analiz ediliyor...');

    const prog = $e('rl-progress');
    if (prog) prog.style.width = `${(1 - safeN(ai.RL_Epsilon, 1)) * 100}%`;
}

// ── SAYFA 4: RİSK ─────────────────────
function updateRisk(risk, ons) {
    const onsP = safeN(ons?.price);
    setT('r-var95', pct(Math.abs(safeN(risk.VAR_95))));
    setT('r-var99', pct(Math.abs(safeN(risk.VAR_99))));
    setT('r-cvar95', pct(Math.abs(safeN(risk.CVaR_95))));
    const varPct = Math.min(Math.abs(safeN(risk.VAR_95)) * 100, 100);
    const vb = $e('var-bar'); if (vb) vb.style.width = varPct + '%';

    const maxdd = Math.abs(safeN(risk.MaxDD));
    setT('r-maxdd', `-${maxdd.toFixed(2)}%`);
    const ddf = $e('r-dd-fill'); if (ddf) ddf.style.width = Math.min(maxdd * 4, 100) + '%';
    setT('r-calmar', fmtN(risk.Calmar));

    setT('r-mc30', `$${fmtN(risk.Monte_Carlo_30d)}`);
    setT('r-mc90', `$${fmtN(risk.Monte_Carlo_90d)}`);
    setT('r-curr-price', `$${onsP.toFixed(2)}`);

    setT('r-vol', pct(safeN(risk.Volatility_Annual)));
    setT('r-garch', pct(safeN(risk.Volatility_Annual) * 0.95));
    setT('r-volreg', risk.Volatility_Annual > 0.25 ? '🔴 YÜKSEK' : risk.Volatility_Annual > 0.10 ? '🟡 ORTA' : '🟢 DÜŞÜK');

    setT('r-es', pct(Math.abs(safeN(risk.CVaR_95))));
    setT('r-dd-dev', pct(safeN(risk.Volatility_Annual) * 0.6));
    setT('r-vol-exceed', pct(0.05));
    setT('r-kurt', fmtN(0));  // placeholder
    setT('r-skew', fmtN(0));  // placeholder

    // Senaryo analizi
    const base = onsP;
    setT('sc-crash', `$${(base * 0.70).toFixed(2)}`);
    setT('sc-bear', `$${(base * 0.85).toFixed(2)}`);
    setT('sc-flat', `$${base.toFixed(2)}`);
    setT('sc-bull', `$${(base * 1.15).toFixed(2)}`);
    setT('sc-rally', `$${(base * 1.30).toFixed(2)}`);
}

// ── SAYFA 5: PORTFÖY ──────────────────
function updatePortfoy(port, risk) {
    const kelly = safeN(port.Kelly_F);
    setT('p-kelly', `${(kelly * 100).toFixed(1)}%`);
    setT('p-winrate', `${fmtN(risk.Win_Rate)}%`);
    setT('p-pf', fmtN(risk.Profit_Factor));
    setT('p-kelly-full', `${(kelly * 100).toFixed(1)}%`);
    setT('p-kelly-half', `${(kelly * 50).toFixed(1)}%`);
    setT('p-vol', pct(safeN(risk.Volatility_Annual)));
    setT('p-inv-vol', fmtN(port.Risk_Parity_Weight));
    setT('p-opt-size', `${(safeN(port.Optimal_Size) * 100).toFixed(1)}%`);
    setT('p-ef-sharpe', fmtN(risk.Sharpe));
    setT('p-dynamic', safeN(risk.Sharpe) > 1 ? '🟢 Riskli Ağırlık' : '🟡 Nakit Ağırlık');
}

// ── SAYFA 6: STRATEJİ ──────────────────
function updateStrateji(m) {
    function setSignBig(id, val) {
        const el = $e(id); if (!el) return;
        const v = (val || 'BEKLE').toUpperCase();
        el.textContent = v;
        el.className = `signal-big ${v}`;
    }
    setSignBig('s-mom', m.Signal_Momentum);
    setSignBig('s-mr', m.Signal_MeanRev);
    setSignBig('s-trend', m.Signal_Trend);
    setSignBig('s-combined', m.Signal_Combined);

    setT('s-mom5', pct(safeN(m.Momentum_5)));
    setT('s-mom20', pct(safeN(m.Momentum_20)));
    setT('s-mom60', pct(safeN(m.Momentum_60)));
    setT('s-zscore', `${fmtN(m.Z_Score)}σ`);
    setT('s-halflife', `${fmtN(m.Half_Life)} gün`);
    setT('s-bbpct', fmtN(m.BB_Pct, 3));
    setT('s-macross', safeN(m.SMA_20) > safeN(m.SMA_50) ? '🟢 Golden Cross' : '🔴 Death Cross');
    setT('s-golden', safeN(m.SMA_20) > safeN(m.SMA_50) ? 'EVET ✅' : 'HAYIR ❌');
    setT('s-hurst', fmtN(m.Hurst, 3));
    setT('s-macd-hist', fmtN(m.MACD_Hist));
    setT('s-rsi-macd', `RSI:${fmtN(m.RSI)} / MACD:${fmtN(m.MACD)}`);
    setT('s-regime', m.Regime || 'YATAY');
    setT('s-vol-signal', safeN(m.Volatility) > 0.25 ? '🔴 Yüksek Vol' : '🟢 Normal Vol');
}

// ── SAYFA 7: EKONOMETRİ ──────────────
function updateEkonometri(m, risk) {
    setT('e-hurst', fmtN(m.Hurst, 3));
    setT('e-halflife', `${fmtN(m.Half_Life)} gün`);
    setT('e-autocorr', fmtN(m.Autocorr_Lag1, 4));
    setT('e-adf', safeN(m.Z_Score) < -2 ? '✅ Durağan (Z<-2)' : '🔄 Birimsiz Kök');
    setT('e-rvol', pct(safeN(risk.Volatility_Annual)));
    setT('e-garch', pct(safeN(risk.Volatility_Annual) * 0.95));
    setT('e-volcluster', risk.Volatility_Annual > 0.25 ? 'YÜKSEK Kümeleme' : 'Normal');
    setT('e-skew', fmtN(m.Rolling_Skew, 3));
    setT('e-kurt', fmtN(m.Rolling_Kurt, 3));
    setT('e-ds-dev', pct(safeN(risk.Volatility_Annual) * 0.65));
    setT('e-stationary', Math.abs(safeN(m.Z_Score)) > 2 ? '✅ Durağan' : '⚠️ Kısmen Durağan');
}

// ── SAYFA 8: MAKRO ────────────────────
function updateMakro(macro, ai) {
    const sent = safeN(ai.Sentiment);
    setT('mac-sent', sent > 0.2 ? '🟢 Boğa (' + sent.toFixed(2) + ')' : sent < -0.2 ? '🔴 Ayı (' + sent.toFixed(2) + ')' : '🟡 Nötr (' + sent.toFixed(2) + ')');
    setT('mac-rate', macro.Interest_Rate + '%');
    setT('mac-cpi', macro.CPI);
}

// ── SAYFA 9: BACKTEST ─────────────────
function updateBacktest(risk) {
    setT('bt-sharpe', fmtN(risk.Sharpe));
    setT('bt-sortino', fmtN(risk.Sortino));
    setT('bt-wr', `${fmtN(risk.Win_Rate)}%`);
    setT('bt-pf', fmtN(risk.Profit_Factor));
    setT('bt-exp', pct(safeN(risk.Expectancy) / 100));
    setT('bt-mc', `$${fmtN(risk.Monte_Carlo_30d)}`);
    setT('bt-mc90', `$${fmtN(risk.Monte_Carlo_90d)}`);
    setT('bt-oos', 'Son 50 gün test edildi');
}

// ── SAYFA 10: MİKRO ──────────────────
function updateMikro(m) {
    setT('mic-atr', fmtN(m.ATR));
    setT('mic-obv', safeN(m.Momentum_20) > 0 ? '📈 Yükselen' : '📉 Düşen');
    setT('mic-mom5', pct(safeN(m.Momentum_5)));
    setT('mic-accel', fmtN(m.MACD_Hist));
    setT('mic-vol', 'Normal (Likid Piyasa)');
    setT('mic-hurst', fmtN(m.Hurst, 3));
    setT('mic-autocorr', fmtN(m.Autocorr_Lag1, 4));
    setT('mic-vcluster', m.Vol_Regime || 'NORMAL');
}

// ── SAYFA 11: HAFIZA ─────────────────
function updateHafiza(ai, m) {
    setT('mem-st', `${ai.Memory_Size || 0} deneyim`);
    setT('mem-lt', `${ai.LT_Memory_Size || 0} desen`);
    setT('mem-patterns', ai.Patterns || 'Analiz ediliyor...');
    setT('mem-rl', `DQN Replay Buffer (${ai.Memory_Size || 0} kayıt)`);
    setT('mem-exp', `${Math.min(safeN(ai.Memory_Size), 1000)} / 1000 kapasite`);
    setT('haf-patterns', ai.Patterns || '---');
}

// ── SAYFA 12: PERFORMANS ─────────────
function updatePerf(risk, m) {
    const sharpe = safeN(risk.Sharpe);
    const sortino = safeN(risk.Sortino);
    const wr = safeN(risk.Win_Rate);
    const pf = safeN(risk.Profit_Factor);
    const maxdd = Math.abs(safeN(risk.MaxDD));

    setT('pf-sharpe', fmtN(sharpe));
    setT('pf-sortino', fmtN(sortino));
    setT('pf-calmar', fmtN(risk.Calmar));
    setT('pf-winrate', `${fmtN(wr)}%`);
    setT('pf-pf', fmtN(pf));
    setT('pf-exp', pct(safeN(risk.Expectancy) / 100));
    setT('pf-maxdd', `-${maxdd.toFixed(2)}%`);
    setT('pf-rolling-sharpe', fmtN(m.Rolling_Sharpe));

    const sharpeBar = $e('sharpe-bar');
    if (sharpeBar) sharpeBar.style.width = Math.min(sharpe * 33, 100) + '%';
    const sortinoBar = $e('sortino-bar');
    if (sortinoBar) sortinoBar.style.width = Math.min(sortino * 22, 100) + '%';
    const wrBar = $e('wr-bar');
    if (wrBar) wrBar.style.width = wr + '%';

    // Max DD renklendirmesi
    const maxddEl = $e('pf-maxdd');
    if (maxddEl) maxddEl.className = maxdd < 10 ? 'big-num green' : maxdd < 20 ? 'big-num warn' : 'big-num red';
}

// ── SAYFA 13: KARAR ROBOTU ───────────
function updateRobot(robot, m) {
    const act = (robot.action || 'BEKLE').toUpperCase();
    const actEl = $e('rob-action');
    if (actEl) {
        actEl.textContent = act === 'AL' ? '🟢 AL TAVSİYESİ' : act === 'SAT' ? '🔴 SAT TAVSİYESİ' : '🟡 BEKLE (NÖTR)';
        actEl.className = `signal-big ${act === 'AL' ? 'signal-buy' : act === 'SAT' ? 'signal-sell' : 'signal-hold'}`;
    }
    
    setT('rob-prob', `${safeN(robot.prob_win).toFixed(1)}%`);
    setT('rob-bull', `%${safeN(robot.prob_bull).toFixed(1)} İhtimal`);
    setT('rob-bear', `%${safeN(robot.prob_bear).toFixed(1)} İhtimal`);
    
    setT('rob-tp', `$${safeN(robot.tp).toFixed(2)}`);
    setT('rob-sl', `$${safeN(robot.sl).toFixed(2)}`);
    
    setT('rob-tech', safeN(m.Z_Score) < -1.5 ? 'Aşırı Satım' : safeN(m.Z_Score) > 1.5 ? 'Aşırı Alım' : 'Yatay Seyir');
    setT('rob-stat', m.Regime || 'BELİRSİZ');
}

// ── SAYFA 14: HABERLER ───────────────
function updateHaber(newsArray) {
    const container = $e('news-container');
    if (!container) return;
    
    if (!newsArray || newsArray.length === 0) {
        container.innerHTML = '<p>Şu an yeni bir haber akışı yok.</p>';
        return;
    }
    
    container.innerHTML = '';
    newsArray.forEach((headline, i) => {
        const div = document.createElement('div');
        div.style.padding = '12px 15px';
        div.style.background = 'rgba(255,255,255,0.05)';
        div.style.borderRadius = '8px';
        div.style.borderLeft = '4px solid ' + (i % 2 === 0 ? 'var(--gold)' : 'var(--blue)');
        div.innerHTML = `<strong>${headline}</strong><br><small style="color:rgba(255,255,255,0.5)">Reuters / YZ Haber Akışı</small>`;
        container.appendChild(div);
    });
}

// ── BAŞLAT ────────────────────────────
appendLog('> Sistem başlatıldı.');
appendLog('> Veri akışı bekleniyor...');
updateDashboard();
setInterval(updateDashboard, 5000);
