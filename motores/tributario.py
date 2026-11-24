"""
Precatórios de natureza TRIBUTÁRIA · União: da data-base do processo à data-base da proposta.

Regra deduzida dos 7 casos tributários homologados (T01 a T07, propostas 2023 a 2027), que fecham ao
centavo, e conferida nas normas da fase de requisitórios:

- SELIC simples (soma das taxas mensais, sem capitalização) SOMENTE sobre o valor principal, do mês da
  data-base (inclusive) até o mês anterior à data-base da proposta. Não há IPCA-E, IPCA, juros do título,
  poupança, 2% a.a. nem troca de regime em 12/2021 ou 09/2025: a mesma regra vale o período todo.
  Normas: EC 113/2021, art. 3º, § 2º, na redação da EC 136/2025 ("Nos processos de natureza tributária
  serão aplicados os mesmos critérios de atualização e remuneração da mora pelos quais a Fazenda Pública
  remunera seu crédito tributário"); Provimento CNJ 207/2025, art. 4º ("Os precatórios de natureza
  tributária devem ser atualizados monetariamente exclusivamente pela Taxa Selic"); Res. CJF 983/2026,
  art. 7º, caput (tributários e não tributários) e art. 8º, § 1º; Res. CJF 983/2026, art. 7º, § 1º e Res.
  CNJ 303/2019, art. 22 (juros de mora só nos não tributários).
- O principal não muda. Os juros informados (a SELIC já apurada no cálculo homologado) também não mudam
  e não recebem SELIC (sem capitalização: Res. CJF 983/2026, art. 7º, § 4º). A SELIC nova é somada aos
  juros, inclusive na proposta 2027 (nos casos T06 e T07 o campo SELIC-PROPOSTA é zero).
- Data-base desde 01/1996 (Lei 9.250/1995, art. 39, § 4º). SELIC de 01/1996 a 12/2002 em
  motores/selic_historica.py (BCB, SGS 4390); a partir de 01/2003, a planilha SELIC do V6. O Rogers
  confirmou (24/11/2026) que a regra é a mesma para os tributários antigos; o V6 também usa uma só regra
  tributária para todas as propostas.
- Centavos: até a proposta 2026 a SELIC apurada é ARREDONDADA (T03, T04 e T05 só fecham arredondando);
  desde a proposta 2027 é TRUNCADA (T06 só fecha truncando, como o X18 dos não tributários).
  Regra deduzida dos casos; aguarda confirmação do Rogers.
"""
from __future__ import annotations

from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

from motores.selic_historica import INICIO_SELIC_TRIBUTARIO, SELIC_1996_2002
from motores.base import Bases, EmDesenvolvimento, Entrada, Linha, Mes, Regra, Resultado, anterior, meses, rotulo

OBS_TRIBUTARIO = "Não se aplica (tributário)"
ANO_TRUNCA = 2027   # desde esta proposta os centavos são truncados (caso T06)


def centavos(v: float, ano_proposta: int) -> float:
    modo = ROUND_DOWN if ano_proposta >= ANO_TRUNCA else ROUND_HALF_UP
    return float(Decimal(repr(v)).quantize(Decimal("0.01"), rounding=modo))


class UniaoTributario(Regra):
    nome = "União · tributário"
    esfera = "Nacional"
    natureza = "Tributário"
    ano_ini = 2001
    ano_fim = 9999
    usa_obs_juros = False
    descricao = ("SELIC simples só sobre o principal, do mês da data-base ao mês anterior à data-base da "
                 "proposta, somada aos juros. Sem IPCA-E/IPCA, sem juros do título e sem troca de regime.")

    def calcular(self, e: Entrada, b: Bases, fim: Mes, origem: str) -> Resultado:
        res = Resultado(entrada=e, data_final=fim, origem_data_final=origem)
        db = e.data_base
        if db < INICIO_SELIC_TRIBUTARIO:
            raise ValueError(f"Data-base {rotulo(db)} anterior a 01/1996: a SELIC só vale para tributos federais "
                             "desde 01/1996 (Lei 9.250/1995, art. 39, § 4º); a regra anterior (UFIR) ainda não "
                             "foi definida para o aplicativo.")
        # Meses de 01/1996 a 12/2002 vêm da série do BCB (SGS 4390); depois, da planilha SELIC do V6.
        taxa = lambda k: b.selic[k] if k in b.selic else SELIC_1996_2002.get(k)  # noqa: E731
        if db >= fim:
            raise ValueError(f"A data-base ({rotulo(db)}) precisa ser anterior à data final da proposta "
                             f"{e.ano_proposta} ({rotulo(fim)}).")
        P0 = float(e.principal)
        J0 = float(e.juros) + float(e.selic or 0)   # a SELIC já apurada fica nos juros e não recebe SELIC
        if e.selic:
            res.avisos.append(f"Tributário: a Selic informada ({e.selic:,.2f}) foi somada aos juros e não "
                              "recebe SELIC de novo.")
        res.linhas.append(Linha(rotulo(db) + " (data-base)", "Data-base", "Valores da data-base",
                                None, None, None, 1.0, 0.0, 0.0, P0, J0, 0.0))
        s = 0.0
        ultimo = None
        for k in meses(db, fim):
            if taxa(k) is None:
                res.parcial = True
                res.avisos.append(
                    f"Cálculo PARCIAL: a planilha SELIC não tem a taxa de {rotulo(k)} (última: "
                    f"{rotulo(b.selic.ultimo) if b.selic.ultimo else '—'}). O resultado vai até "
                    f"{rotulo(anterior(k))}, e não até a data final da proposta ({rotulo(fim)}).")
                break
            s += taxa(k)
            ultimo = k
            res.linhas.append(Linha(rotulo(k), "SELIC (tributário)",
                                    "SELIC simples só sobre o principal (EC 113/2021, art. 3º, § 2º; "
                                    "Prov. CNJ 207/2025, art. 4º)",
                                    None, None, taxa(k), 1.0, 0.0, s, P0, J0 + P0 * s / 100, 0.0))
        selic_nova = centavos(P0 * s / 100, e.ano_proposta)
        modo = "truncada" if e.ano_proposta >= ANO_TRUNCA else "arredondada"
        if ultimo:
            res.trechos.append(dict(trecho="SELIC simples (tributário)", de=rotulo(db), ate=rotulo(ultimo),
                                    descricao=f"SELIC somada {s:.2f}% sobre o principal {P0:,.2f} = "
                                              f"{selic_nova:,.2f} ({modo} em centavos), somada aos juros"))
        res.principal = centavos(P0, e.ano_proposta)
        res.juros = round(centavos(J0, e.ano_proposta) + selic_nova, 2)
        res.selic = 0.0
        return res


REGRAS = {
    "Nacional": UniaoTributario(),
    "Subnacional": EmDesenvolvimento("Subnacional", "Tributário", "Regra tributária subnacional a ser informada."),
}
