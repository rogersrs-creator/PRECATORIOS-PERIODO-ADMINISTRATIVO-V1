"""
App Streamlit · Período administrativo dos precatórios
(da data-base do processo até a data-base da proposta indicada)

Executar localmente:  streamlit run app.py
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

import config
from fontes import carregar_todas
from motores import ESFERAS, NATUREZAS, Bases, Entrada, calcular, data_final, regra_para
from motores.base import rotulo
from motores.nacional.uniao import OBS_JUROS
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
    st.caption("Refaz os 15 casos certificados da União (não tributários) com os índices carregados e o motor "
               f"atual e compara o total (tolerância de R$ {conf.TOLERANCIA:.2f}; os centavos vêm de "
               "arredondamento). Casos em dados/CASOS-CERTIFICADOS.csv.")
    linhas = conf.conferir_todos(bases, df_graca)
    df = pd.DataFrame([{k: v for k, v in x.items() if k != "resultado"} for x in linhas])
    ok = (df["situacao"] == "Fecha").sum()
    (st.success if ok == len(df) else st.error)(f"{ok} de {len(df)} casos fecham.")
    st.dataframe(df.rename(columns={"caso": "Caso", "proposta": "Proposta", "data_base": "Data-base",
                                    "obs_juros": "OBS-JUROS aplicada", "obs_na_base": "OBS-JUROS na base",
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
           "orçamentária, conforme as regras do deck v9.")

c1, c2, c3 = st.columns(3)
esfera = c1.selectbox("Esfera", list(ESFERAS))
natureza = c2.selectbox("Natureza", NATUREZAS)
ano = c3.number_input("Ano da proposta", min_value=2001, max_value=2100, value=2028, step=1)

regra = regra_para(esfera, int(ano), natureza)
fim, origem_fim = data_final(int(ano), df_graca)
if regra is None or not regra.disponivel:
    st.warning(f"**{esfera} · {natureza}**: {regra.descricao if regra else 'sem regime'} "
               "Por enquanto o app calcula só **Nacional · Não Tributário** (União).")
    st.stop()
st.info(f"**Regime:** {regra.nome}. {regra.descricao}\n\n"
        f"**Data final (data-base da proposta {int(ano)}):** {rotulo(fim)} ({origem_fim}). "
        f"As variações entram até {rotulo((fim[0] - (fim[1] == 1), 12 if fim[1] == 1 else fim[1] - 1))}.")

with st.form("entrada"):
    d1, d2, d3 = st.columns(3)
    mes_db = d1.number_input("Data-base do processo: mês", 1, 12, 1)
    ano_db = d2.number_input("Data-base do processo: ano", 2000, 2100, 2020)
    obs = d3.selectbox("OBS-JUROS (obrigatória)", ["— escolha —"] + OBS_JUROS,
                       help="O que a sentença fixou sobre juros de mora. Em branco ou 'sem informação' não é "
                            "regra válida: escolha uma das quatro.")
    v1, v2, v3 = st.columns(3)
    principal = v1.number_input("Principal na data-base (R$)", min_value=0.0, step=0.01, format="%.2f")
    juros = v2.number_input("Juros na data-base (R$)", min_value=0.0, step=0.01, format="%.2f")
    selic = v3.number_input("SELIC na data-base (R$)" + (" · obrigatório desde a proposta 2027" if ano >= 2027 else ""),
                            min_value=0.0, step=0.01, format="%.2f",
                            help="Parcela da SELIC já existente no cálculo homologado (data-base a partir de 12/2021). "
                                 "Informe 0,00 se não houver.")
    enviar = st.form_submit_button("Calcular", type="primary")

if enviar:
    if obs not in OBS_JUROS:
        st.error("Escolha a OBS-JUROS: 1% ao mês, 0,5% ao mês, Poupança ou Não incidem.")
        st.stop()
    entrada = Entrada(esfera, natureza, int(ano), (int(ano_db), int(mes_db)), principal, juros, obs,
                      selic)
    try:
        st.session_state["resultado"] = calcular(entrada, bases, df_graca)
    except (ValueError, NotImplementedError) as e:
        st.session_state.pop("resultado", None)
        st.error(str(e))

res = st.session_state.get("resultado")
if res:
    for a in res.avisos:
        st.warning(a)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Principal", brl(res.principal))
    m2.metric("Juros", brl(res.juros))
    m3.metric("SELIC", brl(res.selic))
    m4.metric("Total", brl(res.total))
    st.subheader(f"Posição na proposta {res.entrada.ano_proposta}")
    st.caption("Como os valores entram na base de propostas. Desde a proposta 2027 o campo SELIC é obrigatório e "
               "fica separado; até a 2026 a SELIC vem somada aos juros.")
    st.dataframe(pd.DataFrame([{k: brl(v) for k, v in res.posicao_proposta().items()}]), hide_index=True,
                 width="stretch")
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
