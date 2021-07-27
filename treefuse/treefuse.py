"""
TreeFuse is a library for writing FUSE filesystems backed by treelib trees.

It wraps python-fuse to provide a CLI entrypoint (`treefuse_main`) which takes
a `tree` parameter and uses that to construct a directory tree and generate
file content within the FUSE filesystem.
"""
import errno
import os.path
import stat
from typing import Any, Iterator, Optional, Union

import fuse
import treelib
from fuse import Fuse

fuse.fuse_python_api = (0, 2)


class TreeFuseStat(fuse.Stat):
    def __init__(self) -> None:
        self.st_mode = 0
        self.st_ino = 0
        self.st_dev = 0
        self.st_nlink = 0
        self.st_uid = 0
        self.st_gid = 0
        self.st_size = 0
        self.st_atime = 0
        self.st_mtime = 0
        self.st_ctime = 0


class TreeFuseFS(Fuse):
    """Implementation of a FUSE filesystem based on a treelib.Tree instance."""

    def __init__(self, *args: Any, tree: treelib.Tree, **kwargs: Any):
        self._tree = tree
        super().__init__(*args, **kwargs)

    def _lookup_path(self, path: str) -> Optional[treelib.Node]:
        """Find the node in self._tree corresponding to the given `path`.

        Returns None if the path isn't present."""
        path = path.lstrip(os.path.sep)
        lookups = path.split(os.path.sep) if path else []

        current_node = self._tree.get_node(self._tree.root)
        while lookups:
            next_segment = lookups.pop(0)
            for child_node_id in current_node.successors(
                self._tree.identifier
            ):
                child_node = self._tree.get_node(child_node_id)
                if child_node.tag == next_segment:
                    current_node = child_node
                    break
            else:
                return None
        return current_node

    def _is_directory(self, node: treelib.Node) -> bool:
        return len(self._tree.children(node.identifier)) != 0

    def getattr(self, path: str) -> Union[TreeFuseStat, int]:
        """Return a TreeFuseStat for the given `path` (or an error code)."""
        node = self._lookup_path(path)
        if node is None:
            return -errno.ENOENT

        st = TreeFuseStat()
        if self._is_directory(node):
            st.st_mode = stat.S_IFDIR | 0o755
            st.st_nlink = 2
        else:
            content = node.data
            st.st_mode = stat.S_IFREG | 0o444
            st.st_nlink = 1
            st.st_size = len(content)
        return st

    def open(self, path: str, flags: int) -> Optional[int]:
        """Perform permission checking for the given `path` and `flags`."""
        node = self._lookup_path(path)
        if node is None:
            return -errno.ENOENT
        accmode = os.O_RDONLY | os.O_WRONLY | os.O_RDWR
        if (flags & accmode) != os.O_RDONLY:
            return -errno.EACCES
        return None

    def read(self, path: str, size: int, offset: int) -> Union[int, bytes]:
        """Read `size` bytes from `path`, starting at `offset`."""
        node = self._lookup_path(path)
        if node is None:
            return -errno.ENOENT
        if self._is_directory(node):
            # XXX: Figure out correct return code here
            return -errno.ENOENT
        if not isinstance(node.data, bytes):
            # XXX: Figure out correct return code here
            return -errno.ENODATA
        content = node.data
        slen = len(content)
        if offset < slen:
            if offset + size > slen:
                size = slen - offset
            buf = content[offset:offset + size]
        else:
            buf = b""
        return buf

    def readdir(
        self, path: str, offset: int
    ) -> Union[Iterator[fuse.Direntry], int]:
        """Return `fuse.Direntry`s for the directory at `path`."""
        dir_node = self._lookup_path(path)
        if dir_node is None:
            return -errno.ENOENT
        children = self._tree.children(dir_node.identifier)
        if not children:
            # XXX: Figure out the appropriate return value for a non-dir
            # TODO: Support empty directories.
            return -errno.ENOENT
        dir_entries = [".", ".."]
        for child in children:
            dir_entries.append(child.tag)
        for entry in dir_entries:
            yield fuse.Direntry(entry)


def treefuse_main(tree: treelib.Tree) -> None:
    if tree.root is None:
        raise Exception("Cannot handle empty Tree objects")
    if len(tree) < 2:
        raise Exception("No support for empty directories, even /")
    usage = (
        """
Userspace hello example
"""
        + Fuse.fusage
    )
    server = TreeFuseFS(
        version="%prog " + fuse.__version__,
        usage=usage,
        dash_s_do="setsingle",
        tree=tree,
    )

    server.parse(errex=1)
    server.main()
