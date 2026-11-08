"use strict";
const $ = s => document.querySelector(s);
const html = (sel, h) => { const el = $(sel); if (el._h !== h) { el.innerHTML = h; el._h = h; } };  // só redesenha o que mudou
const api = p => fetch(p).then(r => r.json());
const fmt = (v, c = 2) => v == null || isNaN(v) ? "—" : v.toLocaleString("pt-BR", {minimumFractionDigits: c, maximumFractionDigits: c});
const pct = v => v == null ? "—" : (v >= 0 ? "+" : "") + fmt(v * 100, 2) + "%";
const cls = v => v == null ? "mu" : v >= 0 ? "up" : "dn";
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
const ler = (k, d) => { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } };
const gravar = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} };

const URLP = new URLSearchParams(location.search);
const S = {sel: URLP.get("t")?.toUpperCase() || ler("sel", null), faixa: "6m", obs: ler("obs", ["^BVSP", "AAPL"]), cart: [], q: {}, hist: null};

// ---------------- topo
const TAPE = {"^BVSP": "Ibovespa", "^GSPC": "S&P 500", "^IXIC": "Nasdaq", "USDBRL=X": "Dólar", "BZ=F": "Brent",
  "GC=F": "Ouro", "^TNX": "Treasury 10a", "^VIX": "VIX", "BTC-USD": "Bitcoin"};
function relogio() {
  const agora = new Date();
  const sp = new Date(agora.toLocaleString("en-US", {timeZone: "America/Sao_Paulo"}));
  const m = sp.getHours() * 60 + sp.getMinutes(), dia = sp.getDay();
  const aberto = dia > 0 && dia < 6 && m >= 600 && m < 1075;
  $("#b3").textContent = aberto ? "B3 aberta" : "B3 fechada";
  $("#b3").className = "mk" + (aberto ? " aberto" : "");
  $("#hora").textContent = sp.toLocaleTimeString("pt-BR", {hour: "2-digit", minute: "2-digit"}) + " Brasília";
}
async function mundo() {
  const d = await api("/api/mundo");
  $("#tape").innerHTML = d.filter(x => TAPE[x.t] && x.p != null).map(x =>
    `<span><b>${TAPE[x.t]}</b>${fmt(x.p, x.p > 1000 ? 0 : 2)} <span class="${cls(x.v)}">${pct(x.v)}</span></span>`).join("");
  $("#tab-mundo").innerHTML = "<thead><tr><th>Mercado</th><th>Símbolo</th><th class='n'>Último</th><th class='n'>Dia</th></tr></thead><tbody>" +
    d.map(x => `<tr data-t="${esc(x.t)}"><td>${esc(x.nome)}</td><td class="mu">${esc(x.t)}</td><td class="n">${fmt(x.p)}</td>
      <td class="n ${cls(x.v)}">${pct(x.v)}</td></tr>`).join("") + "</tbody>";
}

// ---------------- listas
function linha(t, q, extra = "") {
  return `<li data-t="${esc(t)}" class="${t === S.sel ? "sel" : ""}"><span class="t">${esc(t)}</span>
    <span class="p">${fmt(q?.p)}</span><span class="s">${esc(q?.n && q.n !== t ? q.n : "")}</span>
    <span class="v ${cls(q?.v)}">${pct(q?.v)}</span>${extra === "obs" ? `<button class="x" data-rm="${esc(t)}" aria-label="Remover ${esc(t)}">×</button>` : ""}</li>`;
}
function listas() {
  const cart = S.cart.filter(p => p.q && p.p != null || p.q);
  $("#lista-cart").innerHTML = cart.length ? cart.map(p => linha(p.t, S.q[p.t] || p, "")).join("") :
    `<p class="vazio">Nenhuma posição. Peça ao Claude: “registre 100 PETR4 a 38,50”.</p>`;
  $("#lista-obs").innerHTML = S.obs.map(t => linha(t, S.q[t], "obs")).join("") || `<p class="vazio">Use a busca acima.</p>`;
}
async function cotar() {
  const ts = [...new Set([...S.cart.map(p => p.t), ...S.obs, S.sel].filter(Boolean))];
  if (!ts.length) return;
  for (const q of await api("/api/cotacoes?t=" + encodeURIComponent(ts.join(",")))) S.q[q.t] = q;
  listas(); cabecalho();
}

