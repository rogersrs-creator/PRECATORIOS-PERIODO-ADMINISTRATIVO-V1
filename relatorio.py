"""Relatório do cálculo do período administrativo: tabela para a tela e arquivo Excel."""
from __future__ import annotations

import io

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from motores.base import Resultado, rotulo

COLUNAS = ["Mês da variação", "Trecho", "Regra do mês", "Correção %", "Juros do mês %", "SELIC do mês %",
           "Fator de correção", "Juros acumulados %", "SELIC acumulada %", "Principal", "Juros", "SELIC",
           "Total"]


def tabela(res: Resultado) -> pd.DataFrame:
    return pd.DataFrame([[l.mes, l.trecho, l.regra, l.correcao_pct, l.juros_pct, l.selic_pct, l.fator,
                          l.juros_acum_pct, l.selic_acum_pct, l.principal, l.juros, l.selic, l.total]
                         for l in res.linhas], columns=COLUNAS)


def brl(v: float) -> str:
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def gerar_excel(res: Resultado) -> bytes:
    e = res.entrada
    wb = Workbook()
    cab = Font(bold=True, color="FFFFFF")
    fundo = PatternFill("solid", fgColor="1E3A34")
    dinheiro, pct, fator = "#,##0.00", "0.0000", "0.000000000"

    ws = wb.active
    ws.title = "Resumo"
    ws["A1"] = "CÁLCULO DO PERÍODO ADMINISTRATIVO · DATA-BASE DO PROCESSO → DATA-BASE DA PROPOSTA"
    ws["A1"].font = Font(bold=True, size=13)
    itens = [
        ("Esfera", e.esfera), ("Natureza", e.natureza), ("Proposta", e.ano_proposta),
        ("Data-base do processo", rotulo(e.data_base)),
        ("Data final (data-base da proposta)", f"{rotulo(res.data_final)} · {res.origem_data_final}"),
        ("OBS-JUROS", e.obs_juros),
        ("Principal na data-base", e.principal), ("Juros na data-base", e.juros),
        ("SELIC na data-base", float(e.selic or 0)),
        (None, None),
        (f"Valores na proposta {e.ano_proposta}",
         "tributário: SELIC somada aos juros, principal sem correção" if e.natureza == "Tributário" else
         "SELIC em campo próprio" if e.ano_proposta >= 2027 else "até 2026 não há campo Selic: SELIC somada aos juros"),
        *[(k, float(v)) for k, v in res.posicao_proposta().items()
          if e.ano_proposta >= 2027 or k != "SELIC-PROPOSTA"],
        *([("   dos quais SELIC (12/2021 em diante)", res.selic)] if e.ano_proposta < 2027 and res.selic else []),
        *([("   dos quais SELIC do período (tributário)", round(res.juros - e.juros - float(e.selic or 0), 2))]
          if e.natureza == "Tributário" else []),
        (None, None),
        ("Situação", "PARCIAL: faltam índices" if res.parcial else "Completo"),
    ]
    r = 3
    for k, v in itens:
        if k:
            ws.cell(r, 1, k).font = Font(bold=True)
            c = ws.cell(r, 3, v)
            if isinstance(v, float):
                c.number_format = dinheiro
        r += 1
    r += 1
    ws.cell(r, 1, "Trechos").font = Font(bold=True)
    r += 1
    for i, h in enumerate(["Trecho", "De", "Até", "Resumo"], 1):
        x = ws.cell(r, i, h)
        x.font, x.fill = cab, fundo
    for t in res.trechos:
        r += 1
        for i, k in enumerate(["trecho", "de", "ate", "descricao"], 1):
            ws.cell(r, i, t[k])
    if res.avisos:
        r += 2
        ws.cell(r, 1, "Avisos").font = Font(bold=True)
        for a in res.avisos:
            r += 1
            ws.cell(r, 1, a)
    r += 2
    ws.cell(r, 1, ("Centavos: SELIC arredondada até a proposta 2026 e truncada desde a 2027 (casos T01 a T07). "
                   if e.natureza == "Tributário" else "Centavos: valores truncados ao fim do cálculo (casos X). ")
            + "A memória mês a mês está na aba Memoria.")
    for i, w in enumerate([34, 12, 40, 70], 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    m = wb.create_sheet("Memoria")
    for i, h in enumerate(COLUNAS, 1):
        x = m.cell(1, i, h)
        x.font, x.fill = cab, fundo
        x.alignment = Alignment(wrap_text=True, vertical="center")
    m.row_dimensions[1].height = 36
    formatos = [None, None, None, pct, pct, pct, fator, pct, pct, dinheiro, dinheiro, dinheiro, dinheiro]
    for ri, linha in enumerate(tabela(res).itertuples(index=False), 2):
        for ci, (v, fmt) in enumerate(zip(linha, formatos), 1):
            if isinstance(v, float) and pd.isna(v):
                v = None
            c = m.cell(ri, ci, v)
            if fmt:
                c.number_format = fmt
    for i, w in enumerate([18, 24, 62, 11, 11, 11, 14, 12, 12, 15, 15, 15, 15], 1):
        m.column_dimensions[get_column_letter(i)].width = w
    m.freeze_panes = "B2"

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
