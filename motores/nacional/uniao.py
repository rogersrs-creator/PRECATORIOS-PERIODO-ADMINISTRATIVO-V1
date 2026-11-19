"""
União, não tributário: da data-base do processo à data-base da proposta.

Regras do deck v9 (Período administrativo), conferidas nos casos certificados:

Trecho 0 · data-base em 2000: UFIR fixa até 12/2000 e, em 01/2001, o IPCA-E acumulado de
           jan a dez/2000 (fator 1,060356), qualquer que seja o mês da data-base
           (Res. CNJ 303/2019, art. 21-A, IX; regra do caso X02; norma desta fase por revisar).
Trecho 1 · até 11/2021: IPCA-E sem TR sobre principal e juros existentes
           (Res. CNJ 303/2019, art. 21-A, X; Tema 810; ADIs 4357/4425).
           Juros de mora simples sobre o principal corrigido, conforme a OBS-JUROS (Tema 96):
           "1% ao mês" / "0,5% ao mês" até 05/2009 e poupança desde 06/2009
           (Lei 11.960/2009; Tema 1170); "Poupança" o período todo; "Não incidem" nenhum.
           Principal zero: sem juros novos.
Trecho 2 · 12/2021 a 08/2025: SELIC simples, uma única vez, sobre principal + juros
           consolidados (EC 113/2021, art. 3º; Res. CJF 983/2026, art. 7º, § 3º, I e § 4º).
           Incide qualquer que seja a OBS-JUROS.
Trecho 3 · desde 09/2025 (propostas 2027 em diante): IPCA sobre principal, juros e SELIC e
           2% a.a. simples (0,1667% a.m.) sobre o principal corrigido, limitados à SELIC
           (EC 136/2025; Res. CJF 983/2026, art. 7º, § 3º, III). Mês a mês, se a SELIC for menor que
           (1 + IPCA) x (1 + 0,1667%) - 1, nesse mês vale a SELIC só sobre o principal, lançada no campo
           Selic, sem IPCA (como no V6; decisão de 19/11/2026). Os 2% valem também quando a
           OBS-JUROS é "Não incidem" (decisão de 19/11/2026); principal zero, sem 2%.
"""
from __future__ import annotations

from decimal import ROUND_DOWN, Decimal

from motores.base import (Bases, Entrada, Linha, Mes, Regra, Resultado, anterior, meses,
                          proximo, rotulo)

OBS_JUROS = ["1% ao mês", "0,5% ao mês", "Poupança", "Não incidem"]
TAXA_TITULO = {"1% ao mês": 1.0, "0,5% ao mês": 0.5}

INICIO_POUPANCA: Mes = (2009, 6)   # Lei 11.960/2009; Tema 1170 (mês confirmado no caso X01)
INICIO_SELIC: Mes = (2021, 12)     # EC 113/2021
INICIO_IPCA: Mes = (2025, 9)       # EC 136/2025; Res. CJF 983/2026, art. 7º, § 3º, III
JUROS_EC136_MES = 2.0 / 12         # 2% a.a. simples, em % ao mês

# IPCA-E de jan a dez/2000 (variações do IBGE, planilha "IPCA E" do Rogers, coluna C).
# A planilha IPCAE-SEM-TR começa em 07/2000, por isso os meses de 2000 ficam aqui.
IPCAE_2000 = [0.65, 0.34, 0.09, 0.47, 0.09, 0.08, 0.78, 1.99, 0.45, 0.18, 0.17, 0.60]
# atenção: na convenção "linha do mês m = variação de m-1", a lista acima corresponde às
# linhas 02/2000 a 01/2001 da planilha do Rogers, isto é, às variações de jan a dez/2000.


def fator_2000() -> float:
    f = 1.0
    for v in IPCAE_2000:
        f *= 1 + v / 100
    return f


# Etapas em que os valores são truncados em centavos antes do trecho seguinte (além do fim do cálculo).
TRUNCAR_ETAPAS: set[str] = {"selic"}  # SELIC truncada ao fim de 08/2025 (caso X18, 19/11/2026)


def truncar(v: float) -> float:
    """Trunca em centavos (sem arredondar), como nos cálculos certificados."""
    return float(Decimal(repr(v)).quantize(Decimal("0.01"), rounding=ROUND_DOWN))