// ---------------- ativo selecionado
function cabecalho() {
  const q = S.q[S.sel] || {};
  $("#tk").textContent = S.sel || "—";
  $("#nome").textContent = q.n && q.n !== S.sel ? q.n : "";
  const [int, dec] = q.p == null ? ["—", ""] : fmt(q.p).split(",");
  $("#preco").innerHTML = `${q.m ? `<small>${esc(q.m)}</small> ` : ""}${int}${dec ? `<small>,${dec}</small>` : ""}`;
  $("#hero").className = "hero " + (q.v == null ? "" : q.v >= 0 ? "pos" : "neg");
  $("#atraso").textContent = q.f ? `fechamento de ${new Date(q.d + "T12:00").toLocaleDateString("pt-BR")} · fonte ${q.f.toUpperCase()}` :
    q.h ? "atualizado " + new Date(q.h * 1000).toLocaleTimeString("pt-BR", {hour: "2-digit", minute: "2-digit"}) + " · atraso ~15 min" :
    q.erro ? "sem cotação agora: as fontes recusaram, tente em alguns minutos" : "";
  $("#var").textContent = q.v == null ? "sem variação disponível" : `${pct(q.v)} ${q.f ? "no último pregão" : "hoje"}`;
  const pos = S.cart.find(p => p.t === S.sel), st = [
    ["Mín. / máx. do dia", `${fmt(q.min)} / ${fmt(q.max)}`], ["Mín. / máx. 52 sem.", `${fmt(q.min52)} / ${fmt(q.max52)}`]];
  const pts = S.hist?.t === S.sel ? S.hist.pts : [];
  if (pts.length > 1) st.push(["Variação no período", `<span class="${cls(pts.at(-1)[1] / pts[0][1] - 1)}">${pct(pts.at(-1)[1] / pts[0][1] - 1)}</span>`]);
  if (pos?.q) {
    const res = q.p && pos.pm ? q.p / pos.pm - 1 : null;
    st.push(["Sua posição", `${fmt(pos.q, 0)} × PM ${fmt(pos.pm)}`], ["Resultado", `<span class="${cls(res)}">${pct(res)}</span>`],
      ["Valor", fmt(pos.q * (q.p ?? pos.pm))]);
  }
  $("#stats").innerHTML = st.filter(([, b]) => b !== "— / —").map(([a, b]) => `<div><dt>${a}</dt><dd>${b}</dd></div>`).join("");
}
async function grafico() {
  if (!S.sel) return;
  const pedido = S.sel + S.faixa;
  try { const h = await api(`/api/historico?t=${encodeURIComponent(S.sel)}&f=${S.faixa}`); if (pedido === S.sel + S.faixa) S.hist = h; }
  catch { S.hist = {t: S.sel, pts: []}; }
  desenhar(); cabecalho();
}
function desenhar() {
  const svg = $("#svg"), box = $("#chart").getBoundingClientRect(), W = box.width, H = box.height;
  const pts = S.hist?.pts || [];
  svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
  if (pts.length < 2) { svg.innerHTML = `<text x="12" y="24" fill="var(--mu)">Sem histórico para este período.</text>`; return; }
  const ys = pts.map(p => p[1]), lo = Math.min(...ys), hi = Math.max(...ys), pad = (hi - lo) * .08 || 1;
  const L = 0, R = W - 58, T = 8, B = H - 22;
  const x = i => L + i * (R - L) / (pts.length - 1), y = v => B - (v - lo + pad) * (B - T) / (hi - lo + 2 * pad);
  const cor = ys.at(-1) >= ys[0] ? "var(--up)" : "var(--dn)";
  const d = pts.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p[1]).toFixed(1)}`).join("");
  const grade = [0, .25, .5, .75, 1].map(f => { const v = lo - pad + f * (hi - lo + 2 * pad);
    return `<line x1="${L}" x2="${R}" y1="${y(v)}" y2="${y(v)}" stroke="var(--sep)" stroke-dasharray="2 4"/><text x="${R + 8}" y="${y(v) + 4}" fill="var(--tx3)" font-size="11">${fmt(v)}</text>`; }).join("");
  const dt = ts => new Date(ts * 1000).toLocaleDateString("pt-BR", S.faixa === "1d" ? {hour: "2-digit", minute: "2-digit"} : {day: "2-digit", month: "short", year: S.faixa === "5a" ? "2-digit" : undefined});
  const eixos = [0, Math.floor(pts.length / 2), pts.length - 1].map((i, k) =>
    `<text x="${x(i)}" y="${H - 5}" fill="var(--mu)" font-size="11" text-anchor="${["start", "middle", "end"][k]}">${dt(pts[i][0])}</text>`).join("");
  svg.innerHTML = `<defs><linearGradient id="ga" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${cor}" stop-opacity=".32"/><stop offset="1" stop-color="${cor}" stop-opacity="0"/></linearGradient></defs>
    ${grade}${eixos}<path d="${d}L${R},${B}L${L},${B}Z" fill="url(#ga)"/>
    <path d="${d}" fill="none" stroke="${cor}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/><line id="cx" y1="${T}" y2="${B}" stroke="var(--mu)" stroke-dasharray="3 3" visibility="hidden"/>
    <circle id="cp" r="5" fill="${cor}" stroke="var(--tx)" stroke-width="2" visibility="hidden"/>`;
  svg.onmousemove = e => {
    const r = svg.getBoundingClientRect(), i = Math.max(0, Math.min(pts.length - 1, Math.round((e.clientX - r.left - L) / (R - L) * (pts.length - 1))));
    const px = x(i), py = y(pts[i][1]), tip = $("#tip");
    ["cx", "cp"].forEach(id => svg.querySelector("#" + id).setAttribute("visibility", "visible"));
    svg.querySelector("#cx").setAttribute("x1", px); svg.querySelector("#cx").setAttribute("x2", px);
    svg.querySelector("#cp").setAttribute("cx", px); svg.querySelector("#cp").setAttribute("cy", py);
    tip.style.display = "block"; tip.textContent = `${dt(pts[i][0])}  ${fmt(pts[i][1])}`;
    tip.style.left = Math.min(px + 10, R - tip.offsetWidth) + "px"; tip.style.top = Math.max(py - 30, 0) + "px";
  };
  svg.onmouseleave = () => { $("#tip").style.display = "none"; ["cx", "cp"].forEach(id => svg.querySelector("#" + id)?.setAttribute("visibility", "hidden")); };
}
async function noticias() {
  const t = S.sel; if (!t) return;
  $("#news-st").textContent = "carregando…"; $("#news").innerHTML = "";
  try {
    const its = await api(`/api/noticias?t=${encodeURIComponent(t)}&e=${encodeURIComponent(S.q[t]?.n || t)}`);
    if (t !== S.sel) return;
    $("#news-st").textContent = its.length ? `${its.length} nos últimos 7 dias` : "";
    const ago = d => { if (!d) return ""; const h = (Date.now() - new Date(d)) / 36e5; return h < 24 ? `há ${Math.max(1, Math.round(h))} h` : `há ${Math.round(h / 24)} d`; };
    const rot = {real: "REAL", provavel: "RUMOR PROVÁVEL", possivel: "RUMOR POSSÍVEL", improvavel: "RUMOR FRACO", desmentido: "DESMENTIDO"};
    $("#news").innerHTML = its.map(i => `<li><a href="${esc(i.link)}" target="_blank" rel="noopener">${esc(i.titulo)}</a>
      <div class="meta">${i.nivel_rumor ? `<span class="tag ${i.nivel_rumor}">${rot[i.nivel_rumor]}</span>` : ""}
      ${(i.tipos || []).includes("expectativa") ? `<span class="tag exp">EXPECTATIVA</span>` : ""}
      <span>${esc(i.fonte || "")}</span><span>${ago(i.data)}</span></div></li>`).join("") || `<li class="mu">Nada relevante nos últimos 7 dias.</li>`;
  } catch { $("#news-st").textContent = "falhou"; }
}
function selecionar(t) {
  if (!t) return;
  S.sel = t.toUpperCase(); gravar("sel", S.sel); S.hist = null;
  listas(); cabecalho(); grafico(); noticias(); cotar(); live();
}

// ---------------- carteira
async function carteira() {
  const d = await api("/api/carteira");
  S.cart = d.pos;
  d.pos.forEach(p => { if (p.p != null) S.q[p.t] = {...S.q[p.t], t: p.t, p: p.p, v: p.v, m: p.m, n: S.q[p.t]?.n}; });
  const vals = d.pos.map(p => p.q ? p.q * (p.p ?? p.pm ?? 0) : 0), tot = vals.reduce((a, b) => a + b, 0);
  const custo = d.pos.reduce((a, p) => a + (p.q && p.pm ? p.q * p.pm : 0), 0);
  $("#ola-total").innerHTML = (() => { const [i, d] = fmt(tot).split(","); return `${i}<small>,${d}</small>`; })();
  $("#ola-res").textContent = custo ? `${pct(tot / custo - 1)} sobre o custo` : "";
  $("#ola-res").className = "chip " + cls(tot / custo - 1);
  $("#resumo").innerHTML = [["Valor", fmt(tot)], ["Custo", fmt(custo)],
    ["Resultado", `<span class="${cls(tot / custo - 1)}">${custo ? pct(tot / custo - 1) : "—"}</span>`],
    ["Posições", d.pos.length], ["Registro", d.data || "—"]].map(([a, b]) => `<div><span>${a}</span><b>${b}</b></div>`).join("");
  $("#tab-cart").innerHTML = "<thead><tr><th>Ativo</th><th>Classe</th><th class='n'>Qtd.</th><th class='n'>PM</th><th class='n'>Preço</th><th class='n'>Dia</th><th class='n'>Resultado</th><th class='n'>Valor</th><th>Peso</th></tr></thead><tbody>" +
    (d.pos.map((p, i) => { const r = p.p && p.pm ? p.p / p.pm - 1 : null, w = tot ? vals[i] / tot : 0;
      return `<tr data-t="${esc(p.t)}"><td><b>${esc(p.t)}</b></td><td class="mu">${esc(p.classe)}</td><td class="n">${fmt(p.q, 0)}</td>
      <td class="n">${fmt(p.pm)}</td><td class="n">${fmt(p.p)}</td><td class="n ${cls(p.v)}">${pct(p.v)}</td><td class="n ${cls(r)}">${pct(r)}</td>
      <td class="n">${fmt(vals[i])}</td><td><span class="peso" style="width:${(w * 80).toFixed(0)}px"></span>${pct(w).replace("+", "")}</td></tr>`; }).join("")
    || `<tr><td colspan="9" class="mu">Carteira vazia.</td></tr>`) + "</tbody>";
  $("#alertas").innerHTML = d.alertas.map(a => `<li>#${a.id} ${esc(a.txt)}</li>`).join("") || `<li class="mu">Nenhum. Peça ao Claude: “avise se PETR4 cair abaixo de 35”.</li>`;
  $("#analises").innerHTML = d.analises.slice().reverse().map(a => `<li><b>${esc(a.ticker)}</b> ${esc(a.data)} · ${esc(a.conclusao)}${a.decisao ? " · " + esc(a.decisao) : ""}</li>`).join("") || `<li class="mu">Nenhuma ainda.</li>`;
  if (!S.sel) selecionar(d.pos[0]?.t || S.obs[0]); else listas();
}

