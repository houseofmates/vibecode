from __future__ import absolute_import, unicode_literals

from virtualenv.seed.wheels.util import Wheel
from virtualenv.util.path import Path

BUNDLE_FOLDER = Path('/usr/share/python-wheels')
BUNDLE_SUPPORT = {
    "3.11": {
        "pip": "pip-21.3.1-py3-none-any.whl",
        "setuptools": "setuptools-60.2.0-py3-none-any.whl",
        "wheel": "wheel-0.37.1-py2.py3-none-any.whl",
    },
    "3.10": {
        "pip": "pip-21.3.1-py3-none-any.whl",
        "setuptools": "setuptools-60.2.0-py3-none-any.whl",
        "wheel": "wheel-0.37.1-py2.py3-none-any.whl",
    },
    "3.9": {
        "pip": "pip-21.3.1-py3-none-any.whl",
        "setuptools": "setuptools-60.2.0-py3-none-any.whl",
        "wheel": "wheel-0.37.1-py2.py3-none-any.whl",
    },
    "3.8": {
        "pip": "pip-21.3.1-py3-none-any.whl",
        "setuptools": "setuptools-60.2.0-py3-none-any.whl",
        "wheel": "wheel-0.37.1-py2.py3-none-any.whl",
    },
    "3.7": {
        "pip": "pip-21.3.1-py3-none-any.whl",
        "setuptools": "setuptools-60.2.0-py3-none-any.whl",
        "wheel": "wheel-0.37.1-py2.py3-none-any.whl",
    },
    "3.6": {
        "pip": "pip-21.3.1-py3-none-any.whl",
        "setuptools": "setuptools-59.6.0-py3-none-any.whl",
        "wheel": "wheel-0.37.1-py2.py3-none-any.whl",
    },
    "3.5": {
        "pip": "pip-20.3.4-py2.py3-none-any.whl",
        "setuptools": "setuptools-50.3.2-py3-none-any.whl",
        "wheel": "wheel-0.37.1-py2.py3-none-any.whl",
    },
    "2.7": {
        "pip": "pip-20.3.4-py2.py3-none-any.whl",
        "setuptools": "setuptools-44.1.1-py2.py3-none-any.whl",
        "wheel": "wheel-0.37.1-py2.py3-none-any.whl",
    },
}
MAX = "3.11"


# Debian specific: Update BUNDLE_SUPPORT to match pip wheels shipped in
# /usr/share/python-wheels for base install + pkg_resources.
def list_available_wheels(versions):
    import os
    bundle = {version: {} for version in versions}
    wheel_files = [Wheel.from_path(BUNDLE_FOLDER / fn)
                   for fn in os.listdir(BUNDLE_FOLDER)]
    # Sort wheels so the latest compatible version wins
    wheel_files.sort(key=lambda wheel: wheel.version_tuple)
    for wheel in wheel_files:
        if wheel.distribution in ['pip', 'setuptools', 'wheel']:
            for version in versions:
                if wheel.support_py(version):
                    bundle[version][wheel.distribution] = wheel.name
    return bundle


BUNDLE_SUPPORT = list_available_wheels(BUNDLE_SUPPORT.keys())
# End Debian specific


def get_embed_wheel(distribution, for_py_version):
    # Debian specific: Point at the appropriate wheel package
    wheel = BUNDLE_SUPPORT.get(for_py_version, {}).get(distribution)
    if wheel is None:
        raise Exception((
                "Wheel for {} for Python {} is unavailable. "
                "apt install python{}-{}-whl"
            ).format(
                distribution,
                for_py_version,
                '2' if for_py_version == '2.7' else '3',
                distribution,
            ))

    path = BUNDLE_FOLDER / (BUNDLE_SUPPORT.get(for_py_version, {}) or BUNDLE_SUPPORT[MAX]).get(distribution)
    return Wheel.from_path(path)


__all__ = (
    "get_embed_wheel",
    "BUNDLE_SUPPORT",
    "MAX",
    "BUNDLE_FOLDER",
)
