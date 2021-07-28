"""
TreeFuse is a library for writing FUSE filesystems backed by treelib trees.

It wraps python-fuse to provide a CLI entrypoint (`treefuse_main`) which takes
a `tree` parameter and uses that to construct a directory tree and generate
file content within the FUSE filesystem.
"""
import errno
import os.path
import stat
import sys
from dataclasses import dataclass
from typing import Any, Dict, Iterator, Optional, Type, TypeVar, Union

import fuse
import treelib
from fuse import Fuse

fuse.fuse_python_api = (0, 2)

_TFS = TypeVar("_TFS", bound="TreeFuseStat")


class TreeFuseStat(fuse.Stat):
    """An object representing the stat struct for a TreeFuse node.

    This is used both internally, passed into fuse-python's APIs, and as the
    public interface for consumers to specify the stat struct which should
    apply to a given node.

    There are three ways to construct a TreeFuseStat, ordered from most
    preferential:

    * :py:meth:`for_directory` and :py:meth:`for_file` are a consumer-friendly
      APIs, which expose only common parameters
    * :py:meth:`for_directory_stat` and :py:meth:`for_file_stat` are
      lower-level APIs, they take st_* prefixed parameters which are set
      directly in the stat data structure, with reasonable defaults for normal
      operation
    * ``__init__`` is effectively the same interface as ``for_*_stat``, but
      without any defaulting
    """

    _DEFAULT_DIRECTORY_MODE = 0o755
    _DEFAULT_FILE_MODE = 0o444

    # mypy can't infer self.st_size's type, so be explicit
    st_size: Optional[int]

    def ensure_st_size_from(self, content: bytes) -> None:
        """If ``self.st_size`` is not yet set, use ``content`` to set it."""
        if self.st_size is None:
            self.st_size = len(content)

    @classmethod
    def for_directory_stat(
        cls: Type[_TFS],
        st_mode: int = stat.S_IFDIR | _DEFAULT_DIRECTORY_MODE,
        st_nlink: int = 2,
        **kwargs: Any
    ) -> _TFS:
        """Low-level interface to construct a ``TreeFuseStat`` for a directory.

        This lower-level API is used internally, and provided for consumers who
        want to set stat struct values directly.

        Setting these values incorrectly can lead to unexpected and difficult
        to debug errors so, generally, the :py:meth:`for_directory` constructor
        should be preferred.

        Parameters are the same as the fields in ``os.stat_result``:
        https://docs.python.org/3/library/os.html#os.stat_result
        """
        return cls(st_mode=st_mode, st_nlink=st_nlink, **kwargs)

    @classmethod
    def for_directory(
        cls: Type[_TFS], mode: int = _DEFAULT_DIRECTORY_MODE
    ) -> _TFS:
        """Construct a :py:class:`TreeFuseStat` for a directory.

        :param mode:
            The mode to set on this directory (defaults to ``0o755``).
        """
        return cls.for_directory_stat(st_mode=stat.S_IFDIR | mode)

    @classmethod
    def for_file_stat(
        cls: Type[_TFS],
        st_mode: int = stat.S_IFREG | _DEFAULT_FILE_MODE,
        st_nlink: int = 1,
        # st_size defaults to None so ensure_st_size_from can distinguish
        # between consumers not passing a value and passing 0 (the fuse.Stat
        # default)
        st_size: Optional[int] = None,
        **kwargs: Any
    ) -> _TFS:
        """
        Low-level interface to construct a :py:class:`TreeFuseStat` for a file.

        This lower-level API is used internally, and provided for consumers who
        want to set stat struct values directly.

        Setting these values incorrectly can lead to unexpected and difficult
        to debug errors so, generally, the :py:meth:`.for_file` constructor
        should be preferred.

        Parameters are the same as the fields in ``os.stat_result``:
        https://docs.python.org/3/library/os.html#os.stat_result
        """
        return cls(
            st_mode=st_mode, st_nlink=st_nlink, st_size=st_size, **kwargs
        )

    @classmethod
    def for_file(cls: Type[_TFS], mode: int = _DEFAULT_FILE_MODE) -> _TFS:
        """Construct a :py:class:`TreeFuseStat` for a file.

        :param mode:
            The mode to set on this file (defaults to 0o444).
        """
        return cls.for_file_stat(st_mode=stat.S_IFREG | mode)


@dataclass(frozen=True)
class TreeFuseNode:
    _content: Optional[bytes]
    stat: Optional[TreeFuseStat] = None

    @property
    def content(self) -> bytes:
        """Return self._content, or b"" if self._content is None.

        We do this instead of defaulting on initialisation so that we aren't
        throwing away provider input: 'this file has no data' and 'this file's
        data is b""' are not identical inputs.
        """
        return self._content if self._content else b""


