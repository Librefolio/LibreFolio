"""Signal schemas, one module per theme (CP-9b/9c). The package re-exports nothing: import each class from the module that defines it.

- ``base.py``: the strict model, the decimal and text types, the shared patterns and validators.
- ``vocabulary.py``: the enums.
- ``inputs.py``: price and event points, the input data, source capabilities, execution context, requirements and value sources.
- ``outputs.py``: axes, styles, regions, the output spec and the series.
- ``annotations.py``: the annotation requests and the annotation.
- ``result.py``: warnings, errors, availability, computation, the request, the catalog and the result.
- ``preview.py``: the indicator preview.
"""
