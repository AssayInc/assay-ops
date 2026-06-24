"""Codegen hardening (#140): every generated model must be re-exported by the hand-written
``assayops_contracts/__init__.py``, so a newly added schema's models can't silently miss the
public top-level exports.

The codegen-parity gate regenerates the ``models/`` modules and ``mypy --strict`` typechecks them,
but datamodel-code-generator leaves ``models/__init__.py`` empty, so the top-level re-exports are
hand-maintained. This test makes "forgot to re-export the new model" a failing check rather than a
silent gap -- the same "no hardcoded list that won't follow a new schema" rule as the TS ajv test.
"""

import importlib
import inspect
from enum import Enum
from pathlib import Path

from pydantic import BaseModel

import assayops_contracts
from assayops_contracts import models


def _generated_model_names() -> set[str]:
    """Model classes (``BaseModel`` / ``Enum``) defined in each ``models/*.py`` module.

    Discovered from disk so the set follows the schemas exactly -- the point of the test.
    """
    package_init = models.__file__
    assert package_init is not None, "assayops_contracts.models has no __file__"
    models_dir = Path(package_init).parent

    names: set[str] = set()
    for module_path in sorted(models_dir.glob("*.py")):
        if module_path.stem == "__init__":
            continue
        module = importlib.import_module(f"{models.__name__}.{module_path.stem}")
        for class_name, obj in inspect.getmembers(module, inspect.isclass):
            # Only classes defined in THIS module -- skip imports (BaseModel, Enum, ConfigDict).
            if obj.__module__ == module.__name__ and issubclass(obj, (BaseModel, Enum)):
                names.add(class_name)
    return names


def test_generated_models_are_discovered() -> None:
    # Guard the guard: if discovery finds nothing, the parity assertions would pass vacuously.
    assert _generated_model_names(), "no models discovered under assayops_contracts.models"


def test_every_generated_model_is_reexported() -> None:
    missing = _generated_model_names() - set(assayops_contracts.__all__)
    assert not missing, (
        f"generated models missing from __init__.py + __all__: {sorted(missing)}; "
        "add the import + __all__ entry (codegen hardening, #140)."
    )


def test_reexported_models_are_importable() -> None:
    # An __all__ name must resolve to a real attribute (else `from ... import *` breaks).
    for class_name in _generated_model_names():
        assert hasattr(assayops_contracts, class_name), (
            f"{class_name} is a generated model but is not importable from assayops_contracts"
        )
