# Período administrativo dos precatórios · App Streamlit (versão local 2)

Calcula a atualização do valor **da data-base do cálculo homologado até a data-base dos cálculos da
proposta orçamentária** indicada, com as regras do deck v9 (Período administrativo). Mesma base de código e
mesma estrutura do app V6 (PRECATORIOS-TODOS-V6): esfera, natureza, ano da proposta, bases no Google Sheets
com CSV de reserva, relatório Excel e conferência de casos.

## Rodar no computador

Precisa do Python 3.10 ou mais novo.

```bash
pip install -r requirements.txt
streamlit run app.py
```

No Windows, basta dar dois cliques em `INICIAR-WINDOWS.bat`. O app abre no navegador.

Conferência pela linha de comando (sem abrir o app): `python conferencia.py` (Google Sheets) ou
`python conferencia.py --local` (só os CSV da pasta `dados/`).

## O que calcula nesta versão

| Esfera | Natureza | Situação |
|---|---|---|
| Nacional (União) | Não tributário | **Pronto**, propostas de 2001 em diante |
| Nacional | Tributário | aguardando a regra |
| Subnacional | Não tributário / Tributário | aguardando as regras |

Entradas: ano da proposta, data-base do processo (mês/ano), principal, juros, **SELIC na data-base**
(obrigatória desde a proposta 2027; 0,00 se não houver) e **OBS-JUROS (obrigatória)**: 1% ao mês,
0,5% ao mês, Poupança ou Não incidem.

**SELIC na data-base (v2):** parcela da SELIC já existente no cálculo homologado; só é aceita para data-base a
partir de 12/2021. No trecho 2 ela é somada à SELIC nova, sem receber SELIC (sem capitalização, Res. CJF
983/2026, art. 7º, § 4º); no trecho 3 é corrigida pelo IPCA.

**Posição na proposta (v2):** a tela e o Excel trazem os valores como entram na base de propostas
(VALOR-PRINCIPAL-PROPOSTA, VALOR-JUROS-PROPOSTA, SELIC-PROPOSTA, TOTAL-PROPOSTA). Desde a proposta 2027 a SELIC
fica separada; até a 2026 vai somada aos juros, como nos casos certificados.

Trechos (cada um só entra se estiver entre a data-base e a data final):

0. **Data-base em 2000:** UFIR fixa e, em 01/2001, o IPCA-E acumulado de jan–dez/2000 (fator 1,060356).
1. **Até 11/2021:** IPCA-E sem TR sobre principal e juros; juros simples do título sobre o principal corrigido
   (1% ou 0,5% a.m. até 05/2009, poupança desde 06/2009; "Poupança" o período todo; "Não incidem" nenhum).
   Principal zero: sem juros novos.
2. **12/2021 a 08/2025:** SELIC simples, uma vez, sobre principal + juros consolidados (qualquer OBS-JUROS).
3. **Desde 09/2025 (propostas 2027+):** IPCA sobre tudo e 2% a.a. simples sobre o principal corrigido.
   Se em algum mês IPCA + 0,1667% passar da SELIC, o app avisa (regra ainda a definir).

**Data final:** coluna DATA_BASE_INICIAL_CALCULOS da planilha GRACA (propostas 2012–2027). Para outros anos,
a data-limite da CF, art. 100, § 5º: 1º/jul do ano anterior até 2022, abril em 2023–2026 e 1º/fev desde 2027
(proposta 2028 → 02/2027). Se faltar índice para algum mês, o app calcula até o último mês disponível e
marca o resultado como **PARCIAL**.

## Planilhas (bases)

| Base | Origem | Uso |
|---|---|---|
| IPCAE_SEM_TR | `dados/IPCAE-SEM-TR.csv` (nova; ainda sem planilha no Drive) | correção até 11/2021 |
| POUPANCA | mesma planilha do V6 | juros da poupança |
| SELIC | mesma planilha do V6 | trecho 2 e limite do trecho 3 |
| IPCA | mesma planilha do V6 | trecho 3 |
| GRACA | mesma planilha do V6 | data final da proposta |

Links em `config.py`. Link vazio = usa o CSV da pasta `dados/`. Na barra lateral, "Usar só os arquivos
locais" ignora os links.

## Estrutura

```
app.py              tela (cálculo e conferência)
conferencia.py      refaz os casos certificados (também roda pela linha de comando)
fontes.py           leitura das bases (Google Sheets ou CSV local), copiado do V6
relatorio.py        memória mês a mês e Excel
config.py           links das planilhas
motores/
├── __init__.py     registro: escolhe o motor por esfera, natureza e ano
├── base.py         séries, entrada, resultado e interface de regime
├── datas.py        data final de cada proposta
├── nacional/uniao.py   União, não tributário
├── subnacional/    em desenvolvimento
└── tributario.py   em desenvolvimento
dados/              CSV de reserva + CASOS-CERTIFICADOS.csv (15 casos, sem número de processo)
```

## Conferência

Os 15 casos certificados da União (não tributários, propostas 2015–2027) fecham com diferença de no máximo
R$ 0,67, só de arredondamento. A regra de arredondamento ainda será definida.
