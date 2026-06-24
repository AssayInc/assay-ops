"""Codegen hardening (#140): every generated model must be re-exported by the hand-written
``assayops_contracts/__init__.py`` as that exact class, so a new schema's models can't silently
miss the public top-level exports.

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


def _generated_models() -> list[type[object]]:
    """Model classes (``BaseModel`` / ``Enum``) defined in each ``models/*.py`` module.

    Returns class objects (not names) so the caller can assert identity, not a matching name.
    """
    package_init = models.__file__
    assert package_init is not None, "assayops_contracts.models has no __file__"
    models_dir = Path(package_init).parent

    found: list[type[object]] = []
    for module_path in sorted(models_dir.glob("*.py")):
        if module_path.stem == "__init__":
            continue
        module = importlib.import_module(f"{models.__name__}.{module_path.stem}")
        for _name, obj in inspect.getmembers(module, inspect.isclass):
            # Only classes defined in THIS module -- skip imports (BaseModel, Enum, ConfigDict).
            if obj.__module__ == module.__name__ and issubclass(obj, (BaseModel, Enum)):
                found.append(obj)
    return found


def test_generated_models_are_discovered() -> None:
    # Guard the guard: if discovery finds nothing, the parity assertion would pass vacuously.
    assert _generated_models(), "no models discovered under assayops_contracts.models"


def test_every_generated_model_is_reexported() -> None:
    # Re-exported AS THAT EXACT CLASS (identity, not just a matching name): a missing re-export, a
    # cross-module name collision, or a stale same-name attribute must all fail loudly. __all__ is
    # hand-maintained (datamodel-codegen leaves models/__init__.py empty).
    exported = set(assayops_contracts.__all__)
    problems: list[str] = []
    for obj in _generated_models():
        name = obj.__name__
        if name not in exported:
            problems.append(f"{obj.__module__}.{name}: not in assayops_contracts.__all__")
        elif getattr(assayops_contracts, name, None) is not obj:
            problems.append(f"{obj.__module__}.{name}: re-exported as a different object")
    assert not problems, "re-export parity failures (#140):\n" + "\n".join(problems)
