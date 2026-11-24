"""
App Streamlit · Período administrativo dos precatórios
(da data-base do processo até a data-base da proposta indicada)

Executar localmente:  streamlit run app.py
"""
from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

import config
from fontes import carregar_todas, para_numero
from motores import ESFERAS, NATUREZAS, Bases, Entrada, calcular, data_final, regra_para
from motores.base import rotulo
from motores.nacional.uniao import OBS_JUROS
from motores.tributario import OBS_TRIBUTARIO
from importacao import brl as fmt_imp, importar_dados
from relatorio import brl, gerar_excel, tabela

st.set_page_config(page_title="Período administrativo", page_icon="📅", layout="wide")


def obter_urls(somente_local: bool) -> dict:
    if somente_local:
        return {}
    urls = dict(config.PLANILHAS)
    try:
        if "planilhas" in st.secrets:
            urls.update({k.upper(): v for k, v in st.secrets["planilhas"].items()})
    except Exception:
        pass
    return urls


@st.cache_data(ttl=3600, show_spinner="Carregando índices...")
def carregar_bases_cache(urls_itens: tuple):
    return carregar_todas(dict(urls_itens))


with st.sidebar:
    st.header("Bases de índices")
    somente_local = st.checkbox("Usar só os arquivos locais (pasta dados/)", value=False,
                                help="Marque para rodar sem internet ou para testar os CSV da pasta dados/.")
    if st.button("🔄 Recarregar índices", width="stretch"):
        carregar_bases_cache.clear()
        st.session_state.pop("resultado", None)

try:
    dfs, df_graca, origens = carregar_bases_cache(tuple(sorted(obter_urls(somente_local).items())))
except Exception as e:
    st.error(f"Não foi possível carregar as bases de índices.\n\n**Detalhe:** {e}\n\n"
             "Se estiver sem internet, marque **Usar só os arquivos locais** na barra lateral.")
    st.stop()

bases = Bases.de_dataframes(dfs)

with st.sidebar:
    for s in (bases.ipcae, bases.poupanca, bases.selic, bases.ipca):
        st.caption(f"**{s.nome}**: variações até {rotulo(s.ultimo) if s.ultimo else '—'}")
    _falhas = [f"{k}: {v}" for k, v in origens.items() if str(v).startswith("⚠️")]
    if _falhas:
        st.warning("Planilha(s) do Google Sheets não carregaram; o app usou o CSV de reserva:\n\n" +
                   "\n\n".join(_falhas))
    with st.expander("Origem dos dados"):
        for k, v in origens.items():
            st.write(f"{k}: {v}")
    st.divider()
    pagina = st.radio("Página", ["Cálculo", "Conferência dos casos certificados"])

# ------------------------------------------------------------------------------
# Conferência
# ------------------------------------------------------------------------------
if pagina == "Conferência dos casos certificados":
    import conferencia as conf
    st.title("✅ Conferência dos casos certificados")
    st.caption("Refaz os casos certificados da União (não tributários X e tributários T) com os índices carregados e o motor "
               f"atual e compara o total (tolerância de R$ {conf.TOLERANCIA:.2f}; os centavos vêm de "
               "arredondamento). Casos em dados/CASOS-CERTIFICADOS.csv.")
    linhas = conf.conferir_todos(bases, df_graca)
    df = pd.DataFrame([{k: v for k, v in x.items() if k != "resultado"} for x in linhas])
    ok = (df["situacao"] == "Fecha").sum()
    (st.success if ok == len(df) else st.error)(f"{ok} de {len(df)} casos fecham.")
    st.dataframe(df.rename(columns={"caso": "Caso", "proposta": "Proposta", "data_base": "Data-base",
                                    "natureza": "Natureza", "obs_juros": "OBS-JUROS aplicada", "obs_na_base": "OBS-JUROS na base",
                                    "calculado": "Calculado", "certificado": "Certificado",
                                    "diferenca": "Diferença", "selic_proposta": "SELIC-PROPOSTA calculada",
                                    "selic_certificada": "SELIC-PROPOSTA certificada", "situacao": "Situação"}),
                 hide_index=True, width="stretch")
    st.stop()

# ------------------------------------------------------------------------------
# Cálculo
# ------------------------------------------------------------------------------
st.title("📅 Período administrativo")
st.caption("Atualização do valor da data-base do cálculo homologado até a data-base dos cálculos da proposta "
           "orçamentária, conforme as regras do deck v12.")

c_esf, c_nat, c_ano, c_reg = st.columns([1.2, 1.1, 1, 3])
esfera = c_esf.radio("Esfera", list(ESFERAS), horizontal=True)
natureza = c_nat.radio("Natureza", NATUREZAS, horizontal=True,
                       help="Tributário (União): SELIC simples só sobre o principal, somada aos juros.")
