# coding=utf-8
# Copyright 2014 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (nested_scopes, generators, division, absolute_import, with_statement,
                        print_function, unicode_literals)

import logging
import os
import shutil
import uuid

from pants.cache.artifact import TarballArtifact
from pants.cache.artifact_cache import ArtifactCache
from pants.util.dirutil import safe_delete, safe_mkdir, safe_mkdir_for

logger = logging.getLogger(__name__)

class LocalArtifactCache(ArtifactCache):
  """An artifact cache that stores the artifacts in local files."""
  def __init__(self, artifact_root, cache_root, compress=True):
    """
    cache_root: The locally cached files are stored under this directory.
    """
    ArtifactCache.__init__(self, artifact_root)
    self._cache_root = os.path.expanduser(cache_root)
    self._compress = compress

    safe_mkdir(self._cache_root)

  def try_insert(self, cache_key, paths):
    tarfile = self._cache_file_for_key(cache_key)
    safe_mkdir_for(tarfile)
    # Write to a temporary name (on the same filesystem), and move it atomically, so if we
    # crash in the middle we don't leave an incomplete or missing artifact.
    tarfile_tmp = tarfile + '.' + str(uuid.uuid4()) + '.tmp'
    if os.path.exists(tarfile_tmp):
      os.unlink(tarfile_tmp)

    artifact = TarballArtifact(self.artifact_root, tarfile_tmp, self._compress)
    artifact.collect(paths)
    # Note: Race condition here if multiple pants runs (in different workspaces)
    # try to write the same thing at the same time. However since rename is atomic,
    # this should not result in corruption. It may however result in a missing artifact
    # If we crash between the unlink and the rename. But that's OK.
    if os.path.exists(tarfile):
      os.unlink(tarfile)
    os.rename(tarfile_tmp, tarfile)

  def has(self, cache_key):
    return os.path.isfile(self._cache_file_for_key(cache_key))

  def use_cached_files(self, cache_key):
    try:
      tarfile = self._cache_file_for_key(cache_key)
      if os.path.exists(tarfile):
        artifact = TarballArtifact(self.artifact_root, tarfile, self._compress)
        artifact.extract()
        return artifact
      else:
        return None
    except Exception as e:
      logger.warn('Error while reading from local artifact cache: %s' % e)
      return None

  def delete(self, cache_key):
    safe_delete(self._cache_file_for_key(cache_key))

  def prune(self, age_hours):
    pass

  def _cache_file_for_key(self, cache_key):
    # Note: it's important to use the id as well as the hash, because two different targets
    # may have the same hash if both have no sources, but we may still want to differentiate them.
    return os.path.join(self._cache_root, cache_key.id, cache_key.hash) + \
           '.tar.gz' if self._compress else '.tar'
