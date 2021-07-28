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

import errno
import multiprocessing
import os
import stat
import subprocess
import time
import warnings
from unittest import mock

import psutil
import pytest
import treelib

from treefuse import TreeFuseStat, treefuse_main


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
                cmd = ["umount", str(tmp_path)]
                if os.environ.get("TRAVIS") is not None:
                    # XXX: We see failures umount'ing without sudo on Travis
                    cmd.insert(0, "sudo")
                subprocess.check_call(cmd)
            process.join()
        else:
            warnings.warn(
                "mount_tree fixture is a noop if uncalled: remove it?"
            )


class TestInvalidTrees:
    def test_empty_tree(self, mount_tree):
        tree = treelib.Tree()

        with pytest.raises(Exception):
            mount_tree(tree)

        # We should assert on the Exception content here, but we don't have
        # access to it; see TODOs in module docstring.

    def test_rootonly_tree(self, mount_tree):
        tree = treelib.Tree()
        tree.create_node("root")

        with pytest.raises(Exception):
            mount_tree(tree)

        # We should assert on the Exception content here, but we don't have
        # access to it; see TODOs in module docstring.


class TestValidTreesWithoutStat:
    def test_single_file_tree(self, mount_tree, tmp_path):
        tree = treelib.Tree()
        root = tree.create_node("root")
        tree.create_node("rootchild", parent=root, data=b"rootchild content")

        mount_tree(tree)

        assert (
            tmp_path.joinpath("rootchild").read_text() == "rootchild content"
        )

    def test_no_data_file_tree(self, mount_tree, tmp_path):
        tree = treelib.Tree()
        root = tree.create_node("root")
        tree.create_node("rootchild", parent=root)

        mount_tree(tree)

        assert tmp_path.joinpath("rootchild").read_text() == ""

    def test_basic_tree(self, mount_tree, tmp_path):
        """Test we can mount a basic tree structure."""
        tree = treelib.Tree()
        root = tree.create_node("root")
        dir1 = tree.create_node("dir1", parent=root)
        tree.create_node("dirchild", parent=dir1, data=b"dirchild content")
        tree.create_node("rootchild", parent=root, data=b"rootchild content")

        mount_tree(tree)

        assert tmp_path.is_dir()
        assert tmp_path.joinpath("dir1").is_dir()
        assert (
            tmp_path.joinpath("rootchild").read_text() == "rootchild content"
        )
        assert (
            tmp_path.joinpath("dir1", "dirchild").read_text()
            == "dirchild content"
        )


class TestValidTreesWithStat:
    def test_file_stat(self, mount_tree, tmp_path):
        """Test that we can change the mode of a file."""
        tree = treelib.Tree()
        root = tree.create_node("root")
        tree.create_node(
            "rootchild",
            parent=root,
            data=(b"rootchild content", TreeFuseStat.for_file(mode=0o755)),
        )

        mount_tree(tree)

        rootchild = tmp_path.joinpath("rootchild")
        assert rootchild.read_text() == "rootchild content"
        assert stat.S_IMODE(rootchild.stat().st_mode) == 0o755

    def test_file_only_stat(self, mount_tree, tmp_path):
        """Test that we can change the mode of a file."""
        tree = treelib.Tree()
        root = tree.create_node("root")
        tree.create_node(
            "rootchild",
            parent=root,
            data=(None, TreeFuseStat.for_file(mode=0o755)),
        )

        mount_tree(tree)

        rootchild = tmp_path.joinpath("rootchild")
        assert rootchild.read_text() == ""
        assert stat.S_IMODE(rootchild.stat().st_mode) == 0o755

    def test_directory_stat(self, mount_tree, tmp_path):
        """Test that we can change the mode of a directory."""
        tree = treelib.Tree()
        root = tree.create_node("root")
        dir1 = tree.create_node(
            "dir1",
            parent=root,
            data=(None, TreeFuseStat.for_directory(mode=0o705)),
        )
        tree.create_node("dirchild", parent=dir1, data=b"dirchild content")

        mount_tree(tree)

        dir1_path = tmp_path.joinpath("dir1")
        assert stat.S_IMODE(dir1_path.stat().st_mode) == 0o705


class TestValidTreesWithInvalidNodes:

    def test_file_with_nonbytes_content(self, mount_tree, tmp_path):
        tree = treelib.Tree()
        root = tree.create_node("root")
        tree.create_node("rootchild", parent=root, data="not bytes!")

        mount_tree(tree)

        with pytest.raises(OSError) as exc_info:
            tmp_path.joinpath("rootchild").read_text()

        exception = exc_info.value
        assert errno.EILSEQ == exception.errno
