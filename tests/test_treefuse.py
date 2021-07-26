#!/usr/bin/env python

"""Tests for `treefuse` package."""

import multiprocessing
import subprocess
import time
import warnings
from unittest import mock

import psutil
import pytest
import treelib

from treefuse import treefuse, treefuse_main


@pytest.fixture
def mount_tree(tmpdir):
    """Provides a callable which mounts a given treelib.Tree in a tmpdir.

    It handles mounting in a background process, waiting for the mount to
    appear in the filesystem, and unmounting the tmpdir during teardown.

    This uses the `tmpdir` fixture: pytest will provide the same directory to
    consuming tests which request the `tmpdir` fixture.
    """
    process = None

    def _mounter(tree: treelib.Tree) -> None:
        nonlocal process
        # Run treefuse_main in a separate process so we can continue test
        # execution in this one
        process = multiprocessing.Process(target=treefuse_main, args=(tree,))
        with mock.patch("sys.argv", ["_test_", str(tmpdir)]):
            process.start()
        # As FUSE initialisation is happening in the background, we wait until
        # it's mounted before returning control to the test code.
        attempts = 100
        while attempts:
            # all=True to include FUSE filesystems
            partitions = psutil.disk_partitions(all=True)
            if len([p for p in partitions if p.mountpoint == str(tmpdir)]) > 0:
                # We're mounted!
                break
            time.sleep(0.05)
            attempts -= 1
        else:
            raise Exception("FUSE did not appear within 5s")

    try:
        yield _mounter
    finally:
        if process is not None:
            subprocess.check_call(["umount", str(tmpdir)])
            process.join()
        else:
            warnings.warn("mount_tree fixture is a noop if uncalled: remove it?")


def test_basic_tree(mount_tree, tmpdir):
    """Test we can mount a basic tree structure."""
    tree = treelib.Tree()
    root = tree.create_node("root")
    dir1 = tree.create_node("dir1", parent=root)
    tree.create_node("dirchild", parent=dir1, data=b"dirchild content")
    tree.create_node("rootchild", parent=root, data=b"rootchild content")

    mount_tree(tree)

    assert tmpdir.join("rootchild").read() == "rootchild content"
    assert tmpdir.join("dir1", "dirchild").read() == "dirchild content"
