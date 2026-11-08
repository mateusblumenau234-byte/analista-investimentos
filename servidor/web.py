#!/usr/bin/env python3
"""Homebroker local: cotações, gráfico, carteira, notícias e mundo num só painel, no navegador.

Uso:  python servidor/web.py [--porta 8765]      ->  http://127.0.0.1:8765
Também sobe pela ferramenta `homebroker` do servidor MCP. Só escuta em 127.0.0.1 e só lê dados:
operações e alertas continuam sendo feitos pelo Claude, com a confirmação do investidor.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "skills" / "analise-investimentos" / "scripts"))
import estado as st  # noqa: E402
import fontes as fx  # noqa: E402
import memoria as mem  # noqa: E402
import mercados as mk  # noqa: E402

WEB = Path(__file__).resolve().parent / "web"
RELATORIOS = Path(__import__("os").environ.get("ANALISE_RELATORIOS", mem.DADOS.parent / "relatorios"))
FAIXAS = {"1d": ("1d", "5m"), "5d": ("5d", "30m"), "1m": ("1mo", "1d"), "6m": ("6mo", "1d"),
          "1a": ("1y", "1d"), "5a": ("5y", "1wk")}
MUNDO = ["^BVSP", "^GSPC", "^IXIC", "^STOXX50E", "^N225", "^HSI", "USDBRL=X", "EURUSD=X", "DX-Y.NYB",
         "^TNX", "^VIX", "BZ=F", "GC=F", "HG=F", "BTC-USD"]
_cache: dict[str, tuple[float, object]] = {}
_pool = ThreadPoolExecutor(4)   # o Yahoo limita rajadas (HTTP 429)


def cache(chave: str, ttl: float, fn):
    t, v = _cache.get(chave, (0.0, None))
    if time.time() - t < ttl:
        return v
    v = fn()
    _cache[chave] = (time.time(), v)
    return v


def _chart(t: str, faixa: str) -> dict:
    rng, itv = FAIXAS[faixa]
    js = fx._get(fx.YAHOO_URL.format(simbolo=mk.simbolo_yahoo(t)), {"range": rng, "interval": itv},
                 tentativas=2, timeout=12).json()["chart"]["result"][0]
    return js


def cotacao(t: str) -> dict:
    """Preço, variação no dia, moeda e horário (Yahoo, ~15 min de atraso)."""
    def busca():
        try:
            m = _chart(t, "1d")["meta"]
            p, ant = m.get("regularMarketPrice"), m.get("chartPreviousClose") or m.get("previousClose")
            return {"t": t, "p": p, "v": (p / ant - 1) if p and ant else None, "m": m.get("currency"),
                    "h": m.get("regularMarketTime"), "n": m.get("shortName") or m.get("longName") or t,
                    "max": m.get("regularMarketDayHigh"), "min": m.get("regularMarketDayLow"),
                    "max52": m.get("fiftyTwoWeekHigh"), "min52": m.get("fiftyTwoWeekLow")}
        except Exception as e:  # noqa: BLE001
            try:
                return _reserva(t)
            except Exception:  # noqa: BLE001
                return {"t": t, "p": None, "erro": type(e).__name__}
    return cache(f"q:{t}", 60, busca)


def _reserva(t: str) -> dict:
    """Último fechamento por outra fonte quando o Yahoo recusa: FRED para o painel mundial, cadeia de
    provedores (Stooq, Alpha Vantage, brapi, B3) para ativos. Índices e câmbio sem FRED ficam sem cotação,
    para não mostrar o preço de um ETF no lugar do índice."""
    import provedores as pv
    if t in pv.FRED_PAINEL:
        s, fonte = pv.fred(pv.FRED_PAINEL[t][0], 1), "FRED"
    elif t.startswith("^") or "=" in t:
        raise fx.FonteIndisponivel(t)
    else:
        s, fonte, _ = pv.serie(t, 1, pular={"yahoo"})
    s = s.dropna()
    return {"t": t, "p": float(s.iloc[-1]), "v": float(s.iloc[-1] / s.iloc[-2] - 1) if len(s) > 1 else None,
            "n": t, "f": fonte, "d": str(s.index[-1].date())}


def cotacoes(ts: list[str]) -> list[dict]:
    return list(_pool.map(cotacao, ts))


def historico(t: str, faixa: str) -> dict:
    def busca():
        try:
            js = _chart(t, faixa)
            fech = js["indicators"]["quote"][0]["close"]
            pts = [[ts, round(c, 4)] for ts, c in zip(js.get("timestamp") or [], fech) if c is not None]
            return {"t": t, "f": faixa, "pts": pts}
        except Exception:  # noqa: BLE001
            if faixa in ("1d", "5d"):
                raise
            import provedores as pv   # reserva diária pela cadeia de fontes
            dias = {"1m": 31, "6m": 183, "1a": 366, "5a": 1830}[faixa]
            s, fonte, _ = pv.serie(t, max(1, dias // 365 + 1))
            s = s[s.index >= s.index.max() - __import__("pandas").Timedelta(days=dias)]
            return {"t": t, "f": faixa, "fonte": fonte,
                    "pts": [[int(i.timestamp()), round(float(v), 4)] for i, v in s.items()]}
    return cache(f"h:{t}:{faixa}", 60 if faixa in ("1d", "5d") else 900, busca)


def carteira() -> dict:
    linhas, data = mem.ler_carteira()
    tks = [r["ativo"] for r in linhas if r.get("cotas_num") and not any(s in r.get("classe", "").lower()
                                                                        for s in mem.SEM_COTACAO)]
    q = {c["t"]: c for c in cotacoes(tks)}
    pos = []
    for r in linhas:
        c = q.get(r["ativo"], {})
        pos.append({"t": r["ativo"], "classe": r.get("classe"), "q": r["cotas_num"], "pm": r["preco_medio_num"],
                    "p": c.get("p"), "v": c.get("v"), "m": c.get("m"), "status": r.get("status")})
    return {"data": data, "pos": pos, "patrimonio": st.serie_patrimonio(),
            "alertas": [{"id": a["id"], "txt": st.descrever(a)} for a in st.listar_alertas()],
            "analises": mem.ler_historico()[-8:]}


def noticias(t: str, empresa: str | None) -> list[dict]:
    def busca():
        import noticias as nt
        import tempfile
        pasta = Path(tempfile.mkdtemp(prefix="hb_"))
        idi = "pt,en" if mk.eh_b3(t) else "en,pt"
        nt.main(["--empresa", empresa or t, "--ticker", t, "--sem-global", "--dias", "7", "--idiomas", idi,
                 "--saida", str(pasta)])
        itens = json.loads((pasta / "noticias.json").read_text(encoding="utf-8"))
        return [{k: i.get(k) for k in ("titulo", "link", "fonte", "data", "tipos", "nivel_rumor", "pontuacao")}
                for i in itens[:25]]
    return cache(f"n:{t}", 900, busca)


def pasta_analise(t: str, criar: bool = False) -> Path:
    """Pasta da análise de hoje (a mesma que analisar.py usa)."""
    import datetime as dt
    p = RELATORIOS / f"{t.upper()}_{dt.date.today():%Y-%m-%d}"
    if criar:
        p.mkdir(parents=True, exist_ok=True)
    return p


def _json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def analise(t: str) -> dict | None:
    """Estado da análise mais recente do ativo, lido dos arquivos que cada etapa grava (sem custo extra)."""
    pastas = sorted(RELATORIOS.glob(f"{t.upper()}_*"), key=lambda x: x.name)
    if not pastas:
        return None
    p = pastas[-1]
    d = _json(p / "dados.json") or {}
    m, est, ic = d.get("multiplos") or {}, d.get("estatisticas_ativo") or {}, d.get("indicadores_complementares") or {}
    pareceres = {x.stem.split("_", 1)[1]: _json(x) for x in p.glob("parecer_*.json")}
    notas = []
    if (p / "notas.jsonl").exists():
        notas = [json.loads(ln) for ln in (p / "notas.jsonl").read_text(encoding="utf-8").splitlines() if ln.strip()]
    rel = p / "relatorio.html"
    return {
        "pasta": p.name, "inicio": (_json(p / "inicio.json") or {}).get("inicio"),
        "etapas": {"coleta": (p / "relatorio_quantitativo.md").exists(), "exploracao": (p / "exploracao.md").exists(),
                   "noticias": (p / "noticias.md").exists(), "conselho": len(pareceres),
                   "nota": (p / "nota.json").exists(), "relatorio": rel.exists()},
        "metricas": {"preco": m.get("preco"), "p_l": m.get("p_l_ltm"), "p_vp": m.get("p_vp"),
                     "dy": m.get("dividend_yield_caixa"), "valor_mercado": m.get("valor_mercado"),
                     "vol": est.get("volatilidade_anualizada"), "ret": est.get("retorno_anualizado"),
                     "graham": ic.get("numero_graham"), "bazin": ic.get("preco_teto_bazin_6pct"),
                     "empresa": (d.get("empresa") or {}).get("nome")},
        "lacunas": (d.get("lacunas") or [])[:6],
        "conselho": {k: {c: v.get(c) for c in ("nota", "conviccao", "veredito")} for k, v in pareceres.items() if v},
        "nota": _json(p / "nota.json"), "notas": notas[-30:],
        "relatorio": f"/relatorios/{p.name}/relatorio.html" if rel.exists() else None,
        "fim": rel.stat().st_mtime * 1000 if rel.exists() else None}


def anotar(t: str, texto: str) -> None:
    import datetime as dt
    with (pasta_analise(t, criar=True) / "notas.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps({"h": dt.datetime.now().strftime("%H:%M:%S"), "txt": texto}, ensure_ascii=False) + "\n")


def abrir_analise(t: str) -> str:
    import datetime as dt
    p = pasta_analise(t, criar=True)
    if not (p / "inicio.json").exists():
        (p / "inicio.json").write_text(json.dumps({"ticker": t.upper(), "inicio": dt.datetime.now().isoformat()}),
                                       encoding="utf-8")
    return f"{iniciar()}/?t={t.upper()}&analise=1"


def mundo() -> list[dict]:
    return [{**c, "nome": mk.PAINEL_GLOBAL.get(c["t"], ("", c["t"]))[1]} for c in cotacoes(MUNDO)]


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # silencioso: stdout é do MCP
        pass

    def _envia(self, corpo: bytes, tipo: str, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", tipo)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(corpo)

    def do_GET(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        rotas = {"/api/carteira": lambda: carteira(),
                 "/api/cotacoes": lambda: cotacoes([x.strip().upper() for x in q.get("t", "").split(",") if x.strip()][:40]),
                 "/api/historico": lambda: historico(q["t"].upper(), q.get("f", "6m") if q.get("f") in FAIXAS else "6m"),
                 "/api/noticias": lambda: noticias(q["t"].upper(), q.get("e")),
                 "/api/mundo": lambda: mundo(),
                 "/api/analise": lambda: analise(q["t"])}
        if u.path in rotas:
            with _redirect_stdout():
                try:
                    corpo = json.dumps(rotas[u.path](), ensure_ascii=False, default=str, separators=(",", ":"))
                    return self._envia(corpo.encode(), "application/json; charset=utf-8")
                except Exception as e:  # noqa: BLE001
                    return self._envia(json.dumps({"erro": f"{type(e).__name__}: {e}"}).encode(),
                                       "application/json", 500)
        base, rel = (RELATORIOS, u.path[len("/relatorios/"):]) if u.path.startswith("/relatorios/") else (WEB, u.path.lstrip("/"))
        arq = (base / (rel or "index.html")).resolve()
        if base.resolve() in arq.parents and arq.is_file():
            return self._envia(arq.read_bytes(), mimetypes.guess_type(arq.name)[0] or "application/octet-stream")
        self._envia(b"nao encontrado", "text/plain", 404)


class _redirect_stdout:
    """Prints dos módulos vão para stderr (no MCP, stdout é o canal do protocolo)."""
    def __enter__(self):
        import contextlib
        self._c = contextlib.redirect_stdout(sys.stderr)
        self._c.__enter__()

    def __exit__(self, *a):
        self._c.__exit__(*a)


_servidor: ThreadingHTTPServer | None = None


def iniciar(porta: int = 8765) -> str:
    """Sobe o homebroker numa thread (uma vez por processo) e devolve o endereço."""
    global _servidor
    if _servidor is None:
        try:
            _servidor = ThreadingHTTPServer(("127.0.0.1", porta), Handler)
        except OSError:   # porta ocupada: outra sessão do Claude já serve o homebroker com os mesmos dados
            return f"http://127.0.0.1:{porta}"
        threading.Thread(target=_servidor.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{_servidor.server_address[1]}"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--porta", type=int, default=8765)
    url = iniciar(ap.parse_args().porta)
    print(url, flush=True)
    threading.Event().wait()
