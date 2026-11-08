"""Testes offline do app: estado persistente, alertas, monitor, painel e servidor MCP."""
import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import estado as st  # noqa: E402
import memoria as mem  # noqa: E402
import monitor as mo  # noqa: E402
import painel as pn  # noqa: E402


@pytest.fixture
def dados(tmp_path, monkeypatch):
    monkeypatch.setattr(mem, "DADOS", tmp_path / "dados")
    mem.garantir_dados()
    mem.cmd_atualizar("PETR4", 100, 30.0, "Ações BR", "Ativa", None)
    mem.cmd_atualizar("AAPL", 10, 150.0, "Ações EUA", "Ativa", None)
    mem.cmd_atualizar("TESOURO SELIC", 1, 15000.0, "Renda fixa", "Ativa", None)
    return tmp_path


def test_alertas_disparam_uma_vez(dados):
    with pytest.raises(ValueError):
        st.criar_alerta("PETR4", "inexistente", 1)
    with pytest.raises(ValueError):
        st.criar_alerta("PETR4", "preco_abaixo")
    st.criar_alerta("petr4", "preco_abaixo", 28)
    st.criar_alerta("PETR4", "queda_dia", 5)
    st.criar_alerta("AAPL", "rumor")
    leituras = {"PETR4": {"preco": 27.5, "variacao": -0.06}, "AAPL": {"preco": 200.0, "variacao": 0.01}}
    rumores = {"AAPL": [{"titulo": "Apple em negociação", "nivel_rumor": "provavel"}]}
    disp = st.avaliar_alertas(leituras, rumores)
    assert {d["tipo"] for d in disp} == {"preco_abaixo", "queda_dia", "rumor"}
    assert st.listar_alertas() == [] and st.avaliar_alertas(leituras, rumores) == []
    assert any(ev["tipo"] == "alerta" for ev in st.eventos_recentes())


def test_monitor_grava_patrimonio_e_painel(dados):
    precos = {"PETR4": [32.0, 30.0], "AAPL": [180.0, 190.0]}
    def cotar(tk):
        return {"preco": precos[tk].pop(0), "moeda": "BRL" if tk == "PETR4" else "USD", "horario": "teste"}
    st.criar_alerta("PETR4", "queda_dia", 5)
    r1 = mo.rodar(cotar=cotar, noticias=False, hoje="2026-11-06")
    assert set(r1["leituras"]) == {"PETR4", "AAPL"}                 # renda fixa fica fora da cotação
    assert r1["leituras"]["PETR4"]["variacao"] is None
    r2 = mo.rodar(cotar=cotar, noticias=False, hoje="2026-11-07")
    assert r2["leituras"]["PETR4"]["variacao"] == pytest.approx(30 / 32 - 1)
    assert [a["tipo"] for a in r2["alertas"]] == ["queda_dia"]
    serie = st.serie_patrimonio()
    assert [s["data"] for s in serie] == ["2026-11-06", "2026-11-07"]
    assert serie[1]["valor"] == pytest.approx(100 * 30 + 10 * 190)
    md = (mem.DADOS / "monitor" / "ultimo.md").read_text(encoding="utf-8")
    assert "Alertas disparados" in md and "PETR4" in md
    html = Path(r2["painel"]).read_text(encoding="utf-8")
    assert "Painel do investidor" in html and "<polyline" in html and "TESOURO SELIC" in html


def test_monitor_registra_falha_sem_parar(dados):
    def cotar(tk):
        if tk == "AAPL":
            raise ConnectionError("fora do ar")
        return {"preco": 31.0}
    def baixar(url):
        return "<rss><channel></channel></rss>"
    r = mo.rodar(cotar=cotar, noticias=True, baixar=baixar, hoje="2026-11-08")
    assert list(r["leituras"]) == ["PETR4"] and "AAPL" in r["falhas"][0]
    assert (mem.DADOS / "monitor" / "PETR4" / "noticias.md").exists()


def test_painel_com_carteira_vazia(tmp_path, monkeypatch):
    monkeypatch.setattr(mem, "DADOS", tmp_path / "dados")
    html = pn.gerar().read_text(encoding="utf-8")
    assert "Nenhuma posição registrada" in html and "monitor ainda não rodou" in html