class TreelibProvider:
    def __init__(self, tree: treelib.Tree):
        self._tree = tree
        # TreeFuseNode -> treelib node identifier
        self._node_mapping: Dict[TreeFuseNode, str] = {}

    def is_directory(self, node: TreeFuseNode) -> bool:
        treelib_node_identifier = self._node_mapping[node]
        return len(self._tree.children(treelib_node_identifier)) != 0

    def lookup_path(self, path: str) -> Optional[TreeFuseNode]:
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
        treefuse_node = self._unpack_node_data(current_node)
        self._node_mapping[treefuse_node] = current_node.identifier
        return treefuse_node

    def _unpack_node_data(self, node: treelib.Node) -> TreeFuseNode:
        if isinstance(node.data, tuple):
            # We have a (content, stat) tuple.
            return TreeFuseNode(*node.data)
        return TreeFuseNode(node.data)


class TreeFuseFS(Fuse):
    """Implementation of a FUSE filesystem based on a treelib.Tree instance."""

    def __init__(self, *args: Any, provider: TreeFuseProvider, **kwargs: Any):
        self._provider = provider
        super().__init__(*args, **kwargs)

    def getattr(self, path: str) -> Union[TreeFuseStat, int]:
        """Return a TreeFuseStat for the given `path` (or an error code)."""
        node = self._provider.lookup_path(path)
        if node is None:
            return -errno.ENOENT

        content, st = node.content, node.stat

        if self._provider.is_directory(node):
            if st is None:
                st = TreeFuseStat.for_directory_stat()
        else:
            if st is None:
                st = TreeFuseStat.for_file()
            st.ensure_st_size_from(content)
        return st

    def open(self, path: str, flags: int) -> Optional[int]:
        """Perform permission checking for the given `path` and `flags`."""
        # TODO: Distinguish between getting a node object, and checking for path existence
        node = self._provider.lookup_path(path)
        if node is None:
            return -errno.ENOENT
        accmode = os.O_RDONLY | os.O_WRONLY | os.O_RDWR
        if (flags & accmode) != os.O_RDONLY:
            return -errno.EACCES
        return None

    def read(self, path: str, size: int, offset: int) -> Union[int, bytes]:
        """Read `size` bytes from `path`, starting at `offset`."""
        node = self._provider.lookup_path(path)
        if node is None:
            return -errno.ENOENT
        if self._provider.is_directory(node):
            return -errno.EISDIR

        content = node.content
        if not isinstance(content, bytes):
            return -errno.EILSEQ

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
        dir_node = self._provider.lookup_path(path)
        if dir_node is None:
            return -errno.ENOENT
        # XXX
        children = self._provider._tree.children(
            self._provider._node_mapping[dir_node]
        )
        if not children:
            # TODO: Support empty directories.
            return -errno.ENOTDIR
        dir_entries = [".", ".."]
        for child in children:
            dir_entries.append(child.tag)
        for entry in dir_entries:
            yield fuse.Direntry(entry)


def treefuse_main(tree: treelib.Tree) -> None:
    """Parse command-line options to mount a FUSE filesystem for ``tree``.

    The :py:class:`treelib.Tree` instance passed as ``tree`` is interpreted as
    the directory structure that should be presented via FUSE, as follows:

    * Any node without children is interpreted as a file
        * Files have 444 permissions by default
    * Any node with children is interpreted as a directory
        * Directories have 755 permissions by default
        * TreeFuse does not (yet) support empty directories
        * Importantly, this includes the root directory: you must add at least
          one child node (i.e. file) to the root node
    * The ``.data`` attribute provided by :py:class:`treelib.Node`, if set,
      will be read for metadata and content, in one of two ways:
        * If a ``bytes`` instance is set as ``node.data``, it is used as the
          content for file nodes; it is ignored for directory nodes.
        * If a tuple of ``(bytes, TreeFuseStat)`` is set as ``node.data``:
            * The first element is used as the content for file nodes; it is
              ignored for directory nodes.
            * The second element, a :py:class:`TreeFuseStat` instance (or
              something that quacks like one), is used to set the ``stat``
              values (e.g. permissions/mode, owner, group, etc.) on the node:
              see its docs for details.

    .. note::

        In both forms of ``node.data``, file content *must* be specified as
        ``bytes``: users will receive EILSEQ when reading from a file with
        non-``bytes`` content.

    See :ref:`examples` for detailed examples.

    ``treefuse_main`` wraps python-fuse's CLI handling, so the FUSE-specific
    command-line options available to users will depend on the version of
    python-fuse (published on PyPI as ``fuse-python``) which they have
    installed.  See help output for full details.
    """
    if tree.root is None:
        raise Exception("Cannot handle empty Tree objects")
    if len(tree) < 2:
        raise Exception("No support for empty directories, even /")
    usage = (
        f"Mount a {sys.argv[0]} filesystem (powered by TreeFuse)\n"
        + Fuse.fusage
    )
    provider = TreelibProvider(tree)
    server = TreeFuseFS(
        version="%prog " + fuse.__version__,
        usage=usage,
        dash_s_do="setsingle",
        provider=provider,
    )

    server.parse(errex=1)
    server.main()
