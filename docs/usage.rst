=====
Usage
=====

The high-level execution flow a program using TreeFuse is:

* The end user executes the library consumer's CLI
* The CLI constructs a :py:class:`treelib.Tree` representing the FUSE
  filesystem to be mounted
* The CLIT passes that :py:class:`Tree <treelib.Tree>` to
  :py:func:`treefuse_main() <treefuse.treefuse_main>`
* :py:func:`treefuse_main` instantiates a
  :py:class:`treefuse.treefuse.TreeFuseFS` which it uses to

  * parse the FUSE command-line arguments
  * start the background process which mounts and serves the FUSE filesystem
* The CLI exits
* The background process then continues to run, using the logic encoded in
  :py:class:`TreeFuseFS` to serve up the filesystem from the :py:class:`Tree`,
  until the filesystem is unmounted


.. _examples:

Examples
--------

Minimal Example
~~~~~~~~~~~~~~~

This program uses TreeFuse to serve up a single file in the mounted directory::

    import treelib
    from treefuse import treefuse_main

    tree = treelib.Tree()
    root = tree.create_node("root")
    tree.create_node("rootchild", parent=root, data=b"rootchild content\n")

    treefuse_main(tree)

As we can see:

.. code-block:: shell-session

    $ python3 example.py mnt

    $ tree mnt
    mnt
    └── rootchild

    0 directories, 1 file

    $ cat mnt/rootchild
    rootchild content

Filesystem With Directories
~~~~~~~~~~~~~~~~~~~~~~~~~~~

This program uses TreeFuse to serve up a simple filesystem with a single
directory::

    import treelib
    from treefuse import treefuse_main

    tree = treelib.Tree()
    root = tree.create_node("root")
    dir1 = tree.create_node("dir1", parent=root)
    tree.create_node("dirchild", parent=dir1, data=b"dirchild content\n")
    tree.create_node("rootchild", parent=root, data=b"rootchild content\n")

    treefuse_main(tree)

As we can see:

.. code-block:: shell-session

    $ python3 example.py mnt

    $ tree -p mnt
    mnt
    ├── [drwxr-xr-x]  dir1
    │   └── [-r--r--r--]  dirchild
    └── [-r--r--r--]  rootchild

    1 directory, 2 files

    $ cat mnt/rootchild
    rootchild content

    $ cat mnt/dir1/dirchild
    dirchild content


Full Example
~~~~~~~~~~~~

This program uses TreeFuse to serve up the same simple, single-directory
filesystem as above, but demonstrates using :py:class:`treefuse.TreeFuseStat`
to modify the permissions::

    import treelib

    from treefuse import TreeFuseStat, treefuse_main

    tree = treelib.Tree()
    root = tree.create_node("root")
    dir1 = tree.create_node(
        "dir1", parent=root, data=(None, TreeFuseStat.for_directory(mode=0o705))
    )
    tree.create_node("dirchild", parent=dir1, data=b"dirchild content\n")
    tree.create_node(
        "rootchild",
        parent=root,
        data=(b"rootchild content\n", TreeFuseStat.for_file(mode=0o755)),
    )

    treefuse_main(tree)

As we can see, the permissions on the files are different from the previous
example, as we specified:

.. code-block:: shell-session

    $ python3 example.py mnt

    $ tree -p mnt/
    mnt/
    ├── [drwx---r-x]  dir1
    │   └── [-r--r--r--]  dirchild
    └── [-rwxr-xr-x]  rootchild

    1 directory, 2 files
