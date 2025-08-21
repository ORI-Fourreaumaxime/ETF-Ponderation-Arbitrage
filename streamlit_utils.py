# -*- coding: utf-8 -*-
"""Utilitaires d'interface pour l'application Streamlit.

Ces helpers permettent d'injecter une feuille de style commune et de
faciliter la création de conteneurs "carte" au style homogène.
"""

from __future__ import annotations

from contextlib import contextmanager
from uuid import uuid4

import streamlit as st


def inject_css() -> None:
    """Charge `css/styles.css` et l'injecte dans la page Streamlit.

    Si le fichier n'est pas trouvé, l'application continue de fonctionner
    sans interrompre l'utilisateur.
    """

    try:
        with open("css/styles.css", "r", encoding="utf-8") as f:
            css = f.read()
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    except OSError:
        # Fichier de style absent : on ignore silencieusement
        pass


def get_border_color(pct: float) -> str:
    """Retourne une couleur de bordure selon la pondération.

    Les seuils sont volontairement simples pour offrir trois niveaux de
    lecture : rouge pour une faible pondération, jaune pour une
    pondération intermédiaire et vert pour une forte pondération.

    Parameters
    ----------
    pct: float
        La pondération (en %).

    Returns
    -------
    str
        Une couleur CSS.
    """

    if pct >= 40:
        return "green"
    if pct >= 20:
        return "gold"
    return "crimson"


@contextmanager
def card(border_color: str) -> None:
    """Conteneur Streamlit avec bordure colorée.

    Streamlit n'autorise pas de laisser une balise HTML ouverte autour des
    widgets. On utilise donc un petit ``div`` marqueur et le sélecteur CSS
    ``:has()`` pour appliquer le style sur le conteneur parent.

    Parameters
    ----------
    border_color: str
        Couleur de la bordure à appliquer.
    """

    marker = uuid4().hex
    container = st.container()
    # Le div "marqueur" est masqué ; il sert uniquement à cibler le parent.
    container.markdown(
        f"""
        <style>
        div:has(> div#{marker}) {{
            border:2px solid {border_color};
            border-radius:8px;
            padding:12px;
            margin:8px 0;
            background-color:#ffffff;
            box-shadow:0 2px 4px rgba(0,0,0,0.1);
        }}
        div#{marker}{{display:none}}
        </style>
        <div id="{marker}"></div>
        """,
        unsafe_allow_html=True,
    )
    with container:
        yield

