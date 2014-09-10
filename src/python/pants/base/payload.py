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


class PayloadField(AbstractClass):
  _invalidation_hash_memo = None
  def invalidation_hash(self):
    if self._invalidation_hash_memo is None:
      self._invalidation_hash_memo = self.compute_invalidation_hash()
    return self._invalidation_hash_memo

  @abstractmethod
  def compute_invalidation_hash(self):
    pass


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

  def compute_invalidation_hash(self):
    hasher = sha1()
    hasher.update(self.sources_rel_path)
    for source in sorted(self.sources):
      with open(os.path.join(get_buildroot(), rel_path, source), 'rb') as f:
        hasher.update(source)
        hasher.update(f.read())
    return hasher.hexdigest()


class Payload(object):
  def __init__(self, **initial_fields):
    self._fields = {}

  def add_field(self, key, field):
    if key in self._fields:
      raise PayloadFieldAlreadyDefined(
        'Key {key} is already set on this payload.'
        ' The existing field was {existing_field}.'
        ' Tried to set new field {field}.'
        .format(key=key, existing_field=self._fields[key], field=field))
    else:
      self._fields[key] = field

  _invalidation_hash_memo = None
  def invalidation_hash(self):
    if self._invalidation_hash_memo is None:
      self._invalidation_hash_memo = self.compute_invalidation_hash()
    return self._invalidation_hash_memo

  def compute_invalidation_hash(self):
    hasher = sha1()
    for key in sorted(self._fields.keys()):
      field = self._fields[key]
      hasher.update(key)
      hasher.update(field.invalidation_hash())
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


class BundlePayload(Payload):
  def __init__(self, bundles):
    self.bundles = bundles

  def has_sources(self, extension):
    return False

  def invalidation_hash(self):
    hasher = sha1()
    bundle_hashes = [hash_bundle(bundle) for bundle in self.bundles]
    for bundle_hash in sorted(bundle_hashes):
      hasher.update(bundle_hash)
    return hasher.hexdigest()


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


class PythonPayload(SourcesPayload):
  def __init__(self,
               sources_rel_path=None,
               sources=None,
               resources=None,
               requirements=None,
               provides=None,
               compatibility=None):
    super(PythonPayload, self).__init__(sources_rel_path, sources)
    self.resources = list(resources or [])
    self.requirements = requirements
    self.provides = provides
    self.compatibility = compatibility

  def invalidation_hash(self):
    sources_hash = hash_sources(get_buildroot(), self.sources_rel_path, self.sources)
    return sources_hash
    # if self.provides:
    #   hasher.update(bytes(hash(self.provides)))
    # for resource in self.resources:
    #   hasher.update(bytes(hash(resource)))
    # for config in self.configurations:
    #   hasher.update(config)


class ResourcesPayload(SourcesPayload):
  def __init__(self, sources_rel_path=None, sources=None):
    super(ResourcesPayload, self).__init__(sources_rel_path, OrderedSet(sources))

  def invalidation_hash(self):
    return hash_sources(get_buildroot(), self.sources_rel_path, self.sources)


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
