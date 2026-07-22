"""Executable entry-point scripts for the S&P Index Lab pipeline.

Marks ``scripts`` as a package so modules resolve unambiguously as
``scripts.<name>`` (e.g. ``from scripts import export_frontend_data`` in
tests). Without this, mypy discovers ``scripts/export_frontend_data.py`` under
two module names and aborts. Scripts remain runnable directly
(``python scripts/<name>.py``); this file does not affect that.
"""
