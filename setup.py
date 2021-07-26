#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [
    "fuse-python",
    "treelib",
]

test_requirements = ['pytest>=3', ]

setup(
    author="Daniel Watkins",
    author_email='daniel@daniel-watkins.co.uk',
    python_requires='>=3.6',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    description="TreeFuse creates a FUSE filesystem from a treelib.Tree",
    install_requires=requirements,
    license="GNU General Public License v3",
    long_description=readme + '\n\n' + history,
    include_package_data=True,
    keywords='treefuse',
    name='treefuse',
    packages=find_packages(include=['treefuse', 'treefuse.*']),
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/OddBloke/treefuse',
    version='0.1.0',
    zip_safe=False,
)
