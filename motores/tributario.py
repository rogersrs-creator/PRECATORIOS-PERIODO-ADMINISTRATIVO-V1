"""Precatórios tributários: a regra do período administrativo será informada depois."""
from motores.base import EmDesenvolvimento

REGRAS = {
    "Nacional": EmDesenvolvimento("Nacional", "Tributário", "Regra tributária a ser informada."),
    "Subnacional": EmDesenvolvimento("Subnacional", "Tributário", "Regra tributária a ser informada."),
}