class UniaoNaoTributario(Regra):
    nome = "União · não tributário"
    esfera = "Nacional"
    natureza = "Não Tributário"
    ano_ini = 2001
    ano_fim = 9999
    descricao = ("IPCA-E sem TR e juros do título (poupança desde 06/2009) até 11/2021; SELIC simples "
                 "sobre o consolidado de 12/2021 a 08/2025; IPCA + 2% a.a. desde 09/2025.")

    def calcular(self, e: Entrada, b: Bases, fim: Mes, origem: str) -> Resultado:
        res = Resultado(entrada=e, data_final=fim, origem_data_final=origem)
        db = e.data_base
        if e.obs_juros not in OBS_JUROS:
            raise ValueError("A OBS-JUROS é obrigatória: escolha 1% ao mês, 0,5% ao mês, Poupança ou "
                             "Não incidem.")
        if db < (2000, 1):
            raise ValueError("Data-base anterior a 01/2000: a regra desse período (UFIR) ainda não foi "
                             "definida para o aplicativo.")
        if db >= fim:
            raise ValueError(f"A data-base ({rotulo(db)}) precisa ser anterior à data final da proposta "
                             f"{e.ano_proposta} ({rotulo(fim)}).")

        P0, J0, S0 = float(e.principal), float(e.juros), float(e.selic or 0)
        if S0 and e.ano_proposta < 2027:
            raise ValueError("Até a proposta 2026 não há campo Selic: a SELIC já existente entra nos juros.")
        if S0 and db < INICIO_SELIC:
            raise ValueError("SELIC na data-base só existe para data-base a partir de 12/2021 (EC 113/2021). "
                             "Para data-base anterior, deixe o campo SELIC em zero.")
        tem_principal = P0 > 0
        f, js = 1.0, 0.0
        linhas = res.linhas
        linhas.append(Linha(rotulo(db) + " (data-base)", "Data-base", "Valores da data-base",
                            None, None, None, 1.0, 0.0, 0.0, P0, J0, S0))

        def taxa_juros(k: Mes) -> float:
            if not tem_principal or e.obs_juros == "Não incidem":
                return 0.0
            if e.obs_juros == "Poupança" or k >= INICIO_POUPANCA:
                return b.poupanca[k]
            return TAXA_TITULO[e.obs_juros]

        def falta(serie, k: Mes) -> bool:
            if k in serie:
                return False
            res.parcial = True
            res.avisos.append(
                f"Cálculo PARCIAL: a planilha {serie.nome} não tem a variação de {rotulo(k)} "
                f"(última: {rotulo(serie.ultimo) if serie.ultimo else '—'}). O resultado vai até "
                f"{rotulo(anterior(k))}, e não até a data final da proposta ({rotulo(fim)}).")
            return True

        # ---------------- Trecho 0: data-base em 2000 ----------------
        inicio = db
        if db[0] == 2000:
            f2000 = fator_2000()
            js_2000 = 0.0
            for k in meses(db, min((2001, 1), fim)):
                js_2000 += taxa_juros(k)
            js += js_2000
            # Juros contados desde a data-base, inclusive em 2000 (confirmado pelo Rogers em 19/11/2026).
            f *= f2000
            linhas.append(Linha(f"{rotulo(db)} a 12/2000", "0 · UFIR / IPCA-E de 2000",
                                "UFIR fixa em 2000; em 01/2001, IPCA-E acumulado de jan a dez/2000 "
                                "(Res. CNJ 303/2019, art. 21-A, IX; regra do caso X02)",
                                (f2000 - 1) * 100, js_2000 or None, None, f, js, 0.0,
                                P0 * f, J0 * f + P0 * f * js / 100, 0.0))
            res.trechos.append(dict(trecho="0 · UFIR e IPCA-E de 2000", de=rotulo(db), ate="12/2000",
                                    descricao=f"fator {f2000:.6f} aplicado em 01/2001"))
            inicio = (2001, 1)

        # ---------------- Trecho 1: IPCA-E + juros até 11/2021 ----------------
        fim1 = min(fim, INICIO_SELIC)
        ini1 = inicio
        parou = False
        for k in meses(inicio, fim1):
            if falta(b.ipcae, k):
                parou = True
                break
            usa_poupanca = (tem_principal and e.obs_juros != "Não incidem"
                            and (e.obs_juros == "Poupança" or k >= INICIO_POUPANCA))
            if usa_poupanca and falta(b.poupanca, k):
                parou = True
                break
            jr = taxa_juros(k)
            f *=1 + b.ipcae[k] / 100
            js += jr
            if jr == 0:
                regra = "IPCA-E" + (", sem juros (principal zero)" if not tem_principal and
                                    e.obs_juros != "Não incidem" else ", sem juros")
            elif e.obs_juros == "Poupança" or k >= INICIO_POUPANCA:
                regra = "IPCA-E + juros da poupança" + (" (Lei 11.960/2009; Tema 1170)"
                                                        if e.obs_juros in TAXA_TITULO else "")
            else:
                regra = f"IPCA-E + juros de {e.obs_juros} (título)"
            linhas.append(Linha(rotulo(k), "1 · IPCA-E + juros", regra, b.ipcae[k], jr, None, f, js, 0.0,
                                P0 * f, J0 * f + P0 * f * js / 100, 0.0))
        P = P0 * f
        J = J0 * f + P * js / 100
        if "ipcae" in TRUNCAR_ETAPAS and ini1 < fim1:
            P, J = truncar(P), truncar(J)
        S = S0
        if ini1 < fim1:
            res.trechos.append(dict(trecho="1 · IPCA-E + juros do título", de=rotulo(ini1),
                                    ate=rotulo(anterior(fim1)),
                                    descricao=f"fator {f:.6f}; juros {js:.4f}% sobre o principal corrigido"))
        if parou:
            return self._fechar(res, P, J, S)

        # ---------------- Trecho 2: SELIC simples 12/2021 a 08/2025 ----------------
        ini2, fim2 = max(db, INICIO_SELIC), min(fim, INICIO_IPCA)
        s = 0.0
        if ini2 < fim2:
            base = P + J
            for k in meses(ini2, fim2):
                if falta(b.selic, k):
                    parou = True
                    break
                s += b.selic[k]
                S = S0 + base * s / 100
                linhas.append(Linha(rotulo(k), "2 · SELIC (EC 113)",
                                    "SELIC simples sobre principal + juros consolidados (EC 113/2021, art. 3º)",
                                    None, None, b.selic[k], f, js, s, P, J, S))
            if "selic" in TRUNCAR_ETAPAS:
                S = truncar(S)
            res.trechos.append(dict(trecho="2 · SELIC simples (EC 113)", de=rotulo(ini2),
                                    ate=rotulo(anterior(fim2)),
                                    descricao=f"SELIC somada {s:.4f}% sobre {base:,.2f}"
                                    + (f" (mais a SELIC da data-base, {S0:,.2f}, que não recebe SELIC)" if S0 else "")))
            if parou:
                return self._fechar(res, P, J, S)

        # ---------------- Trecho 3: IPCA + 2% a.a. desde 09/2025 ----------------
        ini3 = max(db, INICIO_IPCA)
        if ini3 < fim:
            fa, n, n_selic = 1.0, 0, 0
            for k in meses(ini3, fim):
                if falta(b.ipca, k):
                    break
                jr = JUROS_EC136_MES if tem_principal else 0.0
                composto = ((1 + b.ipca[k] / 100) * (1 + jr / 100) - 1) * 100
                sel = b.selic[k] if k in b.selic else None
                if sel is not None and sel < composto:
                    # Mês em que a SELIC é menor: SELIC só sobre o principal, lançada no campo Selic;
                    # principal, juros e Selic não recebem IPCA (decisão do Rogers, 19/11/2026; regra do V6).
                    n_selic += 1
                    S = S + P * sel / 100
                    linhas.append(Linha(rotulo(k), "3 · SELIC menor (EC 136)",
                                        f"SELIC ({sel:.2f}%) menor que IPCA + 2% a.a. ({composto:.4f}%): SELIC só "
                                        "sobre o principal, no campo Selic", b.ipca[k], None, sel, f * fa, js, s,
                                        P, J, S))
                    continue
                fa *= 1 + b.ipca[k] / 100
                n += 1
                P = P * (1 + b.ipca[k] / 100)
                J = J * (1 + b.ipca[k] / 100) + P * jr / 100
                S = S * (1 + b.ipca[k] / 100)
                linhas.append(Linha(rotulo(k), "3 · IPCA + 2% a.a. (EC 136)",
                                    "IPCA sobre tudo" + (" + 2% a.a. simples sobre o principal" if tem_principal
                                                         else "") + " (EC 136/2025; Res. CJF 983/2026)",
                                    b.ipca[k], jr or None, sel, f * fa, js, s, P, J, S))
            res.trechos.append(dict(trecho="3 · IPCA + 2% a.a. (EC 136)", de=rotulo(ini3),
                                    ate=rotulo(anterior(fim)) if not res.parcial else "parcial",
                                    descricao=f"IPCA {(fa - 1) * 100:.4f}%; {n} meses de IPCA + 2% a.a."
                                              + (f"; {n_selic} meses com a SELIC menor (só sobre o principal)"
                                                 if n_selic else "")))
        return self._fechar(res, P, J, S)

    @staticmethod
    def _fechar(res: Resultado, P: float, J: float, S: float) -> Resultado:
        # Os cálculos certificados truncam os centavos (decisão de 19/11/2026): cada parcela é truncada.
        res.principal, res.juros, res.selic = truncar(P), truncar(J), truncar(S)
        return res
