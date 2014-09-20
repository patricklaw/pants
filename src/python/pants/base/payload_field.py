# coding=utf-8
# Copyright 2014 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (nested_scopes, generators, division, absolute_import, with_statement,
                        print_function, unicode_literals)

from abc import abstractmethod
from hashlib import sha1
import os

import six

from twitter.common.collections import OrderedSet
from twitter.common.lang import AbstractClass

from pants.base.build_environment import get_buildroot
from pants.base.validation import assert_list


class PayloadField(AbstractClass):
  _fingerprint_memo = None
  def fingerprint(self):
    if self._fingerprint_memo is None:
      self._fingerprint_memo = self._compute_fingerprint()
    return self._fingerprint_memo

  @abstractmethod
  def _compute_fingerprint(self):
    pass

  def __hash__(self):
    return hash(self.fingerprint())


class GenericWrapperField(PayloadField):
  def __init__(self, underlying):
    self._underlying = underlying

  def _compute_fingerprint(self):
    return sha1(json.dumps(self._underlying,
                           ensure_ascii=True,
                           allow_nan=False,
                           sort_keys=True)).hexdigest()


class SourcesField(PayloadField):
  def __init__(self, sources_rel_path, sources):
    self.rel_path = sources_rel_path
    self.source_paths = assert_list(sources)

  @property
  def num_chunking_units(self):
    return len(self.source_paths)

  def has_sources(self, extension=''):
    return any(source.endswith(extension) for source in self.source_paths)

  def relative_to_buildroot(self):
    return [os.path.join(self.rel_path, source) for source in self.source_paths]

  def _compute_fingerprint(self):
    hasher = sha1()
    hasher.update(self.rel_path)
    for source in sorted(self.relative_to_buildroot()):
      hasher.update(source)
      with open(os.path.join(get_buildroot(), source), 'rb') as f:
        hasher.update(f.read())
    return hasher.hexdigest()


class PythonRequirementsField(frozenset, PayloadField):
  def _compute_fingerprint(self):
    def fingerprint_iter():
      for req in self:
        hash_items = (
          req._requirement.hashCmp,
          req._repository,
          req._name,
          req._use_2to3,
          hash(req._version_filter.func_code),
          req.compatibility,
        )
        yield sha1(json.dumps(hash_items,
                              ensure_ascii=True,
                              allow_nan=False,
                              sort_keys=True)).hexdigest()
    hasher = sha1()
    for fingerprint in sorted(fingerprint_iter()):
      hasher.update(fingerprint)
    return hasher.hexdigest()


def hash_bundle(bundle):
  hasher = sha1()
  hasher.update(bytes(hash(bundle.mapper)))
  hasher.update(bundle._rel_path)
  for abs_path in sorted(bundle.filemap.keys()):
    buildroot_relative_path = os.path.relpath(abs_path, get_buildroot())
    hasher.update(buildroot_relative_path)
    hasher.update(bundle.filemap[abs_path])
    with open(abs_path, 'rb') as f:
      hasher.update(f.read())
  return hasher.hexdigest()


def combine_hashes(hashes):
  hasher = sha1()
  for h in sorted(hashes):
    hasher.update(h)
  return hasher.hexdigest()


class BundleField(tuple, PayloadField):
  def _compute_fingerprint(self):
    return combine_hashes(map(hash_bundle, self))


class ExcludesField(OrderedSet, PayloadField):
  def _compute_fingerprint(self):
    return combine_hashes(six.binary_type(hash(_) for _ in self))


class ConfigurationsField(OrderedSet, PayloadField):
  def _compute_fingerprint(self):
    return combine_hashes(six.binary_type(hash(_) for _ in self))


class JarsField(tuple, PayloadField):
  def _compute_fingerprint(self):
    return combine_hashes(jar.id for jar in self)

class StringField(six.text_type, PayloadField):
  def _compute_fingerprint(self):
    return combine_hashes(s.encode('utf-8') for s in self)
