"""Testes offline da parte global: mercados, SEC, câmbio e radar de notícias."""
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import mercados as mk  # noqa: E402
import noticias as nt  # noqa: E402
import sec as sc  # noqa: E402


@pytest.mark.parametrize("ticker,codigo,moeda,yahoo", [
    ("PETR4", "B3", "BRL", "PETR4.SA"), ("BOVA11", "B3", "BRL", "BOVA11.SA"), ("ITUB4.SA", "B3", "BRL", "ITUB4.SA"),
    ("AAPL", "EUA", "USD", "AAPL"), ("BRK-B", "EUA", "USD", "BRK-B"), ("ASML.AS", ".AS", "EUR", "ASML.AS"),
    ("7203.T", ".T", "JPY", "7203.T"), ("0700.HK", ".HK", "HKD", "0700.HK"), ("SHOP.TO", ".TO", "CAD", "SHOP.TO"),
])
def test_mercados(ticker, codigo, moeda, yahoo):
    m = mk.mercado(ticker)
    assert (m.codigo, m.moeda) == (codigo, moeda)
    assert mk.simbolo_yahoo(ticker) == yahoo


def test_indices_e_cambio_nao_ganham_sufixo():
    assert mk.simbolo_yahoo("^GSPC") == "^GSPC"
    assert mk.simbolo_yahoo("USDBRL=X") == "USDBRL=X"
    assert mk.par_cambio("USD", "BRL") == "USDBRL=X" and mk.par_cambio("BRL", "brl") is None


def _fato(val, ano, fluxo=True, form="10-K"):
    d = {"val": val, "end": f"{ano}-12-31", "form": form, "fp": "FY", "filed": f"{ano + 1}-02-01"}
    if fluxo:
        d["start"] = f"{ano}-01-01"
    return d


def test_sec_tabela_e_indicadores():
    anos = [2022, 2023, 2024]
    usd = lambda vals, fluxo=True: {"units": {"USD": [_fato(v, a, fluxo) for v, a in zip(vals, anos)]}}  # noqa: E731
    facts = {"facts": {"us-gaap": {
        "Revenues": usd([100, 110, 121]),
        "OperatingIncomeLoss": usd([20, 22, 24]),
        "NetIncomeLoss": usd([15, 16, 18]),
        "StockholdersEquity": usd([100, 110, 120], False),
        "Assets": usd([200, 210, 220], False),
        "NetCashProvidedByUsedInOperatingActivities": usd([18, 20, 22]),
        "PaymentsToAcquirePropertyPlantAndEquipment": usd([5, 5, 6]),
        "LongTermDebtNoncurrent": usd([30, 30, 30], False),
        "CashAndCashEquivalentsAtCarryingValue": usd([10, 12, 14], False),
        "WeightedAverageNumberOfDilutedSharesOutstanding": {"units": {"shares": [_fato(10, a) for a in anos]}},
    }}}
    # um 10-Q trimestral não pode entrar na série anual
    facts["facts"]["us-gaap"]["Revenues"]["units"]["USD"].append(
        {"val": 30, "start": "2024-07-01", "end": "2024-09-30", "form": "10-Q", "fp": "Q3", "filed": "2024-11-01"})
    t = sc.tabela_anual_sec(facts)
    assert list(t.columns) == anos and t.loc["receita_liquida", 2024] == 121
    i = sc.indicadores_sec(t)
    assert i.loc[2024, "crescimento_receita"] == pytest.approx(0.10)
    assert i.loc[2024, "roe"] == pytest.approx(18 / 115)
    assert i.loc[2024, "fcf"] == 16 and i.loc[2024, "divida_liquida"] == 16
    m = sc.multiplos_sec(i, 36.0)
    assert m["p_l"] == pytest.approx(360 / 18) and m["lpa"] == pytest.approx(1.8)


def test_conversao_de_moeda(monkeypatch):
    import analisar
    import fontes as fx
    idx = pd.bdate_range("2025-01-01", periods=5)
    px = pd.DataFrame({"AAPL": [100.0] * 5, "PETR4": [30.0] * 5, "^GSPC": [5000.0] * 5}, index=idx)
    cambio = pd.DataFrame({"USDBRL=X": [5.0, 5.0, 5.5, 5.5, 6.0]}, index=idx)
    monkeypatch.setattr(fx, "_precos_yahoo", lambda s, a: (cambio, []))
    conv, avisos = analisar.converter_moeda(px, "BRL", 1)
    assert list(conv["AAPL"]) == [500, 500, 550, 550, 600]
    assert list(conv["PETR4"]) == [30.0] * 5 and list(conv["^GSPC"]) == [5000.0] * 5
    assert any("AAPL" in a for a in avisos)


