# coding=utf-8
# Copyright 2014 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (nested_scopes, generators, division, absolute_import, with_statement,
                        print_function, unicode_literals)

from pants.cache.artifact_cache import ArtifactCache

class CombinedArtifactCache(ArtifactCache):
  """An artifact cache that delegates to a list of other caches."""
  def __init__(self, artifact_caches):
    """We delegate to artifact_caches, a list of ArtifactCache instances, in order."""
    if not artifact_caches:
      raise ValueError('Must provide at least one underlying artifact cache')
    artifact_root = artifact_caches[0].artifact_root
    if any(x.artifact_root != artifact_root for x in artifact_caches):
      raise ValueError('Combined artifact caches must all have the same artifact root.')
    ArtifactCache.__init__(self, artifact_root)
    self._artifact_caches = artifact_caches

  def insert(self, cache_key, paths):
    for cache in self._artifact_caches:  # Insert into all.
      cache.insert(cache_key, paths)

  def has(self, cache_key):
    return any(cache.has(cache_key) for cache in self._artifact_caches)

  def use_cached_files(self, cache_key):
    for cache in self._artifact_caches:
      artifact = cache.use_cached_files(cache_key)
      if artifact:
        return artifact
    return None

  def delete(self, cache_key):
    for cache in self._artifact_caches:  # Delete from all.
      cache.delete(cache_key)
