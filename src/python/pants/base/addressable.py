# coding=utf-8
# Copyright 2014 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (nested_scopes, generators, division, absolute_import, with_statement,
                        print_function, unicode_literals)

from twitter.common.lang import AbstractClass

from pants.base.address import BuildFileAddress


class NameCallProxy(object):
  def __init__(self, build_file, registration_callback):
    self._build_file = build_file
    self._registration_callback = registration_callback

  def __call__(self, name, obj):
    address = BuildFileAddress(self._build_file, name)
    self._registration_callback(address, obj)
    return obj


class AddressableCallProxy(object):
  def __init__(self, addressable_type, build_file, registration_callback):
    self._addressable_type = addressable_type
    self._build_file = build_file
    self._registration_callback = registration_callback

  def __call__(self, *args, **kwargs):
    addressable = self._addressable_type(*args, **kwargs)
    addressable_name = addressable.addressable_name
    if addressable_name:
      address = BuildFileAddress(self._build_file, addressable_name)
      self._registration_callback(address, addressable)
    return addressable

  def __repr__(self):
    return ('AddressableCallProxy(addressable_type={target_type}, build_file={build_file})'
            .format(target_type=self._addressable_type,
                    build_file=self._build_file))


class Addressable(AbstractClass):
  class AddressableInitError(Exception): pass

  @property
  def addressable_name(self):
    return None

