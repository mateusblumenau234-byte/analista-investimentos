"""Estado persistente do app: patrimônio ao longo do tempo, alertas e eventos do monitor.

Banco SQLite em <dados>/estado.db (a mesma pasta da memória do investidor, fora de qualquer repositório).
A carteira em si continua em carteira.csv (memoria.py); aqui fica o que muda com o tempo.
"""
from __future__ import annotations

import datetime as dt
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import memoria as mem  # noqa: E402

TIPOS_ALERTA = {
    "preco_abaixo": "preço fecha abaixo de {valor}",
    "preco_acima": "preço fecha acima de {valor}",
    "queda_dia": "queda de {valor}% ou mais desde a última leitura",
    "alta_dia": "alta de {valor}% ou mais desde a última leitura",
    "rumor": "rumor classificado como provável ou real (valor ignorado)",
}

ESQUEMA = """
CREATE TABLE IF NOT EXISTS snapshots (data TEXT, ativo TEXT, cotas REAL, preco REAL, moeda TEXT, valor REAL,
                                      fonte TEXT, PRIMARY KEY (data, ativo));
CREATE TABLE IF NOT EXISTS alertas (id INTEGER PRIMARY KEY AUTOINCREMENT, ativo TEXT, tipo TEXT, valor REAL,
                                    nota TEXT, criado TEXT, disparado_em TEXT);
CREATE TABLE IF NOT EXISTS eventos (id INTEGER PRIMARY KEY AUTOINCREMENT, quando TEXT, tipo TEXT, ativo TEXT,
                                    texto TEXT, link TEXT);
"""


def conectar() -> sqlite3.Connection:
    mem.DADOS.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(mem.DADOS / "estado.db")
    c.row_factory = sqlite3.Row
    c.executescript(ESQUEMA)
    return c


def registrar_snapshot(data: str, ativo: str, cotas: float, preco: float, moeda: str | None, fonte: str) -> None:
    with conectar() as c:
        c.execute("INSERT OR REPLACE INTO snapshots VALUES (?,?,?,?,?,?,?)",
                  (data, ativo.upper(), cotas, preco, moeda, cotas * preco, fonte))


def ultimo_preco(ativo: str, antes_de: str) -> float | None:
    with conectar() as c:
        r = c.execute("SELECT preco FROM snapshots WHERE ativo=? AND data<? ORDER BY data DESC LIMIT 1",
                      (ativo.upper(), antes_de)).fetchone()
    return r["preco"] if r else None


def serie_patrimonio() -> list[dict]:
    """Valor total por data (soma das posições cotadas naquele dia), em ordem cronológica."""
    with conectar() as c:
        rows = c.execute("SELECT data, SUM(valor) AS valor, COUNT(*) AS ativos FROM snapshots "
                         "GROUP BY data ORDER BY data").fetchall()
    return [dict(r) for r in rows]


def snapshots_do_dia(data: str | None = None) -> list[dict]:
    with conectar() as c:
        data = data or (c.execute("SELECT MAX(data) AS d FROM snapshots").fetchone()["d"])
        rows = c.execute("SELECT * FROM snapshots WHERE data=? ORDER BY valor DESC", (data,)).fetchall()
    return [dict(r) for r in rows]


def criar_alerta(ativo: str, tipo: str, valor: float | None = None, nota: str = "") -> int:
    if tipo not in TIPOS_ALERTA:
        raise ValueError(f"tipo inválido: {tipo}; use um de {', '.join(TIPOS_ALERTA)}")
    if tipo != "rumor" and valor is None:
        raise ValueError(f"o alerta {tipo} precisa de valor")
    with conectar() as c:
        cur = c.execute("INSERT INTO alertas (ativo, tipo, valor, nota, criado) VALUES (?,?,?,?,?)",
                        (ativo.upper(), tipo, valor, nota, dt.datetime.now().isoformat(timespec="seconds")))
        return int(cur.lastrowid)


def listar_alertas(so_ativos: bool = True) -> list[dict]:
    q = "SELECT * FROM alertas" + (" WHERE disparado_em IS NULL" if so_ativos else "") + " ORDER BY ativo, id"
    with conectar() as c:
        return [dict(r) for r in c.execute(q).fetchall()]


def remover_alerta(id_: int) -> bool:
    with conectar() as c:
        return c.execute("DELETE FROM alertas WHERE id=?", (id_,)).rowcount > 0


def descrever(a: dict) -> str:
    v = a.get("valor")
    return f"{a['ativo']}: " + TIPOS_ALERTA[a["tipo"]].format(valor=v if v is None else f"{v:g}")


def avaliar_alertas(leituras: dict[str, dict], rumores: dict[str, list[dict]] | None = None) -> list[dict]:
    """Confere os alertas ativos contra as leituras do dia e marca os que dispararam (disparam uma vez só).

    leituras: {ativo: {"preco": float, "variacao": float | None}}  (variacao em fração, ex.: -0.05)
    rumores:  {ativo: [itens do radar com nivel_rumor]}
    """
    rumores = rumores or {}
    disparados = []
    for a in listar_alertas():
        ler = leituras.get(a["ativo"], {})
        p, var, v = ler.get("preco"), ler.get("variacao"), a["valor"]
        motivo = None
        if a["tipo"] == "preco_abaixo" and p is not None and p < v:
            motivo = f"preço {p:g} abaixo de {v:g}"
        elif a["tipo"] == "preco_acima" and p is not None and p > v:
            motivo = f"preço {p:g} acima de {v:g}"
        elif a["tipo"] == "queda_dia" and var is not None and var <= -abs(v) / 100:
            motivo = f"queda de {var * 100:.1f}%"
        elif a["tipo"] == "alta_dia" and var is not None and var >= abs(v) / 100:
            motivo = f"alta de {var * 100:.1f}%"
        elif a["tipo"] == "rumor":
            fortes = [r for r in rumores.get(a["ativo"], []) if r.get("nivel_rumor") in ("provavel", "real")]
            if fortes:
                motivo = f"rumor {fortes[0]['nivel_rumor']}: {fortes[0]['titulo']}"
        if motivo:
            agora = dt.datetime.now().isoformat(timespec="seconds")
            with conectar() as c:
                c.execute("UPDATE alertas SET disparado_em=? WHERE id=?", (agora, a["id"]))
            registrar_evento("alerta", a["ativo"], f"{descrever(a)} -> {motivo}")
            disparados.append({**a, "motivo": motivo, "disparado_em": agora})
    return disparados


def registrar_evento(tipo: str, ativo: str | None, texto: str, link: str = "") -> None:
    with conectar() as c:
        c.execute("INSERT INTO eventos (quando, tipo, ativo, texto, link) VALUES (?,?,?,?,?)",
                  (dt.datetime.now().isoformat(timespec="seconds"), tipo, (ativo or "").upper(), texto, link))


def eventos_recentes(limite: int = 30) -> list[dict]:
    with conectar() as c:
        return [dict(r) for r in c.execute("SELECT * FROM eventos ORDER BY id DESC LIMIT ?", (limite,)).fetchall()]
