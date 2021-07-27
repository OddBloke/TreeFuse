=====
Usage
=====

To use TreeFuse to serve up a basic filesystem::

    import treelib
    from treefuse import treefuse_main

    tree = treelib.Tree()
    root = tree.create_node("root")
    dir1 = tree.create_node("dir1", parent=root)
    tree.create_node("dirchild", parent=dir1, data=b"dirchild content\n")
    tree.create_node("rootchild", parent=root, data=b"rootchild content\n")

    treefuse_main(tree)
