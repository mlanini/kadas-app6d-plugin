# -*- coding: utf-8 -*-
"""GUI components – catalog dock, map tool, symbol layer, settings."""

# ======================================================================
# Shared dark-theme stylesheet for KADAS Albireo 2
# ======================================================================
# KADAS uses a dark-blue theme.  Qt widgets default to black text which
# is hard to read.  Rather than changing text colour we give the panel
# container a light background so standard dark text is perfectly legible.

DARK_THEME_SS = """
    QWidget {
        background: #f0f0f0;
        color: #1a1a1a;
    }
    QGroupBox {
        font-weight: bold;
    }
    QTreeWidget::item:selected {
        background: #3399ff;
        color: #ffffff;
    }
"""
