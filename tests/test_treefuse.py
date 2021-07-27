#!/usr/bin/env python

"""Tests for `treefuse` package.

This file contains integration tests: the ``mount_tree`` fixture provides a
callable which will mount a given Tree into a temporary directory, before
passing control back to the requesting test.

python-fuse causes the mounting process to exit, so we use a
multiprocessing.Process to perform the mount itself.

TODO:
* Fully investigate how to stop python-fuse from exiting the test process, to
  obviate the need for multiprocessing.  (I've already tried patching sys.exit
  and catching SystemExit exceptions.)
* Feed exceptions/stdout/stderr from the mounting Process back to the test
  executing process, so tests (e.g. ``test_empty_tree``) can assert on mounting
  failures with more granularity.
"""

import multiprocessing
import subprocess
import time
import warnings
from unittest import mock

import psutil
import pytest
import treelib

from treefuse import treefuse_main


@pytest.fixture
def mount_tree(tmp_path):
    """Provides a callable which mounts a given treelib.Tree in a tempdir.

    It handles mounting in a background process, waiting for the mount to
    appear in the filesystem, and unmounting the tmpdir during teardown.

    This uses the `tmp_path` fixture: pytest will provide the same directory to
    consuming tests which request the `tmp_path` fixture.
    """
    process = None
    skip_umount = False

    def _mounter(tree: treelib.Tree) -> None:
        nonlocal process, skip_umount
        # Run treefuse_main in a separate process so we can continue test
        # execution in this one
        process = multiprocessing.Process(target=treefuse_main, args=(tree,))
        with mock.patch("sys.argv", ["_test_", str(tmp_path)]):
            process.start()
        # As FUSE initialisation is happening in the background, we wait until
        # it's mounted before returning control to the test code.  The FUSE
        # process we execute is only alive while the mounting is happening;
        # wait for it to exit, then check if the mount was successful.
        attempts = 100
        while attempts:
            if not process.is_alive():
                # We're mounted!
                break
            time.sleep(0.05)
            attempts -= 1
        else:
            raise Exception("FUSE process did not exit within 5s")

        # all=True to include FUSE filesystems
        partitions = psutil.disk_partitions(all=True)
        if not len([p for p in partitions if p.mountpoint == str(tmp_path)]):
            process.join()
            skip_umount = True
            raise Exception("FUSE process exited, but mount did not occur")

    try:
        yield _mounter
    finally:
        if process is not None:
            if not skip_umount:
                subprocess.check_call(["umount", str(tmp_path)])
            process.join()
        else:
            warnings.warn(
                "mount_tree fixture is a noop if uncalled: remove it?"
            )


def test_empty_tree(mount_tree):
    tree = treelib.Tree()

    with pytest.raises(Exception):
        mount_tree(tree)

    # We should assert on the Exception content here, but we don't have access
    # to it; see TODOs in module docstring.


def test_rootonly_tree(mount_tree):
    tree = treelib.Tree()
    tree.create_node("root")

    with pytest.raises(Exception):
        mount_tree(tree)

    # We should assert on the Exception content here, but we don't have access
    # to it; see TODOs in module docstring.


def test_single_file_tree(mount_tree, tmp_path):
    tree = treelib.Tree()
    root = tree.create_node("root")
    tree.create_node("rootchild", parent=root, data=b"rootchild content")

    mount_tree(tree)

    assert tmp_path.joinpath("rootchild").read_text() == "rootchild content"


def test_basic_tree(mount_tree, tmp_path):
    """Test we can mount a basic tree structure."""
    tree = treelib.Tree()
    root = tree.create_node("root")
    dir1 = tree.create_node("dir1", parent=root)
    tree.create_node("dirchild", parent=dir1, data=b"dirchild content")
    tree.create_node("rootchild", parent=root, data=b"rootchild content")

    mount_tree(tree)

    assert tmp_path.joinpath("rootchild").read_text() == "rootchild content"
    assert (
        tmp_path.joinpath("dir1", "dirchild").read_text() == "dirchild content"
    )
