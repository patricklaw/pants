# coding=utf-8
# Copyright 2014 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (nested_scopes, generators, division, absolute_import, with_statement,
                        print_function, unicode_literals)

from contextlib import contextmanager
import logging
import os
import shutil
import uuid

from pants.cache.artifact import TarballArtifact
from pants.cache.artifact_cache import ArtifactCache
from pants.util.dirutil import safe_delete, safe_mkdir, safe_mkdir_for
from pants.util.contextutil import temporary_file

logger = logging.getLogger(__name__)

class BaseLocalArtifactCache(ArtifactCache):
  def __init__(self, artifact_root, compress=True):
    ArtifactCache.__init__(self, artifact_root)
    self.compress = compress
    self._cache_root = None

  def _wrap(self, path):
    return TarballArtifact(self.artifact_root, path, self.compress)

  @contextmanager
  def _tmp(self, cache_key, role):
    with temporary_file(suffix=(cache_key.id+role), root_dir=self._cache_root) as tmpfile:
      yield tmpfile

  @contextmanager
  def create_and_insert(self, cache_key, paths):
    with self._tmp(cache_key, 'write') as tmp:
      self._wrap(tmp.name).collect(paths)
      yield self._store(cache_key, tmp.name)

  def read_and_extract(self, cache_key, src):
    with self._tmp(cache_key, 'read') as tmp:
      for chunk in src:
        tmp.write(chunk)
      tmp.close()
      self._wrap(self._store(cache_key, tmp.name)).extract()
      return True

class TempLocalArtifactCache(BaseLocalArtifactCache):
  """A local cache that does not actually store files.

    This implementation does not have a backing _cache_root, and never
    actually stores files between calls.
  """
  def __init__(self, artifact_root, compress=True):
    BaseLocalArtifactCache.__init__(self, artifact_root)
    self.compress = compress
    self._cache_root = None

  def _store(self, cache_key, src):
    return src

  def has(self, cache_key):
    return False

  def use_cached_files(self, cache_key):
    return False

  def delete(self, cache_key):
    pass


class LocalArtifactCache(BaseLocalArtifactCache):
  """An artifact cache that stores the artifacts in local files."""
  def __init__(self, artifact_root, cache_root, compress=True):
    """
    cache_root: The locally cached files are stored under this directory.
    """
    BaseLocalArtifactCache.__init__(self, artifact_root, compress)

    self._cache_root = os.path.expanduser(cache_root)
    safe_mkdir(self._cache_root)

  def has(self, cache_key):
    return os.path.isfile(self._cache_file_for_key(cache_key))

  def _store(self, cache_key, src):
    dest = self._cache_file_for_key(cache_key)
    safe_mkdir_for(dest)
    os.rename(src, dest)
    return dest

  def use_cached_files(self, cache_key):
    try:
      tarfile = self._cache_file_for_key(cache_key)
      if os.path.exists(tarfile):
        self._wrap(tarfile).extract()
        return (cache_key, True)
    except Exception as e:
      logger.warn('Error while reading from local artifact cache: %s' % e)

    return False

  def try_insert(self, cache_key, paths):
    with self.create_and_insert(cache_key, paths) as whatever:
      return True

  def delete(self, cache_key):
    safe_delete(self._cache_file_for_key(cache_key))

  def _cache_file_for_key(self, cache_key):
    # NB: use id AND hash, since different, but empty targets may have same hash
    return os.path.join(self._cache_root, cache_key.id, cache_key.hash) + \
           '.tar.gz' if self.compress else '.tar'
