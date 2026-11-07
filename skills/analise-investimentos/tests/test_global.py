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
    itens = json.loads((tmp_path / "noticias.json").read_text())
    por_link = {i["link"]: i for i in itens}
    assert "http://a/2" not in por_link                            # duplicada (CNBC) foi unida à da Reuters
    assert por_link["http://a/1"]["outras_fontes"] == ["CNBC"]
    assert por_link["http://a/3"]["nivel_rumor"] == "desmentido"
    assert por_link["http://a/4"]["nivel_rumor"] == "desmentido"   # mesma história, desmentida em outra manchete
    assert por_link["http://a/7"]["nivel_rumor"] == "improvavel"
    assert "resultado" in por_link["http://a/5"]["tipos"] and "rumor" not in por_link["http://a/5"]["tipos"]
    assert "expectativa" in por_link["http://a/6"]["tipos"]
    md = (tmp_path / "noticias.md").read_text()
    assert "CHANCE QUASE NULA" in md and "rumor mexe no preço mesmo sendo falso" in md
