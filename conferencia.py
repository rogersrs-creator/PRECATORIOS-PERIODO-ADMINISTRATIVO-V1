"""
Conferência dos casos certificados (União: não tributários X e tributários T).

Refaz cada caso de dados/CASOS-CERTIFICADOS.csv com os índices e o motor atuais e compara o
total com o valor certificado. A base nem sempre separa principal, juros e SELIC como o app
(até a proposta 2026 a SELIC vem somada aos juros), por isso a comparação é pelo total.

Uso pela linha de comando:  python conferencia.py
"""
from __future__ import annotations

import csv
import os

from fontes import PASTA_DADOS, para_numero
from motores import Entrada, calcular

TOLERANCIA = 1.00  # R$; os centavos que sobram vêm do IPCA-E encadeado (ver README, arredondamento)
ARQUIVO_CASOS = os.path.join(PASTA_DADOS, "CASOS-CERTIFICADOS.csv")
ARQUIVO_TRIBUTARIOS = os.path.join(PASTA_DADOS, "CASOS-TRIBUTARIOS.csv")  # União, tributário (T01 a T07)


def ler_casos() -> list[dict]:
    with open(ARQUIVO_CASOS, encoding="utf-8-sig") as f:
        casos = list(csv.DictReader(f, delimiter=";"))
    if os.path.exists(ARQUIVO_TRIBUTARIOS):
        with open(ARQUIVO_TRIBUTARIOS, encoding="utf-8-sig") as f:
            for c in csv.DictReader(f, delimiter=";"):
                c["NATUREZA"] = "Tributário"
                c["OBS_JUROS"] = c["OBS_JUROS_NA_BASE"] = "Não se aplica (tributário)"
                casos.append(c)
    return casos


def conferir(caso: dict, bases, df_graca) -> dict:
    m, a = caso["DATA_BASE"].split("/")
    e = Entrada("Nacional", caso.get("NATUREZA", "Não Tributário"), int(caso["PROPOSTA"]), (int(a), int(m)),
                para_numero(caso["PRINCIPAL"]), para_numero(caso["JUROS"]), caso["OBS_JUROS"],
                para_numero(caso.get("SELIC") or 0))
    r = calcular(e, bases, df_graca)
    cert = sum(para_numero(caso[c]) for c in ("CERT_PRINCIPAL", "CERT_JUROS", "CERT_SELIC"))
    dif = round(r.total, 2) - round(cert, 2)
    pos = r.posicao_proposta()
    selic_cert = para_numero(caso["CERT_SELIC"])
    return dict(caso=caso["CASO"], natureza=e.natureza, proposta=e.ano_proposta, data_base=caso["DATA_BASE"],
                obs_juros=caso["OBS_JUROS"], obs_na_base=caso["OBS_JUROS_NA_BASE"],
                calculado=round(r.total, 2), certificado=round(cert, 2), diferenca=round(dif, 2),
                selic_proposta=round(pos["SELIC-PROPOSTA"], 2), selic_certificada=round(selic_cert, 2),
                situacao="Fecha" if abs(dif) <= TOLERANCIA else "NÃO FECHA", resultado=r)


def conferir_todos(bases, df_graca) -> list[dict]:
    return [conferir(c, bases, df_graca) for c in ler_casos()]


if __name__ == "__main__":
    from fontes import carregar_todas
    from motores import Bases
    import config

    dfs, graca, origens = carregar_todas(config.urls_locais())
    bases = Bases.de_dataframes(dfs)
    linhas = conferir_todos(bases, graca)
    print(f"{'Caso':5} {'Prop':5} {'Data-base':9} {'OBS-JUROS':12} {'Calculado':>14} {'Certificado':>14} "
          f"{'Dif':>8}  Situação")
    for x in linhas:
        print(f"{x['caso']:5} {x['proposta']:<5} {x['data_base']:9} {x['obs_juros']:12} {x['calculado']:>14,.2f} "
              f"{x['certificado']:>14,.2f} {x['diferenca']:>8,.2f}  {x['situacao']}")
    ok = sum(x["situacao"] == "Fecha" for x in linhas)
    print(f"\n{ok} de {len(linhas)} casos fecham (tolerância R$ {TOLERANCIA:.2f}).")
