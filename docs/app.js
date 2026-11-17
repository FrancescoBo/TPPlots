/* Pagina target price: legge data/dati.json (prodotto da scripts/costruisci.py) */
(async function () {
  const D = window.DATI || await fetch('data/dati.json', { cache: 'no-cache' }).then(r => r.json());
  const css = n => getComputedStyle(document.querySelector('.viz-root')).getPropertyValue(n).trim();
  const CL = D.classi;  // Buy, Overweight, Neutral, Underweight, Sell
  const COL_CL = () => ({ Buy: css('--c-buy'), Overweight: css('--c-ow'), Neutral: css('--c-neutral'), Underweight: css('--c-uw'), Sell: css('--c-sell') });
  const $ = s => document.querySelector(s);
  // colore dei target rispetto al precedente dello stesso emittente
  const VAR = [['su', 'Target alzato', '--var-su'], ['giu', 'Target abbassato', '--var-giu'],
               ['invariato', 'Target invariato', '--var-inv'], ['primo', 'Primo target dell\'emittente', '--var-primo', true]];

  const f2 = v => v == null ? '–' : v.toLocaleString('it-IT', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const fp = v => v == null ? '–' : (v > 0 ? '+' : '') + (v * 100).toLocaleString('it-IT', { maximumFractionDigits: 1, minimumFractionDigits: 1 }) + '%';
  const fmld = v => v == null ? '–' : (v / 1e9).toLocaleString('it-IT', { maximumFractionDigits: 1, minimumFractionDigits: 1 });
  const fd = s => s ? s.split('-').reverse().join('/') : '–';
  const segno = v => v == null ? '' : v >= 0 ? 'pos' : 'neg';
  const nomeBreve = n => (n || '').replace(/\s*[-,]?\s*SOCIET[ÀA]'?\s+PER\s+AZIONI.*$/i, '').replace(/\s+(S\.?\s?P\.?\s?A\.?|N\.?\s?V\.?|S\.A\.|SA|SE)$/i, '').replace(/\s*[-–,]\s*$/, '').replace(/\s+'\s+/, "' ").trim();
  const etichetta = x => `${nomeBreve(x.nome)} (${x.ticker})`;
  const SIGLA = { Buy: 'Buy', Overweight: 'Overweight', Neutral: 'Neutral', Underweight: 'Underweight', Sell: 'Sell' };
  const pill = c => c ? `<span class="pill" style="--pc:${COL_CL()[c]}">${c}</span>` : '';

  $('#info').textContent = `Aggiornato al ${fd(D.data_riferimento)} · ${D.recap.length} titoli · ` +
    `titoli con almeno ${D.parametri.min_target_anno} target nell'ultimo anno · ` +
    `un target conta nel TP medio per ${D.parametri.validita_tp_giorni} giorni` +
    (D.senza_prezzi?.length ? ` · in attesa dei prezzi: ${D.senza_prezzi.join(', ')}` : '');

  function layoutBase(extra) {
    return Object.assign({
      paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
      font: { family: 'system-ui, sans-serif', size: 12, color: css('--text-secondary') },
      margin: { l: 56, r: 16, t: 36, b: 40 },
      hoverlabel: { bgcolor: css('--surface-1'), bordercolor: css('--axis'), font: { color: css('--text-primary') } },
      legend: { orientation: 'h', y: 1.02, yanchor: 'bottom', x: 0, traceorder: 'normal' },
    }, extra);
  }
  const asse = extra => Object.assign({ gridcolor: css('--grid'), linecolor: css('--axis'), zerolinecolor: css('--axis'), tickfont: { color: css('--text-secondary') } }, extra);
  const cfg = { displaylogo: false, responsive: true, modeBarButtonsToRemove: ['lasso2d', 'select2d', 'autoScale2d'] };

  /* ---------- tabelle ordinabili ---------- */
  function tabella(el, colonne, righe, opz = {}) {
    let ord = opz.ord || null, asc = false;
    function disegna() {
      const r = [...righe];
      if (ord) {
        const c = colonne.find(c => c.k === ord);
        const val = x => c.v ? c.v(x) : x[c.k];
        r.sort((a, b) => { const A = val(a), B = val(b); if (A == null) return 1; if (B == null) return -1; return (A > B ? 1 : A < B ? -1 : 0) * (asc ? 1 : -1); });
      }
      el.innerHTML = '<thead><tr>' + colonne.map(c => `<th data-k="${c.k}" class="${c.t ? 't' : ''} ${ord === c.k ? 'ord' + (asc ? ' asc' : '') : ''}">${c.h}</th>`).join('') + '</tr></thead><tbody>' +
        r.map(x => `<tr ${opz.clic ? `class="clic" data-id="${opz.id(x)}"` : ''}>` + colonne.map(c => `<td class="${c.t ? 't' : ''} ${c.cls ? c.cls(x) : ''}">${c.f ? c.f(x) : (x[c.k] ?? '–')}</td>`).join('') + '</tr>').join('') + '</tbody>';
      el.querySelectorAll('th').forEach(th => th.onclick = () => { const k = th.dataset.k; asc = ord === k ? !asc : false; ord = k; disegna(); });
      if (opz.clic) el.querySelectorAll('tr.clic').forEach(tr => tr.onclick = () => opz.clic(tr.dataset.id));
    }
    disegna();
  }

  /* ---------- RECAP ---------- */
  const maxTot = Math.max(1, ...D.recap.map(x => CL.reduce((a, c) => a + x[c], 0)));
  const PX = Math.min(7, 170 / maxTot);          // larghezza in pixel di un emittente nella barra
  const barra = x => {
    const col = COL_CL(), tit = CL.map(c => `${c}: ${x[c]}`).join(' · ');
    return `<span class="rb" title="${tit}">` + CL.filter(c => x[c] > 0).map(c => {
      const w = Math.max(x[c] * PX, 4);
      return `<i style="width:${w}px;--pc:${col[c]};--tc:var(--tx-${{Buy:'buy',Overweight:'ow',Neutral:'neutral',Underweight:'uw',Sell:'sell'}[c]})">${w >= 15 ? x[c] : ''}</i>`;
    }).join('') + '</span>';
  };
  $('#leg-rac').innerHTML = CL.map(c => `<span style="--pc:${COL_CL()[c]}">${c}</span>`).join('');
  tabella($('#tab-recap'), [
    { k: 'nome', h: 'Titolo', t: 1, cls: () => 'nome', f: x => `<span title="${x.nome}"><span class="nm">${nomeBreve(x.nome)}</span> <span class="tk">(${x.ticker})</span></span>` },
    { k: 'capitalizzazione', h: 'Cap. (mld €)', f: x => fmld(x.capitalizzazione) },
    { k: 'prezzo', h: 'Prezzo', f: x => f2(x.prezzo) },
    { k: 'tp_medio', h: 'TP medio', f: x => f2(x.tp_medio) },
    { k: 'n_target_validi', h: 'N. target' },
    { k: 'delta_tp', h: 'Delta TP', f: x => fp(x.delta_tp), cls: x => segno(x.delta_tp) },
    { k: 'rac', h: 'Raccomandazioni', t: 1, f: barra, cls: () => 'rac', v: x => x.Buy * 1000 + x.Overweight },
    { k: 'ultima_raccomandazione', h: 'Ultima rac.', f: x => fd(x.ultima_raccomandazione) },
  ], D.recap, { ord: 'rac', clic: tk => apriTitolo(tk), id: x => x.ticker });

  function graficiRecap() {
    const ok = D.recap.filter(x => x.capitalizzazione && x.delta_tp != null);
    const tr = (sel, nome, pieno) => ({
      type: 'scatter', mode: pieno ? 'markers+text' : 'markers', name: nome,
      x: sel.map(x => x.capitalizzazione / 1e9), y: sel.map(x => x.delta_tp), text: sel.map(x => x.ticker),
      textposition: 'top center', textfont: { color: css('--text-secondary'), size: 11 },
      marker: { size: pieno ? 11 : 9, color: pieno ? css('--series-1') : css('--surface-1'), line: { color: css('--series-1'), width: 2 } },
      customdata: sel.map(x => [x.nome, x.tp_medio, x.prezzo]),
      hovertemplate: '<b>%{text}</b> %{customdata[0]}<br>Cap. %{x:.1f} mld €<br>Delta TP %{y:.1%}<br>TP medio %{customdata[1]:.2f} · prezzo %{customdata[2]:.2f}<extra></extra>',
    });
    Plotly.react('g-pareto', [tr(ok.filter(x => x.pareto === 'Pareto'), 'Pareto', true), tr(ok.filter(x => x.pareto !== 'Pareto'), 'Dominato', false)],
      layoutBase({ xaxis: asse({ type: 'log', title: 'Capitalizzazione (mld €, scala log)', tickvals: [1, 2, 5, 10, 20, 50, 100, 200, 500], ticktext: ['1', '2', '5', '10', '20', '50', '100', '200', '500'] }), yaxis: asse({ tickformat: '.0%', title: 'Delta TP', zeroline: true }), margin: { l: 60, r: 16, t: 36, b: 48 } }), cfg);
    document.getElementById('g-pareto').on('plotly_click', e => apriTitolo(e.points[0].text));
  }

  /* ---------- DETTAGLIO TITOLO ---------- */
  const sel = $('#sel-titolo');
  sel.innerHTML = D.recap.map(x => `<option value="${x.ticker}">${etichetta(x)}</option>`).join('');
  sel.onchange = () => disegnaTitolo(sel.value);
  let giorni = 365, corrente = D.recap[0]?.ticker, mostraMM = true;
  $('#chk-mm').onchange = e => { mostraMM = e.target.checked; disegnaTitolo(corrente); };
  document.querySelectorAll('#periodi button').forEach(b => b.onclick = () => {
    document.querySelectorAll('#periodi button').forEach(x => x.classList.toggle('attivo', x === b));
    giorni = +b.dataset.g; disegnaTitolo(corrente);
  });

  function disegnaTitolo(tk) {
    corrente = tk; sel.value = tk;
    const T = D.titoli[tk], R = D.recap.find(x => x.ticker === tk);
    const ultimo = T.prezzi.at(-1)[0];
    const da = giorni ? new Date(new Date(ultimo) - giorni * 864e5).toISOString().slice(0, 10) : T.prezzi[0][0];
    const dentro = d => d >= da;

    $('#kpi').innerHTML = [
      ['Prezzo', f2(R.prezzo) + ` <small>${fd(R.data_prezzo)}</small>`],
      ['Capitalizzazione', R.capitalizzazione ? fmld(R.capitalizzazione) + ' <small>mld €</small>' : '–'],
      ['TP medio', f2(R.tp_medio)], ['Delta TP', `<span class="${segno(R.delta_tp)}">${fp(R.delta_tp)}</span>`],
      ['TP −10%', f2(R.tp_meno_10)], ['Target validi', R.n_target_validi],
      ['Buy / OW / Neu / UW / Sell', CL.map(c => R[c]).join(' / ')],
    ].map(([a, b]) => `<div><span>${a}</span><b>${b}</b></div>`).join('');

    $('#lab-mm').hidden = !T.minmax;
    const P = T.prezzi.filter(p => dentro(p[0]));
    const conMM = T.minmax && mostraMM;
    const lineaMM = (nome, i) => ({ type: 'scatter', mode: 'lines', name: nome, x: P.map(p => p[0]), y: P.map(p => p[i]), connectgaps: false,
      line: { color: css('--series-1'), width: 1.3, dash: 'dash' }, opacity: 0.85,
      hovertemplate: `${nome} %{y:.2f}<extra></extra>` });
    const M = T.tp_medio.filter(p => dentro(p[0]));
    const Rc = T.raccomandazioni.filter(r => r.target != null && dentro(r.data));
    Plotly.react('g-titolo', [
      { type: 'scatter', mode: 'lines', name: 'Prezzo', x: P.map(p => p[0]), y: P.map(p => p[1]),
        line: { color: css('--series-1'), width: 2 }, hovertemplate: '%{x|%d/%m/%Y}<br>Prezzo %{y:.2f}<extra></extra>' },
      ...(conMM ? [lineaMM('Massimo giornaliero', 3), lineaMM('Minimo giornaliero', 2)] : []),
      { type: 'scatter', mode: 'lines', name: 'TP medio', x: M.map(p => p[0]), y: M.map(p => p[1]), customdata: M.map(p => p[2]),
        line: { color: css('--series-2'), width: 2, shape: 'hv' }, connectgaps: false,
        hovertemplate: 'TP medio %{y:.2f} (%{customdata} emittenti)<extra></extra>' },
      ...VAR.map(([k, nome, colore, vuoto]) => {
        const q = Rc.filter(r => (r.variazione || 'primo') === k);
        return { type: 'scatter', mode: 'markers', name: nome, x: q.map(r => r.data), y: q.map(r => r.target),
          customdata: q.map(r => [r.emittente, r.raccomandazione || 'n.d.', r.delta_rec == null ? '–' : fp(r.delta_rec),
            r.target_prec == null ? 'primo target' : 'prec. ' + f2(r.target_prec)]),
          marker: { color: vuoto ? css('--surface-1') : css(colore), size: 8, line: { color: vuoto ? css(colore) : css('--surface-1'), width: vuoto ? 1.5 : 1 } },
          hovertemplate: '<b>%{customdata[0]}</b> · %{x|%d/%m/%Y}<br>%{customdata[1]} · target %{y:.2f} (%{customdata[3]})<br>vs prezzo: %{customdata[2]}<extra></extra>' };
      }),
    ], layoutBase({ hovermode: 'closest', xaxis: asse({ type: 'date', range: [da, ultimo] }), yaxis: asse({ title: '€' }), margin: { l: 56, r: 16, t: 36, b: 40 } }), cfg);

    $('#nota-emittenti').textContent = `Ultima raccomandazione per emittente. I target più vecchi di ${D.parametri.validita_tp_giorni} giorni sono in grigio e non entrano nel TP medio.`;
    tabella($('#tab-emittenti'), [
      { k: 'emittente', h: 'Emittente', t: 1 },
      { k: 'data', h: 'Data', f: x => fd(x.data), v: x => x.data },
      { k: 'raccomandazione', h: 'Raccomandazione', t: 1, f: x => x.raccomandazione || '<span class="muted">n.d.</span>' },
      { k: 'classe', h: 'Classe', t: 1, f: x => pill(x.classe), v: x => x.classe ? CL.indexOf(x.classe) : null },
      { k: 'target', h: 'Target', f: x => f2(x.target), cls: x => x.target_valido ? '' : 'muted' },
      { k: 'delta', h: 'Delta vs prezzo', v: x => x.target ? x.target / R.prezzo - 1 : null, f: x => x.target ? fp(x.target / R.prezzo - 1) : '–', cls: x => x.target_valido ? segno(x.target / R.prezzo - 1) : 'muted' },
      { k: 'n_raccomandazioni', h: 'N. rac.' },
    ], T.emittenti, { ord: 'data' });

    tabella($('#tab-storico'), [
      { k: 'data', h: 'Data', f: x => fd(x.data), v: x => x.data },
      { k: 'emittente', h: 'Emittente', t: 1 },
      { k: 'raccomandazione', h: 'Raccomandazione', t: 1, f: x => x.raccomandazione || '<span class="muted">n.d.</span>' },
      { k: 'target', h: 'Target', f: x => f2(x.target) },
      { k: 'delta_rec', h: 'Delta alla data', f: x => fp(x.delta_rec), cls: x => segno(x.delta_rec) },
      { k: 'giorni_target', h: 'Giorni al target', f: x => x.giorni_target ?? (x.target ? '<span class="muted">non raggiunto</span>' : '–') },
    ], T.raccomandazioni, { ord: 'data' });
  }

  /* ---------- navigazione ---------- */
  function vista(v) {
    document.querySelectorAll('.tab').forEach(t => t.classList.toggle('attivo', t.dataset.vista === v));
    $('#vista-recap').hidden = v !== 'recap'; $('#vista-titolo').hidden = v !== 'titolo';
    if (v === 'recap') graficiRecap(); else disegnaTitolo(corrente);
  }
  function apriTitolo(tk) { corrente = tk; location.hash = tk; vista('titolo'); window.scrollTo(0, 0); }
  document.querySelectorAll('.tab').forEach(t => t.onclick = () => { location.hash = t.dataset.vista === 'recap' ? '' : corrente; vista(t.dataset.vista); });
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => vista($('#vista-recap').hidden ? 'titolo' : 'recap'));
  const h = decodeURIComponent(location.hash.slice(1));
  if (D.titoli[h]) apriTitolo(h); else vista('recap');
})();
