#!/usr/bin/env python3
"""Servidor MCP do analista de investimentos: dá ao Claude ferramentas próprias, em qualquer conversa.

Roda no computador do investidor (stdio) e usa os mesmos módulos da skill: dados em tempo real (CVM, SEC,
bancos centrais, Yahoo, Stooq, FRED, Alpha Vantage), radar de notícias, valuation, carteira persistente,
alertas, monitor diário e painel HTML. Os dados pessoais ficam em ~/.analise-investimentos (ou ANALISE_DADOS).

Registro: o plugin já declara o servidor em .mcp.json. Para usar fora do plugin:
  claude mcp add analista -- python <caminho>/servidor/analista.py
"""
from __future__ import annotations

import contextlib
import functools
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
SCRIPTS = RAIZ / "skills" / "analise-investimentos" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from mcp.server.fastmcp import FastMCP  # noqa: E402

import estado as st  # noqa: E402
import memoria as mem  # noqa: E402

RELATORIOS = Path(os.environ.get("ANALISE_RELATORIOS", mem.DADOS.parent / "relatorios"))
mcp = FastMCP("analista", instructions=(
    "Ferramentas do analista de investimentos. Antes de analisar um ativo, leia `carteira` (perfil, posições, "
    "alertas). Use dados destas ferramentas e cite a fonte; nunca invente números. Siga a skill "
    "analise-investimentos para o método completo (conselho de 3 analistas, nota, relatório). Registrar "
    "posições, compras, alertas e análises só quando o investidor pedir ou confirmar. Não é recomendação."))


def ferramenta(fn):
    """Registra a ferramenta e desvia prints para stderr (stdout é o canal do protocolo MCP)."""
    @functools.wraps(fn)
    def envolta(*a, **k):
        with contextlib.redirect_stdout(sys.stderr):
            try:
                return fn(*a, **k)
            except SystemExit as e:
                return f"Erro: {e}"
            except Exception as e:  # noqa: BLE001
                return f"Erro: {type(e).__name__}: {e}"
    return mcp.tool()(envolta)


