"""
Importação dos dados do processo a partir do texto copiado da tela do sistema (Ctrl+C / Ctrl+V).

Formato esperado (uma informação por linha, a ordem não importa):
  Valor Principal 108.601,00 Data Base 01/07/2025
  Valor Juros 1.234,56 Data Base 01/07/2025        (opcional)
  Valor Selic 35.156,84 Data Base 01/07/2025       (opcional)
  Juros de mora fixados na sentença: Não incidem

- Se um valor aparecer em mais de uma linha (ex.: parcelas), os valores são somados e o app avisa.
- As datas-base precisam ser iguais; se forem diferentes, o app não importa e mostra o erro.
- O texto dos juros de mora vira a OBS-JUROS; se não for reconhecido, o campo fica em branco e o app avisa.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date

from fontes import para_numero

RE_DATA = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})")
RE_VALOR = re.compile(r"-?\d{1,3}(?:\.\d{3})*,\d{2}|-?\d+,\d{2}|-?\d+(?:\.\d+)?")
CAMPOS = {"principal": "Valor Principal", "juros": "Valor Juros", "selic": "Valor Selic"}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip().lower()


def obs_juros_do_texto(txt: str) -> str | None:
    t = _norm(txt)
    if re.search(r"\b1\s*%", t) and not re.search(r"0[,.]5\s*%", t):
        return "1% ao mês"
    if re.search(r"0[,.]5\s*%", t):
        return "0,5% ao mês"
    if "poupanca" in t:
        return "Poupança"
    if "nao incid" in t:
        return "Não incidem"
    return None


def importar_dados(texto: str) -> dict:
    """Retorna {principal, juros, selic, data_base, obs_juros, avisos, erros, reconhecidos}."""
    out = {"principal": None, "juros": None, "selic": None, "data_base": None, "obs_juros": None,
           "avisos": [], "erros": []}
    datas = set()
    contagem = {k: 0 for k in CAMPOS}
    obs_txt = None
    for bruta in texto.splitlines():
        linha = bruta.strip()
        if not linha:
            continue
        n = _norm(linha)
        if n.startswith("juros de mora"):
            obs_txt = linha.split(":", 1)[1].strip() if ":" in linha else linha
            continue
        campo = next((k for k, rot in CAMPOS.items() if n.startswith(_norm(rot))), None)
        if campo is None:
            out["avisos"].append(f"Linha não reconhecida e ignorada: “{linha}”")
            continue
        resto = linha[len(CAMPOS[campo]):]
        m_data = RE_DATA.search(resto)
        antes_data = resto[:m_data.start()] if m_data else resto
        m_val = RE_VALOR.search(antes_data)
        if not m_val:
            out["erros"].append(f"Não achei o valor na linha: “{linha}”")
            continue
        valor = para_numero(m_val.group(0))
        out[campo] = (out[campo] or 0.0) + valor
        contagem[campo] += 1
        if m_data:
            d, m, a = map(int, m_data.groups())
            try:
                datas.add(date(a, m, d))
            except ValueError:
                out["erros"].append(f"Data inválida na linha: “{linha}”")
        else:
            out["avisos"].append(f"Linha sem data-base: “{linha}”")

    for k, n in contagem.items():
        if n > 1:
            out["avisos"].append(f"{CAMPOS[k]} aparece em {n} linhas: os valores foram somados.")
    if out["principal"] is None:
        out["erros"].append("Não encontrei a linha “Valor Principal … Data Base …”.")
    if len(datas) > 1:
        out["erros"].append("As datas-base são diferentes: " +
                            ", ".join(sorted(d.strftime("%d/%m/%Y") for d in datas)) +
                            ". Confira o texto; o app usa uma única data-base.")
    elif datas:
        out["data_base"] = datas.pop()
    else:
        out["erros"].append("Não encontrei a data-base (Data Base dd/mm/aaaa).")
    if obs_txt is None:
        out["avisos"].append("Não encontrei a linha “Juros de mora fixados na sentença: …”. Escolha a OBS-JUROS.")
    else:
        out["obs_juros"] = obs_juros_do_texto(obs_txt)
        if out["obs_juros"] is None:
            out["avisos"].append(f"Juros de mora “{obs_txt}” não corresponde a nenhuma OBS-JUROS "
                                 "(1% ao mês, 0,5% ao mês, Poupança, Não incidem). Escolha manualmente.")
    return out


def brl(v: float | None) -> str:
    if v is None:
        return "0,00"
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
