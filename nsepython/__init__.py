from .rahu import *

try:
    from importlib.metadata import version as _pkg_version
    __version__ = _pkg_version("nsepython")
except Exception:
    # Not pip-installed (e.g. running straight from a git checkout with no
    # installed dist) -- fall back to the last known release rather than
    # raising PackageNotFoundError and breaking the import for everyone.
    __version__ = "2.101"
