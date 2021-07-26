import errno
import os.path
import stat

import fuse
import treelib
from fuse import Fuse

fuse.fuse_python_api = (0, 2)


class TreeFuseStat(fuse.Stat):
    def __init__(self):
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
    def __init__(self, *args, tree, **kwargs):
        self._tree = tree
        super().__init__(*args, **kwargs)

    def _lookup_path(self, path: str) -> treelib.Node:
        path = path.lstrip(os.path.sep)
        lookups = path.split(os.path.sep) if path else []

        current_node = self._tree.get_node(self._tree.root)
        while lookups:
            next_segment = lookups.pop(0)
            for child_node_id in current_node.successors(self._tree.identifier):
                child_node = self._tree.get_node(child_node_id)
                if child_node.tag == next_segment:
                    current_node = child_node
                    break
            else:
                return None
        return current_node

    def getattr(self, path):
        node = self._lookup_path(path)
        if node is None:
            return -errno.ENOENT

        st = TreeFuseStat()
        if self._tree.children(node.identifier):
            # This is a directory
            st.st_mode = stat.S_IFDIR | 0o755
            st.st_nlink = 2
        else:
            # This is a node
            content = node.data
            st.st_mode = stat.S_IFREG | 0o444
            st.st_nlink = 1
            st.st_size = len(content)
        return st

    def open(self, path, flags):
        node = self._lookup_path(path)
        if node is None:
            return -errno.ENOENT
        accmode = os.O_RDONLY | os.O_WRONLY | os.O_RDWR
        if (flags & accmode) != os.O_RDONLY:
            return -errno.EACCES

    def read(self, path, size, offset):
        node = self._lookup_path(path)
        if node is None:
            return -errno.ENOENT
        if self._tree.children(node.identifier):
            # This is a directory.
            # XXX: Figure out correct return code here
            return -errno.ENOENT
        content = node.data
        slen = len(content)
        if offset < slen:
            if offset + size > slen:
                size = slen - offset
            buf = content[offset : offset + size]
        else:
            buf = b""
        return buf

    def readdir(self, path, offset):
        dir_node = self._lookup_path(path)
        if dir_node is None:
            return -errno.ENOENT
        children = self._tree.children(dir_node.identifier)
        if not children:
            # XXX: Figure out the appropriate return value for "readdir on a non-dir"
            # TODO: Support empty directories.
            return -errno.ENOENT
        dir_entries = [".", ".."]
        for child in children:
            dir_entries.append(child.tag)
        for entry in dir_entries:
            yield fuse.Direntry(entry)


def treefuse_main(tree):
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
