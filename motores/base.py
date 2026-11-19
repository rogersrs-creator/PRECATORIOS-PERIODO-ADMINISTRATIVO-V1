"""
Peças comuns dos motores do período administrativo.

Convenção das planilhas de índices (a mesma do app V6): a linha do mês m traz a
variação do mês m-1. Ex.: na SELIC, a linha 02/2003 traz a taxa de 01/2003.
Nos motores e na memória de cálculo, cada linha é identificada pelo
**mês da variação** (o mês m-1), como na planilha de conferência dos casos.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

Mes = tuple[int, int]  # (ano, mês)


def proximo(k: Mes) -> Mes:
    a, m = k
    return (a + 1, 1) if m == 12 else (a, m + 1)


def anterior(k: Mes) -> Mes:
    a, m = k
    return (a - 1, 12) if m == 1 else (a, m - 1)


def meses(ini: Mes, fim: Mes) -> list[Mes]:
    """Meses de ini (inclusive) até fim (exclusive)."""
    out, k = [], ini
    while k < fim:
        out.append(k)
        k = proximo(k)
    return out


def rotulo(k: Mes) -> str:
    return f"{k[1]:02d}/{k[0]}"


class Serie:
    """Série mensal de variações (%), indexada pelo mês da variação."""

    def __init__(self, nome: str, df: pd.DataFrame):
        self.nome = nome
        self.var: dict[Mes, float] = {}
        for _, r in df.iterrows():
            linha = (r["data"].year, r["data"].month)
            v = r.get("variacao")
            if v is None or pd.isna(v):
                continue
            self.var[anterior(linha)] = float(v)
        # o mês-base da planilha (índice inicial) não tem variação própria
        primeira = (df["data"].iloc[0].year, df["data"].iloc[0].month) if len(df) else None
        if primeira:
            self.var.pop(anterior(primeira), None)
        self.ultimo: Mes | None = max(self.var) if self.var else None

    def __contains__(self, k: Mes) -> bool:
        return k in self.var

    def __getitem__(self, k: Mes) -> float:
        return self.var[k]


@dataclass
class Bases:
    ipcae: Serie      # IPCA-E sem TR (até 11/2021)
    poupanca: Serie   # juros da poupança (% a.m.)
    selic: Serie      # SELIC mensal (% a.m.)
    ipca: Serie       # IPCA (desde 09/2025)

    @classmethod
    def de_dataframes(cls, dfs: dict) -> "Bases":
        return cls(Serie("IPCA-E sem TR", dfs["IPCAE_SEM_TR"]),
                   Serie("Poupança", dfs["POUPANCA"]),
                   Serie("SELIC", dfs["SELIC"]),
                   Serie("IPCA", dfs["IPCA"]))


@dataclass
class Entrada:
    esfera: str
    natureza: str
    ano_proposta: int
    data_base: Mes
    principal: float
    juros: float
    obs_juros: str
    selic: float = 0.0   # SELIC já existente na data-base (só para data-base desde 12/2021)


@dataclass
class Linha:
    mes: str
    trecho: str
    regra: str
    correcao_pct: float | None
    juros_pct: float | None
    selic_pct: float | None
    fator: float
    juros_acum_pct: float
    selic_acum_pct: float
    principal: float
    juros: float
    selic: float

    @property
    def total(self) -> float:
        return self.principal + self.juros + self.selic


@dataclass
class Resultado:
    entrada: Entrada
    data_final: Mes
    origem_data_final: str
    linhas: list[Linha] = field(default_factory=list)
    trechos: list[dict] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    parcial: bool = False
    principal: float = 0.0
    juros: float = 0.0
    selic: float = 0.0

    @property
    def total(self) -> float:
        return self.principal + self.juros + self.selic

    def posicao_proposta(self) -> dict:
        """Valores como entram na base de propostas (colunas ...-PROPOSTA).

        Desde a proposta 2027 o campo SELIC é obrigatório e fica separado; até a 2026 a SELIC
        vem somada aos juros (como nos casos certificados)."""
        if self.entrada.ano_proposta >= 2027:
            return {"VALOR-PRINCIPAL-PROPOSTA": self.principal, "VALOR-JUROS-PROPOSTA": self.juros,
                    "SELIC-PROPOSTA": self.selic, "TOTAL-PROPOSTA": self.total}
        return {"VALOR-PRINCIPAL-PROPOSTA": self.principal, "VALOR-JUROS-PROPOSTA": self.juros + self.selic,
                "SELIC-PROPOSTA": 0.0, "TOTAL-PROPOSTA": self.total}


class Regra:
    """Interface de um regime de cálculo (esfera + natureza + faixa de propostas)."""
    nome = ""
    descricao = ""
    esfera = ""
    natureza = "Não Tributário"
    ano_ini = 0
    ano_fim = 9999
    disponivel = True

    def atende(self, ano: int) -> bool:
        return self.ano_ini <= ano <= self.ano_fim

    def calcular(self, entrada: Entrada, bases: Bases, data_final: Mes, origem: str) -> Resultado:
        raise NotImplementedError


class EmDesenvolvimento(Regra):
    disponivel = False

    def __init__(self, esfera: str, natureza: str, motivo: str):
        self.esfera = esfera
        self.natureza = natureza
        self.nome = f"{esfera} · {natureza}"
        self.descricao = motivo

    def calcular(self, *a, **k):
        raise NotImplementedError(self.descricao)
