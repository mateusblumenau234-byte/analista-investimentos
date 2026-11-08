#!/usr/bin/env python3
"""Monitor da carteira: cota cada posição, guarda o patrimônio do dia, confere alertas e varre notícias.

Uso:  python monitor.py [--sem-noticias] [--dias 3]

Pensado para rodar sozinho todo dia (tarefa agendada) ou pela ferramenta `monitorar` do servidor MCP.
Grava em <dados>/monitor/: ultimo.md (resumo para o investidor), ultimo.json e uma pasta por ativo com o
radar de notícias. Depois atualiza o painel (painel.html).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estado as st  # noqa: E402
import memoria as mem  # noqa: E402
import mercados as mk  # noqa: E402


def posicoes() -> list[dict]:
    """Posições com cotação em bolsa e cotas informadas."""
    linhas, _ = mem.ler_carteira()
    out = []
    for r in linhas:
        if "exclu" in r.get("status", "").lower() or not r.get("cotas_num"):
            continue
        if any(s in r.get("classe", "").lower() for s in mem.SEM_COTACAO):
            continue
        out.append(r)
    return out


def _cotar_padrao(ticker: str) -> dict:
    import fontes as fx
    return fx.cotacao_atual(ticker)


def _radar(ticker: str, dias: int, baixar=None) -> list[dict]:
    import noticias as nt
    pasta = mem.DADOS / "monitor" / ticker
    idiomas = "pt,en" if mk.eh_b3(ticker) else "en,pt"
    args = ["--empresa", ticker, "--ticker", ticker, "--sem-global", "--dias", str(dias), "--idiomas", idiomas,
            "--saida", str(pasta)]
    nt.main(args, **({"baixar": baixar} if baixar else {}))
    return json.loads((pasta / "noticias.json").read_text(encoding="utf-8"))


def rodar(cotar=_cotar_padrao, noticias: bool = True, dias: int = 3, baixar=None, hoje: str | None = None) -> dict:
    hoje = hoje or dt.date.today().isoformat()
    leituras, falhas, destaques, rumores = {}, [], {}, {}
    for r in posicoes():
        tk = r["ativo"]
        try:
            c = cotar(tk)
            preco = float(c["preco"])
        except Exception as e:  # noqa: BLE001
            falhas.append(f"{tk}: cotação indisponível ({type(e).__name__})")
            continue
        anterior = st.ultimo_preco(tk, hoje)
        var = preco / anterior - 1 if anterior else None
        st.registrar_snapshot(hoje, tk, r["cotas_num"], preco, c.get("moeda"), c.get("horario") or "")
        leituras[tk] = {"preco": preco, "variacao": var, "moeda": c.get("moeda"), "cotas": r["cotas_num"],
                        "preco_medio": r.get("preco_medio_num"), "valor": r["cotas_num"] * preco}
        if noticias:
            try:
                itens = _radar(tk, dias, baixar)
            except Exception as e:  # noqa: BLE001
                falhas.append(f"{tk}: radar de notícias falhou ({type(e).__name__})")
                itens = []
            destaques[tk] = [i for i in itens if i.get("escopo") == "empresa"][:5]
            rumores[tk] = [i for i in itens if i.get("nivel_rumor")]
    disparados = st.avaliar_alertas(leituras, rumores)
    total = sum(x["valor"] for x in leituras.values())
    res = {"data": hoje, "patrimonio_cotado": total, "leituras": leituras, "alertas": disparados,
           "destaques": destaques, "rumores": {k: v for k, v in rumores.items() if v}, "falhas": falhas}
    st.registrar_evento("monitor", None, f"{len(leituras)} posições cotadas, {len(disparados)} alertas, "
                                         f"{len(falhas)} falhas")
    pasta = mem.DADOS / "monitor"
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / "ultimo.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    (pasta / "ultimo.md").write_text(resumo_md(res), encoding="utf-8")
    import painel
    res["painel"] = str(painel.gerar())
    return res


def _pct(v) -> str:
    return "n/d" if v is None else f"{v * 100:+.1f}%".replace(".", ",")


def resumo_md(res: dict) -> str:
    md = [f"# Monitor da carteira: {res['data']}", ""]
    if res["alertas"]:
        md += ["## Alertas disparados", *(f"- **{a['ativo']}**: {a['motivo']}" for a in res["alertas"]), ""]
    md += ["## Posições", "| Ativo | Preço | Desde a última leitura | Resultado sobre o preço médio | Valor |",
           "|---|---|---|---|---|"]
    for tk, l in sorted(res["leituras"].items(), key=lambda x: -x[1]["valor"]):
        pm = l.get("preco_medio")
        md.append(f"| {tk} | {l['preco']:,.2f} {l.get('moeda') or ''} | {_pct(l['variacao'])} | "
                  f"{_pct(l['preco'] / pm - 1 if pm else None)} | {l['valor']:,.2f} |")
    md += ["", f"Patrimônio cotado (soma em moedas originais): {res['patrimonio_cotado']:,.2f}", ""]
    if res["rumores"]:
        md += ["## Rumores sobre a carteira (o agente confirma ou corrige o nível)"]
        for tk, its in res["rumores"].items():
            md += [f"- **{tk}** · {i['nivel_rumor']} · [{i['titulo']}]({i['link']})" for i in its[:3]]
        md.append("")
    if any(res["destaques"].values()):
        md.append("## Notícias de maior nota")
        for tk, its in res["destaques"].items():
            md += [f"- **{tk}** · {i.get('fonte') or '?'} · [{i['titulo']}]({i['link']})" for i in its[:3]]
        md.append("")
    if res["falhas"]:
        md += ["## Falhas", *(f"- {f}" for f in res["falhas"]), ""]
    md.append("Dados observados, sem recomendação. Confirme fatos na fonte primária antes de decidir.")
    return "\n".join(md)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sem-noticias", action="store_true")
    ap.add_argument("--dias", type=int, default=3)
    a = ap.parse_args(argv)
    res = rodar(noticias=not a.sem_noticias, dias=a.dias)
    print(resumo_md(res))
    print(f"\nPainel: {res['painel']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