RSS = """<?xml version="1.0"?><rss><channel>
<item><title>Apple in talks to buy startup, people familiar say - Reuters</title><link>http://a/1</link>
<pubDate>{d1}</pubDate><source url="http://r">Reuters</source></item>
<item><title>Apple in talks to buy startup, people familiar say - CNBC</title><link>http://a/2</link>
<pubDate>{d1}</pubDate><source url="http://c">CNBC</source></item>
<item><title>Apple denies report it is in talks to buy chipmaker</title><link>http://a/3</link>
<pubDate>{d1}</pubDate><source url="http://b">Bloomberg</source></item>
<item><title>Apple reportedly weighing chipmaker purchase</title><link>http://a/4</link>
<pubDate>{d2}</pubDate><source url="http://x">Some Blog</source></item>
<item><title>Apple beats quarterly earnings estimates</title><link>http://a/5</link>
<pubDate>{d1}</pubDate><source url="http://r">Reuters</source></item>
<item><title>Analysts raise Apple price target after results</title><link>http://a/6</link>
<pubDate>{d1}</pubDate><source url="http://m">MarketWatch</source></item>
<item><title>Rumor: Apple exploring TV launch</title><link>http://a/7</link>
<pubDate>{d2}</pubDate><source url="http://z">Tiny Site</source></item>
</channel></rss>"""


def test_radar_de_noticias_e_rumores(tmp_path):
    agora = dt.datetime.now(dt.timezone.utc)
    d1 = agora.strftime("%a, %d %b %Y %H:%M:%S GMT")
    d2 = (agora - dt.timedelta(days=10)).strftime("%a, %d %b %Y %H:%M:%S GMT")
    xml = RSS.format(d1=d1, d2=d2)
    urls = []

    def baixar(url):
        urls.append(url)
        return xml if "Apple" in url or "AAPL" in url else "<rss><channel></channel></rss>"
    assert nt.main(["--empresa", "Apple", "--ticker", "AAPL", "--idiomas", "en", "--saida", str(tmp_path)],
                   baixar=baixar) == 0
    assert any("Federal%20Reserve" in u for u in urls)            # contexto mundial também é buscado
    itens = json.loads((tmp_path / "noticias.json").read_text(encoding="utf-8"))
    por_link = {i["link"]: i for i in itens}
    assert "http://a/2" not in por_link                            # duplicada (CNBC) foi unida à da Reuters
    assert por_link["http://a/1"]["outras_fontes"] == ["CNBC"]
    assert por_link["http://a/3"]["nivel_rumor"] == "desmentido"
    assert por_link["http://a/4"]["nivel_rumor"] == "desmentido"   # mesma história, desmentida em outra manchete
    assert por_link["http://a/7"]["nivel_rumor"] == "improvavel"
    assert "resultado" in por_link["http://a/5"]["tipos"] and "rumor" not in por_link["http://a/5"]["tipos"]
    assert "expectativa" in por_link["http://a/6"]["tipos"]
    md = (tmp_path / "noticias.md").read_text(encoding="utf-8")
    assert "CHANCE QUASE NULA" in md and "rumor mexe no preço mesmo sendo falso" in md


def test_radar_integra_noticias_do_composio(tmp_path):
    agora = dt.datetime.now(dt.timezone.utc)
    resposta = {"successful": True, "data": {"feed": [         # Alpha Vantage NEWS_SENTIMENT via Composio
        {"title": "Apple beats quarterly earnings estimates", "url": "http://c/1", "source": "Benzinga",
         "time_published": agora.strftime("%Y%m%dT%H%M%S"), "overall_sentiment_label": "Bullish"},
        {"title": "Apple reportedly in talks to buy streaming startup", "url": "http://c/2", "source": "Reuters",
         "time_published": (agora - dt.timedelta(days=2)).strftime("%Y%m%dT%H%M%S")},
        {"title": "", "url": "http://c/3"},                       # sem título: ignorado
    ]}}
    arq = tmp_path / "composio.json"
    arq.write_text(json.dumps(resposta), encoding="utf-8")
    assert nt.main(["--empresa", "Apple", "--idiomas", "en", "--sem-global", "--extras", str(arq),
                    "--extras", str(tmp_path / "nao_existe.json"), "--saida", str(tmp_path)],
                   baixar=lambda url: "<rss><channel></channel></rss>") == 0
    por_link = {i["link"]: i for i in json.loads((tmp_path / "noticias.json").read_text(encoding="utf-8"))}
    assert set(por_link) == {"http://c/1", "http://c/2"}
    c1, c2 = por_link["http://c/1"], por_link["http://c/2"]
    assert c1["origem"] == "composio" and c1["sentimento"] == "Bullish" and "resultado" in c1["tipos"]
    assert c1["data"].startswith(agora.strftime("%Y-%m-%d"))
    assert "rumor" in c2["tipos"] and c2["nivel_rumor"] == "provavel"   # Reuters = fonte de referência
    md = (tmp_path / "noticias.md").read_text(encoding="utf-8")
    assert "via Composio" in md and "sentimento: Bullish" in md
    assert "extras" in md and "nao_existe.json" in md                   # arquivo ausente vira falha, não erro


