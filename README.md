# Período administrativo dos precatórios · App Streamlit

Calcula a atualização do valor **da data-base do cálculo homologado até a data-base dos cálculos da proposta
orçamentária** indicada, com as regras do **deck v12** (Período administrativo, 19/11/2026). Usa a mesma base de
código e a mesma estrutura do app V6 (PRECATORIOS-TODOS-V6): esfera, natureza, ano da proposta, bases no Google
Sheets com CSV de reserva, relatório Excel e conferência de casos.

## Rodar

No computador (Python 3.10 ou mais novo):

```bash
pip install -r requirements.txt
streamlit run app.py
```

No Windows, basta dar dois cliques em `INICIAR-WINDOWS.bat`. O app abre no navegador.

Na web (Streamlit Cloud): share.streamlit.io › Create app › este repositório › branch `main` › arquivo `app.py` ›
Deploy. Não precisa de Secrets nem de senha: o app só lê planilhas públicas.

Conferência pela linha de comando: `python conferencia.py` (Google Sheets) ou `python conferencia.py --local`
(só os CSV da pasta `dados/`).

## O que calcula

| Esfera | Natureza | Situação |
|---|---|---|
| Nacional (União) | Não tributário | **Pronto**, propostas de 2001 em diante |
| Nacional (União) | Tributário | **Pronto** (v13), data-base desde 01/1996 |
| Subnacional | Não tributário / Tributário | aguardando as regras |

### Entradas

- **Ano da proposta** (lista de 2001 em diante).
- **Data-base do cálculo** (calendário DD/MM/AAAA; só mês e ano contam).
- **Valor principal** e **Juros** (formato brasileiro, ex.: 1.234,56).
- **Selic**: só desde a proposta 2027, obrigatória (0,00 se não houver). Até a proposta 2026 não existe campo Selic:
  a SELIC já existente no cálculo homologado entra nos juros e segue as regras daquele período.
- **OBS-JUROS** (obrigatória): 1% ao mês, 0,5% ao mês, Poupança ou Não incidem.

Os dados podem ser **colados da tela do sistema** ("📋 Colar os dados da tela do sistema"):

```
Valor Principal 108.601,00 Data Base 01/07/2025
Valor Selic 35.156,84 Data Base 01/07/2025
Juros de mora fixados na sentença: Não incidem
```

O app preenche o formulário para conferência. Linhas "Valor Juros" também são lidas; valores repetidos são somados
(com aviso); datas-base diferentes impedem a importação; texto de juros de mora fora das quatro regras deixa a
OBS-JUROS em branco e avisa. Em proposta até 2026, um "Valor Selic" colado é somado aos juros, com aviso.

### Tributário (União) · v12–v13

Regra deduzida dos 7 casos tributários homologados (T01–T07, propostas 2023 a 2027, em
`dados/CASOS-TRIBUTARIOS.csv`), que fecham ao centavo:

- **SELIC simples só sobre o principal**, do mês da data-base (inclusive) ao mês anterior à data-base da
  proposta. Sem IPCA-E, IPCA, juros do título, poupança ou 2% a.a., e sem troca de regime em 12/2021 ou 09/2025.
- O principal não muda; os juros informados (SELIC já apurada) não mudam e não recebem SELIC; a SELIC nova é
  **somada aos juros**, inclusive na proposta 2027 (SELIC-PROPOSTA = 0 nos casos).
- Sem OBS-JUROS e sem campo Selic: um "Valor Selic" colado vai para os juros.
- **Centavos:** SELIC arredondada até a proposta 2026 (T03, T04, T05) e truncada desde a 2027 (T06).
- Normas: EC 113/2021, art. 3º, § 2º (redação da EC 136/2025); Provimento CNJ 207/2025, art. 4º; Res. CJF
  983/2026, art. 7º, caput e § 4º, e art. 8º, § 1º; Res. CNJ 303/2019, art. 22 (juros de mora só nos não tributários).
- Data-base desde 01/1996 (Lei 9.250/1995, art. 39, § 4º). A SELIC de 01/1996 a 12/2002 vem do Banco Central
  (SGS 4390) em `motores/selic_historica.py`; desde 01/2003, da planilha SELIC do V6. A regra é a mesma para
  qualquer proposta (confirmado pelo Rogers em 24/11/2026; o V6 também usa uma só regra tributária).

### Data final

