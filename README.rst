========
TreeFuse
========


.. image:: https://img.shields.io/pypi/v/treefuse.svg
        :target: https://pypi.python.org/pypi/treefuse

.. image:: https://img.shields.io/travis/OddBloke/treefuse.svg
        :target: https://travis-ci.com/OddBloke/treefuse

.. image:: https://readthedocs.org/projects/treefuse/badge/?version=latest
        :target: https://treefuse.readthedocs.io/en/latest/?version=latest
        :alt: Documentation Status

TreeFuse is a library for building FUSE filesystem CLIs from treelib Tree
objects.

It wraps python-fuse to provide a CLI entrypoint (`treefuse_main`) which takes
a `tree` parameter and uses that to construct a directory tree and generate
file content within the FUSE filesystem.

Example Program
---------------

Executing this program::

    tree = treelib.Tree()
    root = tree.create_node("root")
    dir1 = tree.create_node("dir1", parent=root)
    tree.create_node("dirchild", parent=dir1, data=b"dirchild content\n")
    tree.create_node("rootchild", parent=root, data=b"rootchild content\n")

    treefuse_main(tree)

With a target directory (e.g. ``python3 example.py mnt``) will mount a
filesystem matching the given tree::

    $ tree mnt
    mnt
    ├── dir1
    │   └── dirchild
    └── rootchild

    1 directory, 2 files

    $ cat mnt/rootchild
    rootchild content

    $ cat mnt/dir1/dirchild
    dirchild content


* Free software: GNU General Public License v3
* Documentation: https://treefuse.readthedocs.io.

Roadmap
-------

For 1.0
~~~~~~~

For a first, minimal, feature complete release, we need:

* All XXX comments have been addressed
* Library consumers can provide ``stat`` values for files and directories
* Usable documentation

Beyond
~~~~~~

* Abstract the interface so that sources other than ``treelib`` can be
  implemented
* Provide a mechanism for library consumers to populate filesystem contents
  asynchronously

Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

This library was written during a hack week at my employer, DigitalOcean.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
