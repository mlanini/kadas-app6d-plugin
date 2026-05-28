# -*- coding: utf-8 -*-
"""Utility functions for the KADAS APP-6(D) plugin."""

import os


def plugin_path(*paths: str) -> str:
    """Return an absolute path relative to the plugin's root directory.

    Example::

        icon = plugin_path("resources", "sketcharmy.svg")
    """
    root = os.path.dirname(os.path.dirname(__file__))
    return os.path.join(root, *paths)


def milsymb_data_dir() -> str:
    """Return (and create) the user data directory for KADAS APP-6(D)."""
    base = os.path.expanduser("~/.kadas/kadas_milsymb")
    os.makedirs(base, exist_ok=True)
    return base
