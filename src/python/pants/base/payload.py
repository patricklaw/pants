# coding=utf-8
# Copyright 2014 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (nested_scopes, generators, division, absolute_import, with_statement,
                        print_function, unicode_literals)

from abc import abstractmethod
import os
from hashlib import sha1

from twitter.common.collections import OrderedSet
from twitter.common.lang import AbstractClass

from pants.base.build_environment import get_buildroot
from pants.base.validation import assert_list


class PayloadFieldAlreadyDefinedError(Exception): pass
class PayloadFrozenError(Exception): pass


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
    self.sources_rel_path = sources_rel_path
    self.sources = assert_list(sources)

  @property
  def num_chunking_units(self):
    return len(self.sources)

  def has_sources(self, extension=''):
    return any(source.endswith(extension) for source in self.sources)

  def sources_relative_to_buildroot(self):
    return [os.path.join(self.sources_rel_path, source) for source in self.sources]

  def _compute_fingerprint(self):
    hasher = sha1()
    hasher.update(self.sources_rel_path)
    for source in sorted(self.sources):
      with open(os.path.join(get_buildroot(), rel_path, source), 'rb') as f:
        hasher.update(source)
        hasher.update(f.read())
    return hasher.hexdigest()


class Payload(object):
  def __init__(self):
    self._fields = {}
    self._frozen = False

  def freeze(self):
    self._frozen = True

  def add_field(self, key, field):
    if key in self._fields:
      raise PayloadFieldAlreadyDefinedError(
        'Key {key} is already set on this payload.'
        ' The existing field was {existing_field}.'
        ' Tried to set new field {field}.'
        .format(key=key, existing_field=self._fields[key], field=field))
    elif self._frozen:
      raise PayloadFrozenError('Payload is frozen, field with name {key} cannot be added to it.'
                               .format(key=key))
    else:
      self._fields[key] = field
      self._fingerprint_memo = None

  _fingerprint_memo = None
  def fingerprint(self):
    if self._fingerprint_memo is None:
      self._fingerprint_memo = self._compute_fingerprint()
    return self._fingerprint_memo

  def _compute_fingerprint(self):
    hasher = sha1()
    for key in sorted(self._fields.keys()):
      field = self._fields[key]
      hasher.update(key)
      hasher.update(field.fingerprint())
    return hasher.hexdigest()

  def __getattr__(self, attr):
    return self._fields[attr]


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


class BundleField(PayloadField):
  def __init__(self, bundles):
    self.bundles = bundles

  def _compute_fingerprint(self):
    hasher = sha1()
    bundle_hashes = [hash_bundle(bundle) for bundle in self.bundles]
    for bundle_hash in sorted(bundle_hashes):
      hasher.update(bundle_hash)
    return hasher.hexdigest()


class ProvidesField(PayloadField):
  def __init__(self, provides):

class JvmTargetPayload(SourcesPayload):
  def __init__(self,
               sources_rel_path=None,
               sources=None,
               provides=None,
               excludes=None,
               configurations=None):
    super(JvmTargetPayload, self).__init__(sources_rel_path, assert_list(sources))
    self.provides = provides
    self.excludes = OrderedSet(excludes)
    self.configurations = OrderedSet(configurations)

  def __hash__(self):
    return hash((self.sources, self.provides, self.excludes, self.configurations))

  def invalidation_hash(self):
    hasher = sha1()
    sources_hash = hash_sources(get_buildroot(), self.sources_rel_path, self.sources)
    hasher.update(sources_hash)
    if self.provides:
      hasher.update(bytes(hash(self.provides)))
    for exclude in sorted(self.excludes):
      hasher.update(bytes(hash(exclude)))
    for config in sorted(self.configurations):
      hasher.update(config)
    return hasher.hexdigest()


class JarLibraryPayload(Payload):
  def __init__(self, jars):
    self.jars = sorted(jars)
    self.excludes = OrderedSet()

  def has_sources(self, extension):
    return False

  def invalidation_hash(self):
    hasher = sha1()
    for jar in self.jars:
      hasher.update(jar.id)
    return hasher.hexdigest()


class JavaProtobufLibraryPayload(JvmTargetPayload):
  def __init__(self, imports, **kwargs):
    super(JavaProtobufLibraryPayload, self).__init__(**kwargs)
    self.imports = imports

  def __hash__(self):
    return hash((self.sources, self.provides, self.excludes, self.configurations))

  def invalidation_hash(self):
    hasher = sha1()
    sources_hash = hash_sources(get_buildroot(), self.sources_rel_path, self.sources)
    hasher.update(sources_hash)
    if self.provides:
      hasher.update(bytes(hash(self.provides)))
    for exclude in sorted(self.excludes):
      hasher.update(bytes(hash(exclude)))
    for config in sorted(self.configurations):
      hasher.update(config)
    for jar in sorted(self.imports):
      hasher.update(bytes(hash(jar)))
    return hasher.hexdigest()


class PythonRequirementLibraryPayload(Payload):
  def __init__(self, requirements):
    self.requirements = set(requirements or [])

  def has_sources(self, extension):
    return False

  def invalidation_hash(self):
    hasher = sha1()
    hasher.update(bytes(hash(tuple(self.requirements))))
    return hasher.hexdigest()