anos_graca = sorted(df_graca["ANO_PROPOSTA"].unique().tolist())
anos_disponiveis = list(range(max(anos_graca[-1] if anos_graca else 2027, date.today().year) + 3, 2000, -1))
ano = c_ano.selectbox("Ano da proposta", anos_disponiveis, index=None, placeholder="Selecione o ano...",
                      help="Propostas de 2001 em diante. Fora da planilha GRACA, a data final segue a CF, art. 100, § 5º.")

regra = regra_para(esfera, ano or 2028, natureza)
if regra is None or not regra.disponivel:
    st.info(f"O modelo de cálculo para **{esfera} · {natureza}** ainda está em desenvolvimento "
            f"({regra.descricao if regra else 'sem regime'}). Selecione **Nacional** para calcular.")
    st.stop()
if ano is None:
    st.stop()
ano = int(ano)
fim, origem_fim = data_final(ano, df_graca)
fim_ts = date(fim[0], fim[1], 1)
c_reg.info(f"**Regime:** {regra.nome}. {regra.descricao}\n\n"
           f"**Data-base da proposta {ano}:** {fim_ts:%d/%m/%Y} ({origem_fim}). "
           f"As variações entram até o mês anterior.")

tributario = natureza == "Tributário"
# Tributário: não há campo Selic separado nem OBS-JUROS; a SELIC já apurada fica nos juros (casos T01 a T07).
selic_obrigatorio = ano >= 2027 and not tributario

for _k, _v in (("principal_txt", ""), ("juros_txt", "0,00"), ("selic_txt", ""), ("data_base", None), ("obs", None)):
    st.session_state.setdefault(_k, _v)

with st.expander("📋 Colar os dados da tela do sistema", expanded=False):
    st.caption("Copie da tela do sistema (Ctrl+C) as linhas do processo e cole abaixo (Ctrl+V). Exemplo:\n\n"
               "Valor Principal 108.601,00 Data Base 01/07/2025  \n"
               "Valor Selic 35.156,84 Data Base 01/07/2025  \n"
               "Juros de mora fixados na sentença: Não incidem\n\n"
               "Os campos do formulário são preenchidos para conferência antes do cálculo.")
    texto_colado = st.text_area("Texto copiado", height=120, label_visibility="collapsed", key="texto_colado")
    if st.button("Importar", type="primary"):
        imp = importar_dados(texto_colado)
        if imp["erros"]:
            for _e in imp["erros"]:
                st.error(_e)
        else:
            st.session_state["principal_txt"] = fmt_imp(imp["principal"])
            if selic_obrigatorio:
                st.session_state["juros_txt"] = fmt_imp(imp["juros"])
                st.session_state["selic_txt"] = fmt_imp(imp["selic"])
            else:
                # Até a proposta 2026 não há campo Selic: a SELIC faz parte dos juros.
                st.session_state["juros_txt"] = fmt_imp((imp["juros"] or 0.0) + (imp["selic"] or 0.0))
                st.session_state["selic_txt"] = ""
                if imp["selic"]:
                    imp["avisos"].append((f"Tributário: não há campo Selic. O Valor Selic "
                                          if tributario else f"Proposta {ano}: até 2026 não há campo Selic. O Valor Selic ")
                                         + f"({fmt_imp(imp['selic'])}) foi somado aos juros.")
            if tributario:
                imp["avisos"] = [a for a in imp["avisos"] if "OBS-JUROS" not in a and "Juros de mora" not in a]
            st.session_state["data_base"] = imp["data_base"]
            st.session_state["obs"] = imp["obs_juros"]
            st.session_state.pop("resultado", None)
            st.session_state["importado"] = imp
            st.rerun()
    imp = st.session_state.get("importado")
    if imp:
        st.success(f"Importado: principal {fmt_imp(imp['principal'])}, juros {fmt_imp(imp['juros'])}, "
                   f"selic {fmt_imp(imp['selic'])}, data-base {imp['data_base']:%d/%m/%Y}, "
                   f"OBS-JUROS {imp['obs_juros'] or '— escolha —'}. "
                   "Confira no formulário e clique em Calcular.")
        for _a in imp["avisos"]:
            st.warning(_a)

with st.form("form_calculo"):
    st.subheader("Dados do processo")
    c1, c2, c3, *c4 = st.columns(4 if selic_obrigatorio else 3)
    data_base = c1.date_input("Data-base do cálculo", key="data_base",
                              min_value=date(1996, 1, 1) if tributario else date(2000, 1, 1),
                              max_value=fim_ts, format="DD/MM/YYYY",
                              help="Data-base do cálculo homologado. Só o mês/ano é considerado (o dia é ajustado "
                                   "para 1º).")
    principal_txt = c2.text_input("Valor principal (R$)", placeholder="Ex.: 871,04", key="principal_txt")
    juros_txt = c3.text_input("Juros (R$)", key="juros_txt",
                              help="Tributário: a SELIC já apurada no cálculo homologado. Não recebe SELIC de novo."
                              if tributario else None if selic_obrigatorio else "Até a proposta 2026 a SELIC já existente no cálculo "
                                                                  "homologado entra aqui, somada aos juros.")
    if selic_obrigatorio:
        selic_txt = c4[0].text_input("Selic (R$) *", placeholder="Obrigatório (ex.: 0,00)", key="selic_txt",
                                     help="Campo obrigatório desde a proposta 2027. Parcela da SELIC já existente no "
                                          "cálculo homologado (data-base a partir de 12/2021). Informe 0,00 se não "
                                          "houver.")
    else:
        selic_txt = ""   # até a proposta 2026 a SELIC já existente faz parte dos juros
    if tributario:
        obs = OBS_TRIBUTARIO
        st.caption("Tributário: não há OBS-JUROS. Incide só a SELIC simples sobre o principal "
                   "(EC 113/2021, art. 3º, § 2º; Provimento CNJ 207/2025, art. 4º).")
    else:
        obs = st.radio("OBS-JUROS (obrigatória)", OBS_JUROS, horizontal=True, key="obs",
                       help="O que a sentença fixou sobre juros de mora. Em branco ou 'sem informação' não é regra "
                            "válida: escolha uma das quatro.")
    enviar = st.form_submit_button("Calcular", type="primary", width="stretch")