def test_servidor_mcp_expoe_ferramentas(dados):
    pytest.importorskip("mcp")
    import asyncio
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "servidor"))
    import analista as srv
    nomes = {t.name for t in asyncio.run(srv.mcp.list_tools())}
    assert {"carteira", "cotacao", "noticias", "analisar_ativo", "monitorar", "criar_alerta", "painel",
            "registrar_operacao", "valuation_dcf"} <= nomes
    info = json.loads(srv.carteira())
    assert {p["ativo"] for p in info["posicoes"]} == {"PETR4", "AAPL", "TESOURO SELIC"}
    assert "Alerta #1" in srv.criar_alerta("PETR4", "preco_acima", 40)
    assert srv.criar_alerta("PETR4", "errado").startswith("Erro: ValueError")   # erro vira texto, não derruba
    assert "PETR4 = 50 cotas a PM 30.00" in srv.registrar_operacao("PETR4", -50, 35.0)   # venda mantém o PM


def test_homebroker_api(dados, monkeypatch):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "servidor"))
    import urllib.request
    import pandas as pd
    import provedores as pv
    import web
    web._cache.clear()
    def chart(t, faixa):
        if t != "PETR4":
            raise ConnectionError("429")
        return {"meta": {"regularMarketPrice": 33.0, "chartPreviousClose": 30.0, "currency": "BRL", "shortName": "Petro"},
                "timestamp": [1, 2, 3], "indicators": {"quote": [{"close": [30.0, None, 33.0]}]}}
    monkeypatch.setattr(web, "_chart", chart)
    idx = pd.to_datetime(["2026-11-05", "2026-11-06"])
    monkeypatch.setattr(pv, "serie", lambda t, a, pular=frozenset(): (pd.Series([200.0, 210.0], index=idx), "stooq", []))
    q = {c["t"]: c for c in web.cotacoes(["PETR4", "AAPL", "^N225"])}
    assert q["PETR4"]["p"] == 33.0 and q["PETR4"]["v"] == pytest.approx(0.1)
    assert q["AAPL"]["f"] == "stooq" and q["AAPL"]["v"] == pytest.approx(0.05)    # reserva quando o Yahoo recusa
    assert q["^N225"]["p"] is None                                                 # índice nunca vira preço de ETF
    assert web.historico("PETR4", "6m")["pts"] == [[1, 30.0], [3, 33.0]]
    url = web.iniciar(0)                                                           # porta livre
    cart = json.loads(urllib.request.urlopen(url + "/api/carteira").read())
    assert {p["t"] for p in cart["pos"]} == {"PETR4", "AAPL", "TESOURO SELIC"}
    assert b"Homebroker" in urllib.request.urlopen(url + "/").read()
    with pytest.raises(urllib.error.HTTPError):
        urllib.request.urlopen(url + "/../servidor/analista.py")


def test_analise_ao_vivo(dados, tmp_path, monkeypatch):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "servidor"))
    import urllib.request
    import web
    monkeypatch.setattr(web, "RELATORIOS", tmp_path / "relatorios")
    url = web.abrir_analise("bbas3")
    assert url.endswith("/?t=BBAS3&analise=1")
    p = web.pasta_analise("BBAS3")
    a = web.analise("BBAS3")
    assert a["inicio"] and a["etapas"]["conselho"] == 0 and not a["etapas"]["relatorio"]
    web.anotar("BBAS3", "P/VP de 0,53.")
    (p / "dados.json").write_text(json.dumps({"multiplos": {"preco": 17.1, "p_vp": 0.53}}), encoding="utf-8")
    (p / "parecer_risco.json").write_text(json.dumps({"nota": 3.5, "veredito": "cautela"}), encoding="utf-8")
    (p / "relatorio.html").write_text("<h1>ok</h1>", encoding="utf-8")
    a = web.analise("BBAS3")
    assert a["notas"][0]["txt"] == "P/VP de 0,53." and a["metricas"]["p_vp"] == 0.53
    assert a["conselho"]["risco"]["nota"] == 3.5 and a["etapas"]["relatorio"] and a["fim"]
    base = url.split("/?")[0]
    assert urllib.request.urlopen(base + a["relatorio"]).read() == b"<h1>ok</h1>"
    assert web.analise("XPTO3") is None
