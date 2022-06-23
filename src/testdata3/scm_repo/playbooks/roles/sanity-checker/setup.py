"""
This repository is not only an ansible role, but also a home of a python module
named `sanity_check`. The reason for that is that I needed to have the same checks
installable as an ansible role, and as a view in [dalite-ng][1]. I decided
not to copy the code, but find the way to share it between the two,
and this was the least bad way do do it.

[1]: https://github.com/open-craft/dalite-ng
"""

from distutils.core import setup


setup(
    name='sanity-checker',
    version='0.1.0',
    py_modules=['sanity_check'],
    package_dir={'': 'files'},
    license='AGPL',
)
