========
TreeFuse
========


.. image:: https://img.shields.io/pypi/v/treefuse.svg
        :target: https://pypi.python.org/pypi/treefuse

.. image:: https://img.shields.io/travis/com/OddBloke/TreeFuse
        :target: https://travis-ci.com/OddBloke/treefuse
        :alt: Travis (.com)

.. image:: https://readthedocs.org/projects/treefuse/badge/?version=latest
        :target: https://treefuse.readthedocs.io/en/latest/?version=latest
        :alt: Documentation Status

.. doc-index-include-start
.. ^ and the corresponding -end below are used to indicate the portion of the
   README which is included in the documentation index

TreeFuse is a library for building FUSE filesystem CLIs from treelib Tree
objects.

It wraps python-fuse to provide a CLI entrypoint (`treefuse_main`) which takes
a `tree` parameter and uses that to construct a directory tree and generate
file content within the FUSE filesystem.

* Free software: GNU General Public License v3
* Documentation: https://treefuse.readthedocs.io.

Example Program
---------------

Executing this program::

    import treelib
    from treefuse import treefuse_main

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

See `Examples <https://treefuse.readthedocs.io/en/latest/usage.html#examples>`_
for more examples.

Roadmap
-------

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

.. doc-index-include-end
