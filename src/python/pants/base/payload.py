# coding=utf-8
# Copyright 2014 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (nested_scopes, generators, division, absolute_import, with_statement,
                        print_function, unicode_literals)

from abc import abstractmethod
from hashlib import sha1
import os

from twitter.common.collections import OrderedSet
from twitter.common.lang import AbstractClass

from pants.base.build_environment import get_buildroot
from pants.base.validation import assert_list


class PayloadFieldAlreadyDefinedError(Exception): pass


class PayloadFrozenError(Exception): pass


class Payload(object):
  def __init__(self):
    self._fields = {}
    self._frozen = False
    self._fingerprint_memo_map = {}

  def freeze(self):
    self._frozen = True

  def get_field(self, key, default=None):
    return self._fields.get(key, default)

  def add_fields(self, field_dict):
    for key, field in field_dict.items():
      self.add_field(key, field)

  def add_field(self, key, field):
    if key in self._fields:
      raise PayloadFieldAlreadyDefinedError(
        'Key {key} is already set on this payload.'
        ' The existing field was {existing_field}.'
        ' Tried to set new field {field}.'
        .format(key=key, existing_field=self._fields[key], field=field))
    elif self._frozen:
      raise PayloadFrozenError(
        'Payload is frozen, field with key {key} cannot be added to it.'
        .format(key=key))
    else:
      self._fields[key] = field
      self._fingerprint_memo = None

  def fingerprint(self, field_keys=None):
    field_keys = frozenset(field_keys or self._fields.keys())
    if field_keys not in self._fingerprint_memo_map:
      self._fingerprint_memo_map[field_keys] = self._compute_fingerprint(field_keys)
    return self._fingerprint_memo_map[field_keys]

  def _compute_fingerprint(self, field_keys):
    hasher = sha1()
    for key in sorted(field_keys):
      field = self._fields[key]
      hasher.update(key)
      hasher.update(field.fingerprint())
    return hasher.hexdigest()

  def __getattr__(self, attr):
    return self._fields[attr]