def _rodar_script(nome: str, args: list[str], timeout: int = 900) -> str:
    r = subprocess.run([sys.executable, str(SCRIPTS / nome), *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout, cwd=str(RELATORIOS.parent))
    saida = (r.stdout + ("\n" + r.stderr if r.returncode else "")).strip()
    return saida[-6000:]


def _df_texto(df, linhas: int = 60) -> str:
    return df.head(linhas).to_string() if df is not None and len(df) else "sem dados"


# ---------------------------------------------------------------- memória e carteira
@ferramenta
def carteira() -> str:
    """Perfil do investidor, posições registradas, alertas ativos e último monitor. Use no começo de toda análise."""
    mem.garantir_dados()
    linhas, data = mem.ler_carteira()
    pos = [{k: r.get(k) for k in mem.CAMPOS_CARTEIRA} for r in linhas]
    mon = mem.DADOS / "monitor" / "ultimo.md"
    return json.dumps({"pasta_dados": str(mem.DADOS), "perfil": mem.perfil_texto(), "carteira_atualizada_em": data,
                       "posicoes": pos,
                       "alertas_ativos": [f"#{a['id']} {st.descrever(a)}" for a in st.listar_alertas()],
                       "ultimo_monitor": mon.read_text(encoding="utf-8") if mon.exists() else None,
                       "ultimas_analises": mem.ler_historico()[-10:]}, ensure_ascii=False, indent=1)


@ferramenta
def resumo_do_ativo(ticker: str) -> str:
    """O que já se sabe do investidor sobre este ativo (posição, histórico) e as perguntas que ainda faltam."""
    mem.garantir_dados()
    return mem.cmd_resumo(ticker)


@ferramenta
def registrar_posicao(ativo: str, cotas: float | None = None, preco_medio: float | None = None,
                      classe: str | None = None, status: str | None = None, observacao: str | None = None) -> str:
    """Grava ou corrige uma posição da carteira (só com dados que o investidor informou)."""
    mem.garantir_dados()
    r = mem.cmd_atualizar(ativo, cotas, preco_medio, classe, status, observacao)
    st.registrar_evento("carteira", ativo, r)
    return r


@ferramenta
def registrar_operacao(ativo: str, cotas: float, preco: float) -> str:
    """Soma uma compra (cotas > 0) ou uma venda (cotas < 0) e recalcula o preço médio."""
    mem.garantir_dados()
    r = mem.cmd_compra(ativo, cotas, preco)
    st.registrar_evento("compra" if cotas > 0 else "venda", ativo, f"{cotas:g} cotas a {preco:g}. {r}")
    return r


@ferramenta
def registrar_analise(ticker: str, motivo: str, conclusao: str, nota: float | None = None, preco: float | None = None,
                      decisao: str | None = None, pasta: str | None = None) -> str:
    """Acrescenta uma análise concluída ao histórico (motivo: comprar, manter, vender, aportar...)."""
    import argparse
    mem.garantir_dados()
    r = mem.cmd_registrar(argparse.Namespace(ticker=ticker, motivo=motivo, conclusao=conclusao, nota=nota,
                                             preco=preco, decisao=decisao, pasta=pasta))
    st.registrar_evento("analise", ticker, conclusao)
    return r


# ---------------------------------------------------------------- dados de mercado
@ferramenta
def cotacao(tickers: list[str], conferir: bool = False) -> str:
    """Cotação atual de ativos de qualquer bolsa (PETR4, AAPL, ASML.AS, ^BVSP, USDBRL=X).
    conferir=True compara o último fechamento em duas fontes independentes."""
    import fontes as fx
    import provedores as pv
    out = {}
    for t in tickers:
        try:
            out[t] = pv.conferir_ultimo_preco(t) if conferir else fx.cotacao_atual(t)
        except Exception as e:  # noqa: BLE001
            out[t] = {"erro": f"{type(e).__name__}: {e}"}
    return json.dumps(out, ensure_ascii=False, indent=1, default=str)


@ferramenta
def painel_mundial() -> str:
    """Painel mundial: bolsas, juros, dólar, VIX, commodities e cripto, com variação em 1, 3 e 12 meses."""
    import fontes as fx
    return _df_texto(fx.painel_global(1), 80)


@ferramenta
def serie_bcb(serie: str, anos: int = 2) -> str:
    """Série do Banco Central (SGS): ex. 432 Selic meta, 12 CDI, 433 IPCA, 1 dólar. Últimos valores."""
    import datetime as dt
    import fontes as fx
    s = fx.bcb_sgs(serie, dt.date.today() - dt.timedelta(days=365 * anos))
    return s.tail(24).to_string()


@ferramenta
def focus(indicador: str = "IPCA") -> str:
    """Expectativas do boletim Focus (IPCA, Selic, PIB Total, Câmbio)."""
    import fontes as fx
    return _df_texto(fx.bcb_focus(indicador), 40)


@ferramenta
def noticias(empresa: str, ticker: str | None = None, setor: str | None = None, brasil: bool = False,
             dias: int = 30, extras_composio: str | None = None) -> str:
    """Radar de notícias: empresa, setor, mundo e (brasil=True) política e fiscal do Brasil, com rumores
    classificados por credibilidade. extras_composio: JSON de notícias trazidas pelo Composio (por exemplo a
    resposta do ALPHA_VANTAGE_NEWS_SENTIMENT), que entram na mesma classificação."""
    import noticias as nt
    pasta = Path(tempfile.mkdtemp(prefix="radar_"))
    args = ["--empresa", empresa, "--dias", str(dias), "--saida", str(pasta)]
    if ticker:
        args += ["--ticker", ticker]
    if setor:
        args += ["--setor", setor]
    if brasil:
        args.append("--brasil")
    if extras_composio:
        (pasta / "extras.json").write_text(extras_composio, encoding="utf-8")
        args += ["--extras", str(pasta / "extras.json")]
    nt.main(args)
    return (pasta / "noticias.md").read_text(encoding="utf-8")


# ---------------------------------------------------------------- análise
@ferramenta
def analisar_ativo(ticker: str, pares: str | None = None, horizonte: int = 5,
                   objetivo: str = "equilibrio", premissas_json: str | None = None) -> str:
    """Coleta quantitativa completa (demonstrações CVM/SEC, múltiplos, preços, Markowitz com a carteira real,
    painel mundial e DCF se houver premissas) e exploração dos dados. Devolve a pasta e o relatório
    quantitativo. Demora alguns minutos. pares: concorrentes separados por vírgula."""
    RELATORIOS.mkdir(parents=True, exist_ok=True)
    args = ["--ticker", ticker, "--horizonte", str(horizonte), "--objetivo", objetivo, "--saida", str(RELATORIOS)]
    if pares:
        args += ["--pares", pares]
    if premissas_json:
        arq = RELATORIOS / f"premissas_{ticker.upper()}.json"
        arq.write_text(premissas_json, encoding="utf-8")
        args += ["--premissas", str(arq)]
    log = _rodar_script("analisar.py", args)
    pastas = sorted(RELATORIOS.glob(f"{ticker.upper()}_*"), key=lambda p: p.stat().st_mtime)
    if not pastas:
        return f"A coleta não gerou pasta.\n{log}"
    pasta = pastas[-1]
    _rodar_script("explorar_dados.py", [str(pasta)])
    rel = pasta / "relatorio_quantitativo.md"
    corpo = rel.read_text(encoding="utf-8") if rel.exists() else log
    return f"Pasta: {pasta}\n\n{corpo[:20000]}"


@ferramenta
def valuation_dcf(premissas_json: str) -> str:
    """DCF (FCFF) com cenários a partir de premissas documentadas (formato de references/premissas_exemplo.json).
    Sem valores padrão: se faltar premissa, a resposta lista o que falta."""
    import valuation as va
    p = json.loads(premissas_json)
    base = va.dcf_fcff(p)
    return json.dumps({"base": {k: v for k, v in base.items() if k != "projecao"}, "cenarios": va.cenarios(p)},
                      ensure_ascii=False, indent=1, default=float)


@ferramenta
def nota_final(pasta: str) -> str:
    """Consolida a nota (50% regras quantitativas, 50% conselho) a partir de dados.json e dos parecer_*.json
    gravados pelos 3 analistas na pasta da análise."""
    return _rodar_script("nota.py", [pasta])


@ferramenta
def relatorio_html(pasta: str) -> str:
    """Gera o relatório profissional em HTML (gráficos, nota, conselho) na pasta da análise."""
    import relatorio_html as rh
    return str(rh.main(Path(pasta)))


# ---------------------------------------------------------------- monitor, alertas e painel
@ferramenta
def monitorar(noticias: bool = True, dias: int = 3) -> str:
    """Cota toda a carteira, grava o patrimônio do dia, confere alertas, varre notícias e rumores de cada
    posição e atualiza o painel. É o que roda sozinho todo dia."""
    import monitor as mo
    res = mo.rodar(noticias=noticias, dias=dias)
    return mo.resumo_md(res) + f"\n\nPainel: {res['painel']}"


@ferramenta
def criar_alerta(ativo: str, tipo: str, valor: float | None = None, nota: str = "") -> str:
    """Cria um alerta que o monitor confere. tipos: preco_abaixo, preco_acima, queda_dia (%), alta_dia (%),
    rumor (dispara com rumor provável ou real)."""
    i = st.criar_alerta(ativo, tipo, valor, nota)
    return f"Alerta #{i} criado: {st.descrever({'ativo': ativo.upper(), 'tipo': tipo, 'valor': valor})}"


@ferramenta
def alertas(incluir_disparados: bool = False) -> str:
    """Lista os alertas (ativos e, se pedido, os que já dispararam)."""
    return json.dumps(st.listar_alertas(not incluir_disparados), ensure_ascii=False, indent=1)


@ferramenta
def remover_alerta(id_alerta: int) -> str:
    """Apaga um alerta pelo número."""
    return "Removido." if st.remover_alerta(id_alerta) else "Alerta não encontrado."


@ferramenta
def painel() -> str:
    """Gera o painel do investidor (HTML local com patrimônio, alocação, posições, alertas e análises) e
    devolve o caminho para abrir no navegador."""
    import painel as pn
    return str(pn.gerar())


if __name__ == "__main__":
    mcp.run()
