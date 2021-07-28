"""Top-level package for TreeFuse.

TreeFuse is a library for writing FUSE filesystems backed by treelib trees.

This contains the public API: :py:func:`treefuse_main` is the entrypoint for
CLIs, and :py:class:`TreeFuseStat` is used to specify additional attributes for
nodes which need it.  (See their documentation for details.)
"""

__author__ = """Daniel Watkins"""
__email__ = "daniel@daniel-watkins.co.uk"
__version__ = "1.0.0"

from .treefuse import TreeFuseStat, treefuse_main

__all__ = ["TreeFuseStat", "treefuse_main"]