def test_ler_extras_aceita_lista_simples():
    itens = nt.ler_extras([{"titulo": "Petrobras anuncia dividendos", "fonte": "Valor", "escopo": "brasil",
                            "data": "2026-11-07T10:00:00Z"}, "lixo"], origem="outra")
    assert len(itens) == 1 and itens[0]["escopo"] == "brasil" and itens[0]["origem"] == "outra"
    assert itens[0]["data"] == "2026-11-07T10:00:00+00:00"


# ---------------------------------------------------------------- várias fontes
import provedores as pv  # noqa: E402
import fontes as fx  # noqa: E402


@pytest.mark.parametrize("t,stooq,av", [
    ("AAPL", "aapl.us", "AAPL"), ("BRK-B", "brk.b.us", "BRK.B"), ("PETR4", None, "PETR4.SAO"),
    ("HSBA.L", "hsba.uk", "HSBA.LON"), ("7203.T", "7203.jp", None), ("0700.HK", "700.hk", None),
    ("^GSPC", "^spx", None), ("USDBRL=X", None, None),
])
def test_simbolos_das_fontes(t, stooq, av):
    assert pv.simbolo_stooq(t) == stooq
    assert pv.simbolo_alphavantage(t) == av


def test_cadeia_passa_para_a_proxima_fonte(monkeypatch):
    idx = pd.bdate_range("2025-01-01", periods=10)
    def falha(s, a):
        raise fx.FonteIndisponivel("fora do ar")
    monkeypatch.setitem(pv.PROVEDORES, "yahoo", falha)
    monkeypatch.setitem(pv.PROVEDORES, "stooq", lambda s, a: pd.Series(range(1, 11), index=idx, dtype=float))
    monkeypatch.delenv("ANALISE_FONTES_PRECO", raising=False)
    df, origem = pv.precos(["AAPL", "MSFT"], 1)
    assert origem == {"AAPL": "stooq", "MSFT": "stooq"} and df["AAPL"].iloc[-1] == 10
    monkeypatch.setenv("ANALISE_FONTES_PRECO", "yahoo")      # só Yahoo: tudo falha
    with pytest.raises(fx.FonteIndisponivel):
        pv.precos(["AAPL"], 1)


def test_conferencia_cruzada_aponta_divergencia(monkeypatch):
    idx = pd.bdate_range("2025-01-01", periods=5)
    monkeypatch.delenv("ANALISE_FONTES_PRECO", raising=False)
    monkeypatch.setitem(pv.PROVEDORES, "yahoo", lambda s, a: pd.Series([10.0] * 5, index=idx))
    monkeypatch.setitem(pv.PROVEDORES, "stooq", lambda s, a: pd.Series([10.1] * 5, index=idx))
    ok = pv.conferir_ultimo_preco("AAPL")
    assert ok["conferido"] and ok["fonte_2"] == "stooq"
    monkeypatch.setitem(pv.PROVEDORES, "stooq", lambda s, a: pd.Series([12.0] * 5, index=idx))
    ruim = pv.conferir_ultimo_preco("AAPL")
    assert not ruim["conferido"] and "DIVERGÊNCIA" in ruim["obs"]


def test_fred_e_reserva_do_painel(monkeypatch):
    csv = "observation_date,DGS10\n2025-01-02,4.50\n2025-01-03,.\n2025-01-06,4.60\n"
    class R:
        text = csv
    monkeypatch.setattr(fx, "_get", lambda *a, **k: R())
    s = pv.fred("DGS10")
    assert list(s.values) == [4.5, 4.6]                     # "." (sem dado) é descartado
    monkeypatch.setattr(fx, "_precos_yahoo", lambda simbolos, anos: (None, list(simbolos)))
    pg = fx.painel_global()
    linha = pg[pg["simbolo"] == "^TNX"].iloc[0]
    assert linha["ultimo"] == 4.6 and linha["fonte"].startswith("FRED")
