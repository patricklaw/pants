# coding=utf-8
# Copyright 2014 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (nested_scopes, generators, division, absolute_import, with_statement,
                        print_function, unicode_literals)

from abc import abstractmethod
from hashlib import sha1

from twitter.common.lang import AbstractClass


class FingerprintStrategy(AbstractClass):
  """A helper object for doing per-task, finer grained invalidation of Targets."""

  @classmethod
  def name(cls):
    """The name of this strategy.

    This will ultimately appear in a human readable form in the fingerprint itself, for debugging
    purposes.
    """
    raise NotImplemented

  @abstractmethod
  def compute_fingerprint(self, target, transitive=False):
    """Subclasses override this method to actually compute the Task specific fingerprint."""

  def __init__(self, fingerprint_cache=None):
    self._fingerprint_cache = fingerprint_cache or {}

  def fingerprint_target(self, target, transitive=False):
    """Consumers of subclass instances call this to get a fingerprint labeled with the name"""
    if (target, transitive) not in self._fingerprint_cache:
      fingerprint = self.compute_fingerprint(target,
                                             transitive=transitive,
                                             fingerprint_cache=fingerprint_cache)
      formatted_fingerprint = '{fingerprint}-{name}'.format(fingerprint=fingerprint,
                                                            name=self.name())
      fingerprint_cache[(target, transitive)] = formatted_fingerprint
    return self._fingerprint_cache[(target, transitive)]


class DefaultFingerprintStrategy(FingerprintStrategy):
  """The default FingerprintStrategy, which delegates to target.payload.invalidation_hash()."""

  @classmethod
  def name(cls):
    return 'default'

  def compute_fingerprint(self, target, transitive=False):
    target_hash = target.payload.invalidation_hash()
    if target_hash is None and not transitive:
      return None

    if not transitive:
      return target_hash
    else:
      dep_hasher = sha1()
      def dep_hash_iter():
        for dep in target.dependencies:
          dep_hash = self.compute_fingerprint(dep, transitive=transitive)
          if dep_hash is not None:
            yield dep_hash
      sorted_dep_hashes = sorted(dep_hash_iter())
      if target_hash is None and not sorted_dep_hashes:
        return None
      for dep_hash in sorted_dep_hashes:
        dep_hasher.update(dep_hash)

      dependencies_hash = dep_hasher.hexdigest()[:12]
      combined_hash = '{target_hash}.{deps_hash}'.format(target_hash=target_hash,
                                                         deps_hash=dependencies_hash)
      return combined_hash
