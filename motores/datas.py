"""
Data final do período administrativo: a data-base dos cálculos da proposta.

1. Se o ano está na planilha GRACA (a mesma do app V6), vale a coluna
   DATA_BASE_INICIAL_CALCULOS.
2. Senão, vale a data-limite de apresentação do precatório (CF, art. 100, § 5º):
   - até a proposta 2022: 1º de julho do ano anterior (redação original e EC 62/2009);
   - propostas 2023 a 2026: 2 de abril do ano anterior (EC 114/2021), mês 04;
   - desde a proposta 2027: 1º de fevereiro do ano anterior (EC 136/2025).
As variações entram até o mês anterior à data final.
"""
from __future__ import annotations

import pandas as pd

from motores.base import Mes


def data_final_pela_cf(ano: int) -> Mes:
    if ano <= 2022:
        return (ano - 1, 7)
    if ano <= 2026:
        return (ano - 1, 4)
    return (ano - 1, 2)


def data_final(ano: int, df_graca: pd.DataFrame | None) -> tuple[Mes, str]:
    if df_graca is not None and len(df_graca):
        linha = df_graca[df_graca["ANO_PROPOSTA"] == ano]
        if len(linha):
            dt = linha["DATA_BASE_INICIAL_CALCULOS"].iloc[0]
            return (dt.year, dt.month), "planilha GRACA"
    return data_final_pela_cf(ano), "CF, art. 100, § 5º (ano fora da planilha GRACA)"
