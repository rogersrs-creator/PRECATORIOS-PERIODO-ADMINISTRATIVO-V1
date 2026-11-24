"""
SELIC mensal de 01/1996 a 12/2002 (a planilha SELIC do V6 começa em 01/2003).

Fonte primária: Banco Central, SGS 4390 "Taxa de juros - Selic acumulada no mês" (% a.m.),
api.bcb.gov.br/dados/serie/bcdata.sgs.4390, lida em 24/11/2026 (conferida: 01/2003 = 1,97;
02/2003 = 1,83; 03/2003 = 1,78, iguais à planilha do V6).
Começa em 01/1996 porque a SELIC passou a valer na restituição e compensação de tributos federais
a partir de 1º/01/1996 (Lei 9.250/1995, art. 39, § 4º).
Chave: mês da variação (ano, mês), como em motores.base.Serie.
"""
_VALORES = """
1996 2,58 2,35 2,22 2,07 2,01 1,98 1,93 1,97 1,90 1,86 1,80 1,80
1997 1,73 1,67 1,64 1,66 1,58 1,61 1,60 1,59 1,59 1,67 3,04 2,97
1998 2,67 2,13 2,20 1,71 1,63 1,60 1,70 1,48 2,49 2,94 2,63 2,40
1999 2,18 2,38 3,33 2,35 2,02 1,67 1,66 1,57 1,49 1,38 1,39 1,60
2000 1,46 1,45 1,45 1,30 1,49 1,39 1,31 1,41 1,22 1,29 1,22 1,20
2001 1,27 1,02 1,26 1,19 1,34 1,27 1,50 1,60 1,32 1,53 1,39 1,39
2002 1,53 1,25 1,37 1,48 1,41 1,33 1,54 1,44 1,38 1,65 1,54 1,74
"""

SELIC_1996_2002: dict[tuple[int, int], float] = {}
for _linha in _VALORES.strip().splitlines():
    _ano, *_taxas = _linha.split()
    assert len(_taxas) == 12
    for _m, _t in enumerate(_taxas, 1):
        SELIC_1996_2002[(int(_ano), _m)] = float(_t.replace(",", "."))

INICIO_SELIC_TRIBUTARIO = (1996, 1)
