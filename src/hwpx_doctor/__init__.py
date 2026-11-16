"""hwpx-doctor: integrity checks and safe repairs for generated HWPX documents.

Public API: :func:`check`, :func:`fix`, :data:`RULES`, :class:`Finding`,
:class:`Report`, :class:`FixResult`, :class:`HwpxDoctorError`, :class:`InputError`.
Everything else (``package``, ``xmltree``, ``rules``...) is internal.
"""

from ._version import __version__
from .catalog import RULES, Rule
from .checker import check
from .fixer import fix
from .model import Finding, FixResult, HwpxDoctorError, InputError, Report

__all__ = [
    "RULES",
    "Finding",
    "FixResult",
    "HwpxDoctorError",
    "InputError",
    "Report",
    "Rule",
    "__version__",
    "check",
    "fix",
]
