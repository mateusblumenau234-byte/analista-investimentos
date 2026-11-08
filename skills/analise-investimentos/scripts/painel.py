#!/usr/bin/env python3
"""Painel do investidor em HTML: patrimônio no tempo, alocação, posições, alertas, monitor e análises.

Uso:  python painel.py        (grava <pasta da memória>/../painel.html e mostra o caminho)

Arquivo local, aberto no navegador. Não é publicado em lugar nenhum: contém a carteira do investidor.
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import markdown

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estado as st  # noqa: E402
import memoria as mem  # noqa: E402
from relatorio_html import CSS, e, num  # noqa: E402

EXTRA_CSS = """
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:14px}
.kpi{background:var(--panel);border:1px solid var(--rule);border-radius:6px;padding:14px}
.kpi b{display:block;font:600 1.5rem/1.2 var(--mono)}.kpi span{color:var(--muted);font-size:.82rem}
.alloc{display:grid;gap:8px}.alloc .dim{grid-template-columns:150px 1fr 60px}
td.up{color:var(--good)}td.down{color:var(--bad)}
"""


def grafico_patrimonio(serie: list[dict]) -> str:
    if len(serie) < 2:
        return '<p class="note">O gráfico aparece depois de duas leituras do monitor (uma por dia).</p>'
    W, H, m = 640, 220, 44
    vs = [s["valor"] for s in serie]
    lo, hi = min(vs), max(vs)
    hi = hi if hi > lo else lo + 1
    def x(i):
        return m + i * (W - 2 * m) / (len(vs) - 1)
    def y(v):
        return H - 28 - (v - lo) * (H - 56) / (hi - lo)
    pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(vs))
    grade = "".join(f'<line x1="{m}" x2="{W - m}" y1="{y(v):.1f}" y2="{y(v):.1f}" class="grid"/>'
                    f'<text x="{m - 6}" y="{y(v) + 4:.1f}" class="axis" text-anchor="end">{num(v, 0)}</text>'
                    for v in (lo, (lo + hi) / 2, hi))
    datas = (f'<text x="{m}" y="{H - 8}" class="axis">{e(serie[0]["data"])}</text>'
             f'<text x="{W - m}" y="{H - 8}" class="axis" text-anchor="end">{e(serie[-1]["data"])}</text>')
    return (f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Patrimônio cotado de {e(serie[0]["data"])} a '
            f'{e(serie[-1]["data"])}">{grade}{datas}<polyline points="{pts}" class="line s1"/></svg>')


def gerar(destino: Path | None = None) -> Path:
    destino = destino or mem.DADOS.parent / "painel.html"
    linhas, data_cart = mem.ler_carteira()
    snaps = {s["ativo"]: s for s in st.snapshots_do_dia()}
    precos = {a: s["preco"] for a, s in snaps.items()}
    serie = st.serie_patrimonio()
    aloc = mem.alocacao_por_classe(precos)
    total_aloc = sum(aloc.values()) or 1

    linhas_tab, custo, valor = [], 0.0, 0.0
    for r in sorted(linhas, key=lambda r: -(r["cotas_num"] or 0) * (precos.get(r["ativo"]) or r["preco_medio_num"] or 0)):
        q, pm, px = r["cotas_num"], r["preco_medio_num"], precos.get(r["ativo"])
        res = px / pm - 1 if px and pm else None
        v = q * (px or pm or 0) if q else None
        if q and pm:
            custo += q * pm
            valor += q * (px or pm)
        cls = "" if res is None else "up" if res >= 0 else "down"
        linhas_tab.append(f"<tr><td>{e(r['ativo'])}</td><td>{e(r.get('classe', ''))}</td><td class='n'>{num(q, 0)}</td>"
                          f"<td class='n'>{num(pm, 2)}</td><td class='n'>{num(px, 2)}</td>"
                          f"<td class='n {cls}'>{num(res, 1, pct=True)}</td><td class='n'>{num(v, 2)}</td>"
                          f"<td>{e(r.get('status', ''))}</td></tr>")

    barras = "".join(f'<div class="dim"><span>{e(k)}</span><div class="bar-bg"><div class="bar-fg mid" '
                     f'style="width:{v / total_aloc * 100:.1f}%"></div></div><span class="n">{num(v / total_aloc, 1, pct=True)}'
                     f'</span></div>' for k, v in sorted(aloc.items(), key=lambda x: -x[1]))
    alertas = "".join(f"<li>#{a['id']} {e(st.descrever(a))}{(' · ' + e(a['nota'])) if a['nota'] else ''}</li>"
                      for a in st.listar_alertas()) or "<li>Nenhum alerta ativo.</li>"
    eventos = "".join(f"<li><b>{e(ev['quando'][:16].replace('T', ' '))}</b> · {e(ev['tipo'])} · {e(ev['texto'])}</li>"
                      for ev in st.eventos_recentes(15)) or "<li>Nada registrado ainda.</li>"
    hist = []
    for h in reversed(mem.ler_historico()[-20:]):
        rel = Path(h.get("pasta") or "") / "relatorio.html"
        link = f' · <a href="{e(rel.resolve().as_uri())}">relatório</a>' if h.get("pasta") and rel.exists() else ""
        hist.append(f"<tr><td>{e(h.get('data'))}</td><td>{e(h.get('ticker'))}</td><td>{e(h.get('motivo'))}</td>"
                    f"<td class='n'>{e(h.get('nota') or '')}</td><td>{e(h.get('conclusao'))}{link}</td></tr>")
    mon = mem.DADOS / "monitor" / "ultimo.md"
    monitor = (markdown.markdown(mon.read_text(encoding="utf-8").split("\n", 1)[1], extensions=["tables"])
               if mon.exists() else "<p>O monitor ainda não rodou. Peça: <i>rode o monitor da carteira</i>.</p>")
    var_total = valor / custo - 1 if custo else None

    html_doc = f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Painel do investidor</title>
<style>{CSS}{EXTRA_CSS}</style></head><body><main class="wrap">
<header class="masthead"><span class="eyebrow">Analista de investimentos</span><h1>Painel do investidor</h1>
<div class="meta"><span>Gerado em <b>{dt.datetime.now():%d/%m/%Y %H:%M}</b></span>
<span>Carteira registrada em <b>{e(data_cart or 'sem data')}</b></span></div></header>
<section class="kpis">
<div class="kpi"><b>{num(valor, 2)}</b><span>Valor das posições (cotação do monitor ou preço médio)</span></div>
<div class="kpi"><b>{num(custo, 2)}</b><span>Custo pelo preço médio</span></div>
<div class="kpi"><b class="{'good' if (var_total or 0) >= 0 else 'bad'}">{num(var_total, 1, pct=True)}</b><span>Resultado sobre o custo</span></div>
<div class="kpi"><b>{len(linhas)}</b><span>Posições</span></div></section>
<section><h2>Patrimônio cotado</h2><figure class="chart scroll">{grafico_patrimonio(serie)}
<figcaption>Soma das posições cotadas em cada leitura do monitor, em moedas originais.</figcaption></figure></section>
<section><h2>Alocação por classe</h2><div class="alloc">{barras or '<p>Carteira vazia.</p>'}</div></section>
<section><h2>Posições</h2><div class="scroll"><table><thead><tr><th>Ativo</th><th>Classe</th><th>Cotas</th>
<th>Preço médio</th><th>Último preço</th><th>Resultado</th><th>Valor</th><th>Status</th></tr></thead>
<tbody>{''.join(linhas_tab) or '<tr><td colspan="8">Nenhuma posição registrada.</td></tr>'}</tbody></table></div></section>
<section><h2>Último monitor</h2><div class="body">{monitor}</div></section>
<section><h2>Alertas ativos</h2><ul>{alertas}</ul></section>
<section><h2>Análises feitas</h2><div class="scroll"><table><thead><tr><th>Data</th><th>Ativo</th><th>Motivo</th>
<th>Nota</th><th>Conclusão</th></tr></thead><tbody>{''.join(hist) or '<tr><td colspan="5">Nenhuma ainda.</td></tr>'}
</tbody></table></div></section>
<section><h2>Linha do tempo</h2><ul>{eventos}</ul></section>
<p class="disclaimer">Painel local com dados observados. Não é recomendação de investimento.</p>
</main></body></html>"""
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(html_doc, encoding="utf-8")
    return destino


if __name__ == "__main__":
    print(gerar())