Coluna DATA_BASE_INICIAL_CALCULOS da planilha GRACA (propostas 2012–2027). Para outros anos, a data-limite da CF,
art. 100, § 5º: 1º/jul do ano anterior até a proposta 2022, abril nas propostas 2023–2026 e 1º/fev desde a 2027
(proposta 2028 → 02/2027). As variações entram até o mês anterior à data final. Se faltar índice para algum mês, o
app calcula até o último mês disponível e marca o resultado como **PARCIAL**.

### Regras (cada trecho só entra se estiver entre a data-base e a data final)

0. **Data-base em 2000:** UFIR fixa e, em 01/2001, o IPCA-E acumulado de jan–dez/2000 (fator 1,060356), qualquer
   que seja o mês da data-base. Havendo juros do título, eles contam desde a data-base, inclusive os meses de 2000.
1. **Até 11/2021:** IPCA-E sem TR sobre principal e juros; juros simples do título sobre o principal corrigido:
   1% ou 0,5% a.m. até 05/2009 e poupança desde 06/2009 (Lei 11.960/2009; Tema 1170); "Poupança" o período todo;
   "Não incidem" nenhum. Principal zero: sem juros novos.
2. **12/2021 a 08/2025:** SELIC simples, uma vez, sobre principal + juros consolidados, qualquer que seja a
   OBS-JUROS (EC 113/2021; Res. CJF 983/2026, art. 7º, § 3º, I e § 4º). A Selic já existente na data-base (propostas
   desde 2027) é somada sem receber SELIC. A SELIC é truncada em centavos ao fim deste trecho.
3. **Desde 09/2025 (propostas 2027 em diante):** mês a mês, IPCA sobre principal, juros e Selic e 2% a.a. simples
   (0,1667% a.m.) sobre o principal corrigido, lançados nos juros (EC 136/2025; Res. CJF 983/2026, art. 7º, § 3º,
   III). Os 2% valem também com "Não incidem"; principal zero, sem 2%. **Limite da SELIC:** no mês em que a SELIC
   for menor que (1 + IPCA) × (1 + 0,1667%) − 1, vale a SELIC só sobre o principal, lançada no campo Selic, e nesse
   mês não há IPCA (Provimento CNJ 207/2025; regra do V6). Até 08/2026 isso não ocorreu.

**Centavos:** principal, juros e Selic são truncados (não arredondados), como nos cálculos certificados.

**Valores na proposta:** até a proposta 2026, a tela e o Excel mostram Principal, Juros (com a SELIC somada) e
Total, como na base de propostas; desde a 2027, a Selic fica em campo próprio. A memória mês a mês mostra a SELIC
numa coluna à parte, para conferência.

## Planilhas (bases)

| Base | Origem | Uso |
|---|---|---|
| IPCAE_SEM_TR | planilha própria no Drive | correção até 11/2021 |
| POUPANCA | mesma planilha do V6 | juros da poupança |
| SELIC | mesma planilha do V6 | trecho 2 e limite do trecho 3 |
| IPCA | mesma planilha do V6 | trecho 3 |
| GRACA | mesma planilha do V6 | data final da proposta |

Links em `config.py` (link sem `gid` = primeira aba). Se uma planilha do Drive não carregar, o app usa o CSV de
reserva da pasta `dados/` e mostra um aviso na barra lateral. "Usar só os arquivos locais" ignora os links.

## Conferência

16 casos certificados da União, não tributários, propostas 2015–2027 (`dados/CASOS-CERTIFICADOS.csv`, sem número de
processo nem nome de parte), incluindo o X18 (proposta 2027 com Selic na data-base). Todos fecham dentro de R$ 1,00:
8 em 0,00, 4 entre 0,01 e 0,05, e X01 (+0,66), X02 (+0,42), X04 (+0,16) e X05 (−0,27), de período longo de IPCA-E,
cuja origem não foi identificada (a razão entre números-índice do IBGE foi testada e piora os resultados).

## Estrutura

```
app.py              tela (cálculo e conferência)
importacao.py       leitura dos dados colados da tela do sistema
conferencia.py      refaz os casos certificados (também roda pela linha de comando)
fontes.py           leitura das bases (Google Sheets ou CSV local), adaptado do V6
relatorio.py        memória mês a mês e Excel
config.py           links das planilhas
motores/
├── __init__.py     registro: escolhe o motor por esfera, natureza e ano
├── base.py         séries, entrada, resultado e interface de regime
├── datas.py        data final de cada proposta
├── nacional/uniao.py   União, não tributário
├── subnacional/    em desenvolvimento
└── tributario.py   em desenvolvimento
dados/              CSV de reserva + CASOS-CERTIFICADOS.csv
```

O histórico das versões (v1 a v11) está nos commits deste repositório.