// ---------------- eventos
document.addEventListener("click", e => {
  const rm = e.target.closest("[data-rm]");
  if (rm) { S.obs = S.obs.filter(t => t !== rm.dataset.rm); gravar("obs", S.obs); listas(); e.stopPropagation(); return; }
  const tab = e.target.closest("[data-tab]");
  if (tab) { document.querySelectorAll(".tabs button,.tab").forEach(el => el.classList.remove("on")); tab.classList.add("on"); $("#" + tab.dataset.tab).classList.add("on"); return; }
  const f = e.target.closest("[data-f]");
  if (f) { document.querySelectorAll("#faixas button").forEach(b => b.classList.toggle("on", b === f)); S.faixa = f.dataset.f; grafico(); return; }
  const row = e.target.closest("[data-t]");
  if (row) selecionar(row.dataset.t);
});
$("#busca").addEventListener("submit", e => {
  e.preventDefault(); const t = $("#novo").value.trim().toUpperCase(); if (!t) return;
  if (!S.obs.includes(t) && !S.cart.some(p => p.t === t)) { S.obs.push(t); gravar("obs", S.obs); }
  $("#novo").value = ""; selecionar(t);
});
addEventListener("resize", desenhar);
// brilho do vidro acompanha o ponteiro (como a luz no Liquid Glass)
let rafBrilho = 0;
document.addEventListener("pointermove", e => {
  if (rafBrilho) return;
  rafBrilho = requestAnimationFrame(() => { rafBrilho = 0;
    const g = e.target.closest?.(".glass"); if (!g) return;
    const r = g.getBoundingClientRect();
    g.style.setProperty("--mx", `${e.clientX - r.left}px`); g.style.setProperty("--my", `${e.clientY - r.top}px`); });
}, {passive: true});