if enviar:
    erros = []
    principal = para_numero(principal_txt)
    juros = para_numero(juros_txt) if juros_txt.strip() else 0.0
    if not principal_txt.strip() or pd.isna(principal) or principal < 0:
        erros.append("Informe um **valor principal** válido (ex.: 871,04; use 0,00 se não houver).")
    if pd.isna(juros) or juros < 0:
        erros.append("Informe um valor de **juros** válido (use 0,00 se não houver).")
    if not selic_txt.strip():
        if selic_obrigatorio:
            erros.append("O campo **Selic** é obrigatório nesta proposta (informe 0,00 se não houver).")
        selic = 0.0
    else:
        selic = para_numero(selic_txt)
        if pd.isna(selic) or selic < 0:
            erros.append("Informe um valor de **Selic** válido (ex.: 1.234,56).")
    if data_base is None:
        erros.append("Informe a **data-base do cálculo**.")
    if obs not in OBS_JUROS and not tributario:
        erros.append("Escolha a **OBS-JUROS**: 1% ao mês, 0,5% ao mês, Poupança ou Não incidem.")
    if erros:
        for e in erros:
            st.error(e)
        st.session_state.pop("resultado", None)
    else:
        entrada = Entrada(esfera, natureza, ano, (data_base.year, data_base.month), principal, juros, obs, selic)
        if selic_obrigatorio and juros > 0 and selic == 0 and (data_base.year, data_base.month) >= (2021, 12):
            st.warning("Data-base a partir de 12/2021 com **Juros** preenchidos e **Selic** zerada. Se o valor "
                       "informado em Juros for a SELIC do cálculo homologado, mova-o para o campo **Selic**: a SELIC "
                       "fica no próprio campo e não recebe SELIC de novo.")
        try:
            st.session_state["resultado"] = calcular(entrada, bases, df_graca)
        except (ValueError, NotImplementedError) as e:
            st.session_state.pop("resultado", None)
            st.error(str(e))

res = st.session_state.get("resultado")
if res:
    for a in res.avisos:
        st.warning(a)
    pos = res.posicao_proposta()
    st.subheader(f"Valores na proposta {res.entrada.ano_proposta}")
    if res.entrada.ano_proposta >= 2027:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Principal", brl(pos["VALOR-PRINCIPAL-PROPOSTA"]))
        m2.metric("Juros", brl(pos["VALOR-JUROS-PROPOSTA"]))
        m3.metric("Selic", brl(pos["SELIC-PROPOSTA"]))
        m4.metric("Total", brl(pos["TOTAL-PROPOSTA"]))
    else:
        m1, m2, m3 = st.columns(3)
        m1.metric("Principal", brl(pos["VALOR-PRINCIPAL-PROPOSTA"]))
        m2.metric("Juros", brl(pos["VALOR-JUROS-PROPOSTA"]))
        m3.metric("Total", brl(pos["TOTAL-PROPOSTA"]))
        if res.entrada.natureza == "Tributário":
            st.caption("Tributário: a SELIC do período está somada aos juros; o principal não muda.")
        elif res.selic:
            st.caption(f"Até a proposta 2026 não há campo Selic: a SELIC de 12/2021 em diante "
                       f"({brl(res.selic)}) está somada aos juros ({brl(res.juros)} + {brl(res.selic)}).")
    st.subheader("Trechos")
    st.dataframe(pd.DataFrame(res.trechos).rename(columns={"trecho": "Trecho", "de": "De", "ate": "Até",
                                                           "descricao": "Resumo"}),
                 hide_index=True, width="stretch")
    st.subheader("Memória mês a mês")
    st.dataframe(tabela(res), hide_index=True, width="stretch", height=420)
    e = res.entrada
    st.download_button("⬇️ Baixar Excel", gerar_excel(res),
                       file_name=f"PERIODO-ADM-{e.esfera.upper()}-PROPOSTA-{e.ano_proposta}-DB-"
                                 f"{e.data_base[1]:02d}-{e.data_base[0]}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
