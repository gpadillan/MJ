"""
Permite hacer: from pagesEIM.deuda import deuda_page
Evita ciclos importando deuda_main solo cuando se llama.
"""
def deuda_page():
    from .. import deuda_main
    return deuda_main.deuda_eim_page()

__all__ = ["deuda_page"]