// ---------------- análise ao vivo (lê os arquivos que cada etapa grava; o Claude escreve os comentários)
const PASSOS = [["coleta", "Coleta de dados"], ["noticias", "Notícias e rumores"], ["exploracao", "Exploração"],
  ["conselho", "Conselho (3 analistas)"], ["nota", "Nota final"], ["relatorio", "Relatório"]];
const NOMES = {valor: "Fundamentalista de valor", macro: "Estrategista macro", risco: "Gestor de risco"};
let liveT = null;
async function live() {
  const t = S.sel; if (!t) return;
  let a; try { a = await api("/api/analise?t=" + encodeURIComponent(t)); } catch { return; }
  const hoje = a?.pasta?.endsWith(new Date().toLocaleDateString("sv-SE"));
  if (!a || (!hoje && !URLP.has("analise"))) { $("#live").hidden = true; return; }
  $("#live").hidden = false;
  const e = a.etapas, feito = k => k === "conselho" ? e.conselho >= 3 : e[k];
  const atual = PASSOS.find(([k]) => !feito(k))?.[0];
  $("#live-st").textContent = e.relatorio ? "Análise concluída" : "Análise em andamento";
  $("#live-st").classList.toggle("fim", !!e.relatorio);
  $("#live-tit").textContent = `${t}${a.metricas.empresa ? " · " + a.metricas.empresa : ""}`;
  html("#passos", PASSOS.map(([k, n]) => `<li class="${feito(k) ? "ok" : k === atual ? "agora" : ""}">${n}${k === "conselho" && e.conselho && e.conselho < 3 ? ` ${e.conselho}/3` : ""}</li>`).join(""));
  if (a.inicio) {
    const fim = a.fim || Date.now(), seg = Math.max(0, (fim - new Date(a.inicio)) / 1000);
    $("#live-tempo").textContent = `${Math.floor(seg / 60)}:${String(Math.floor(seg % 60)).padStart(2, "0")}`;
    $(".timer").classList.toggle("over", seg > 300);
  }
  const m = a.metricas;
  html("#live-num", [["Preço", fmt(m.preco)], ["P/L", fmt(m.p_l, 1)], ["P/VP", fmt(m.p_vp, 2)],
    ["Dividend yield", m.dy == null ? "—" : pct(m.dy).replace("+", "")], ["Volatilidade a.a.", m.vol == null ? "—" : pct(m.vol).replace("+", "")],
    ["Retorno a.a.", pct(m.ret)], ["Nº de Graham", fmt(m.graham)], ["Teto Bazin 6%", fmt(m.bazin)]]
    .filter(([, v]) => v !== "—").map(([k, v]) => `<div><dt>${k}</dt><dd>${v}</dd></div>`).join("") || `<p class="mu">Aguardando a coleta…</p>`);
  html("#live-cons", ["valor", "macro", "risco"].map(k => { const c = a.conselho[k];
    return c ? `<div class="an"><b>${NOMES[k]}</b><span class="nt">${fmt(c.nota, 1)}</span><p>${esc(c.veredito || "")}${c.conviccao ? ` · convicção ${esc(c.conviccao)}` : ""}</p></div>`
      : `<div class="an vazio">${NOMES[k]}: analisando…</div>`; }).join(""));
  html("#live-notas", a.notas.slice().reverse().map(n => `<li><time>${esc(n.h)}</time>${esc(n.txt)}</li>`).join("") || `<li class="mu">Os comentários aparecem aqui enquanto a análise acontece.</li>`);
  const n = a.nota;
  html("#live-final", n ? `<h4>Nota final</h4><div class="big">${fmt(n.nota_final, 1)}<small> / 10</small></div>
    <div class="lei">${esc(n.leitura || "")}</div><div class="mu">quantitativa ${fmt(n.nota_quant, 1)} · conselho ${fmt(n.nota_conselho, 1)} · consenso ${esc(n.consenso)}</div>
    ${(n.travas || []).map(x => `<div class="dn">${esc(x)}</div>`).join("")}${a.relatorio ? `<a class="btn" href="${a.relatorio}" target="_blank">Abrir relatório completo</a>` : ""}`
    : `<h4>Nota final</h4><p class="mu">Sai depois do conselho.</p>${a.lacunas.length ? `<h4>Lacunas</h4><ul>${a.lacunas.map(x => `<li class="mu">${esc(x)}</li>`).join("")}</ul>` : ""}`);
  clearTimeout(liveT); liveT = setTimeout(live, e.relatorio ? 30e3 : 3e3);
}

relogio(); setInterval(relogio, 30e3);
carteira().catch(() => selecionar(S.sel || S.obs[0]));
if (S.sel) selecionar(S.sel);
mundo(); setInterval(mundo, 120e3);
setInterval(cotar, 30e3);
