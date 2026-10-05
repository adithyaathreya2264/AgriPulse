"""
Import a heavy library (pandas, scikit-learn) the first time it is used, not when the server starts.

pandas plus scikit-learn take about 140 MB of memory. Most requests never need them, and a free
512 MB server has little to spare, so they are only loaded once someone asks for a price forecast.
"""

import importlib


class LazyModule:
    def __init__(self, name):
        self._name = name
        self._module = None

    def __getattr__(self, attribute):
        if self._module is None:
            self._module = importlib.import_module(self._name)

        return getattr(self._module, attribute)


def lazy(name):
    return LazyModule(name)
