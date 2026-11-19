"""
Registro de regimes do período administrativo (mesma lógica do app V6).

O app escolhe o motor por (esfera, natureza, ano da proposta). Para incluir um regime novo,
crie o módulo e acrescente-o à lista REGRAS da esfera (ou a tributario.REGRAS).
"""
from motores import nacional, subnacional, tributario
from motores.base import Bases, Entrada, Resultado  # noqa: F401
from motores.datas import data_final  # noqa: F401

ESFERAS = {
    "Nacional": nacional.REGRAS,
    "Subnacional": subnacional.REGRAS,
}
NATUREZAS = ["Não Tributário", "Tributário"]


def regra_para(esfera: str, ano: int, natureza: str = "Não Tributário"):
    if natureza == "Tributário":
        return tributario.REGRAS.get(esfera)
    for regra in ESFERAS.get(esfera, []):
        if not regra.disponivel or regra.atende(ano):
            return regra
    return None


def calcular(entrada: Entrada, bases: Bases, df_graca):
    regra = regra_para(entrada.esfera, entrada.ano_proposta, entrada.natureza)
    if regra is None:
        raise ValueError("Não há regime para essa combinação de esfera, natureza e proposta.")
    if not regra.disponivel:
        raise NotImplementedError(regra.descricao)
    fim, origem = data_final(entrada.ano_proposta, df_graca)
    return regra.calcular(entrada, bases, fim, origem)
