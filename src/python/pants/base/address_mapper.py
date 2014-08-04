# coding=utf-8
# Copyright 2014 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (nested_scopes, generators, division, absolute_import, with_statement,
                        print_function, unicode_literals)

from twitter.common.lang import AbstractClass

from pants.base.address import SyntheticAddress


class AddressMapper(AbstractClass):
  '''Maps addresses in the pants virtual address space to the corresponding objects.

  Subclasses (notably `BuildFileAddressMapper`) look at externally defined resources to
  satisfy calls to `resolve`, mapping an address to some arbitrary object.
  '''

  class AddressLookupError(Exception): pass

  def resolve(self, address):
    '''Maps an address in the virtual address space to an object.'''

  def resolve_spec(self, spec):
    '''Converts a spec to an address and maps it using `resolve`'''
    address = SyntheticAddress.parse(spec)
    return self.resolve(address)

  def address_map_from_spec_path(self, spec_path):
    '''Returns a resolution map of all addresses in a "directory" in the virtual address space.'''

  def addresses_in_spec_path(self, spec_path):
    '''Returns only the addresses gathered by `address_map_from_spec_path`, with no values.'''
    return self.address_map_from_spec_path(spec_path).keys()

  def spec_to_address(self, spec, relative_to=''):
    '''A helper method for mapping a spec to the Address type this mapper works with.'''

  def specs_to_addresses(self, specs, relative_to=''):
    '''The equivalent of `spec_to_address` for a group of specs all relative to the same path.'''
    for spec in specs:
      yield self.spec_to_address(spec, relative_to=relative_to)

  def scan_addresses(self, root=None):
    '''Recursively gathers all addresses visible under `root` of the virtual address space.

    `root` defaults to the root directory of the pants project.
    '''
