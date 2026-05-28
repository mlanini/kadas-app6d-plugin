# -*- coding: utf-8 -*-
"""
Entry point for the KADAS APP-6(D) plugin.

This file is loaded by KADAS/QGIS. The only required symbol is
``classFactory``, which must return an instance of the plugin class.
"""

import os

from qgis.PyQt.QtCore import QCoreApplication, QTranslator


def classFactory(iface):  # noqa: N802
    """Instantiate the plugin.

    :param iface: A QgisInterface instance provided by the host application.
    :returns: An instance of the plugin class.
    """
    # ------------------------------------------------------------------
    # Install translation (if available)
    # ------------------------------------------------------------------
    try:
        from qgis.core import QgsApplication

        locale = QgsApplication.locale()
    except Exception:
        locale = ""

    i18n_dir = os.path.join(os.path.dirname(__file__), "i18n")
    candidates = [locale, locale.split("_")[0]] if locale else []
    for candidate in candidates:
        translation_path = os.path.join(i18n_dir, f"kadas_milsymb_{candidate}.qm")
        if os.path.exists(translation_path):
            translator = QTranslator()
            if translator.load(translation_path):
                QCoreApplication.installTranslator(translator)
            break

    from .plugin import KadasApp6Plugin  # noqa: PLC0415

    return KadasApp6Plugin(iface)
