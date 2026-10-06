# -*- coding: utf-8 -*-
"""Bendri keliai abiem build skriptams.

Skriptai gyvena src/, o svetaine - repo saknyje (GitHub Pages skaito is
saknies). Keliai skaiciuojami nuo sio failo, todel skriptus galima paleisti
is bet kurio aplanko.
"""
import os

SRC = os.path.dirname(os.path.abspath(__file__))
SAKNIS = os.path.dirname(SRC)


def saltinis(vardas):
    """Failas src/ aplanke."""
    return os.path.join(SRC, vardas)


def isvestis(*dalys):
    """Failas repo saknyje (ten, kur skaito GitHub Pages)."""
    return os.path.join(SAKNIS, *dalys)
