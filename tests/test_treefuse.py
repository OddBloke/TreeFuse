#!/usr/bin/env python

"""Tests for `treefuse` package."""

import pytest


from treefuse import treefuse


def test_init():
    fs = treefuse.TreeFuseFS(tree=None)
    assert fs is not None
