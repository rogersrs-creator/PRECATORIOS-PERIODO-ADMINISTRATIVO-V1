"""
Links das planilhas do Google Sheets (as mesmas do app V6, compartilhadas).

Cole o link da ABA correta (termina em '#gid=NUMERO'). Se um link ficar vazio (""), o app usa o
CSV correspondente da pasta 'dados/'. Para rodar sem internet, marque "Usar só os arquivos
locais" na barra lateral do app (ou rode `python conferencia.py --local`).

A IPCAE-SEM-TR está no Drive desde 19/11/2026 (aba única IPCAE-SEM-TR); dados/IPCAE-SEM-TR.csv fica como reserva.
"""
import sys

PLANILHAS = {
    # IPCA-E sem TR (07/2000 = 1). colunas: data;variacao-mes;n_indice
    "IPCAE_SEM_TR": "https://docs.google.com/spreadsheets/d/1YirgR_GKC8Oc7JN7uOHJyAsmCLX4slkxaBY0IwhXGn4/edit?gid=0#gid=0",
    # colunas: data;variacao-mes;n_indice  (mesma planilha do V6)
    "POUPANCA": "https://docs.google.com/spreadsheets/d/15p8EWBw9N19uyQzsxgip42OuOPQIyAnV-zwAk7PPOKE/edit?gid=1434923967#gid=1434923967",
    # colunas: data;variacao-mes;n_indice  (mesma planilha do V6)
    "SELIC":    "https://docs.google.com/spreadsheets/d/129ivdR59PZCXlMRAl1h-9pLosQnW90TEmz6HOS17d7Q/edit?gid=850105924#gid=850105924",
    # colunas: data;variacao-mes;n_indice  (mesma planilha do V6)
    "IPCA":     "https://docs.google.com/spreadsheets/d/11GKOkuxJs4GSsLRQv8h79n-XdcVrAADgMR-7fjxvd2o/edit?gid=1260545934#gid=1260545934",
    # colunas: ANO_PROPOSTA;DATA_BASE_INICIAL_CALCULOS;FIM_PER_GRACA  (mesma planilha do V6)
    "GRACA":    "https://docs.google.com/spreadsheets/d/15bxluzMKAxs66fTgnRb4AY14ouN1ks79jQ4IFwlg_RE/edit?gid=935090251#gid=935090251",
}


def urls_locais() -> dict:
    """Links para a linha de comando: vazios (só CSV locais) se for passado --local."""
    return {} if "--local" in sys.argv else dict(PLANILHAS)
