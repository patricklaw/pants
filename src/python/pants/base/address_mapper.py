# coding=utf-8
# Copyright 2014 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (nested_scopes, generators, division, absolute_import, with_statement,
                        print_function, unicode_literals)

from threading import Event

from pants.base.address import BuildFileAddress, parse_spec
from pants.base.address_pointer import AddressPointer
from pants.base.build_file import BuildFile
from pants.base.build_environment import get_buildroot


class AddressMapper(object):
  class AddressLookupError(Exception): pass

  def __init__(self, build_file_parser):
    self._build_file_parser = build_file_parser
    self._spec_path_to_address_map_map = {}  # {spec_path: {address: addressable}} mapping

  @property
  def root_dir(self):
    return self._build_file_parser._root_dir

  def resolve(self, address):
    address_map = self.address_map_from_spec_path(address.spec_path)
    if address not in address_map:
      raise AddressMapper.AddressLookupError("Failed to resolve address {address}"
                                             .format(address=address))
    else:
      return address_map[address]

  def resolve_spec(self, spec):
    address = SyntheticAddress(spec)
    return self.resolve(address)

  def address_map_from_spec_path(self, spec_path):
    parse_finished_event = Event()
    address_pointer = AddressPointer(rel_path=spec_path,
                                     resolve_callback=self.resolve,
                                     parse_finished_event=parse_finished_event)
    extra_context = {'P': address_pointer}
    address_map = self._build_file_parser.address_map_from_spec_path(spec_path, extra_context)
    self._spec_path_to_address_map_map[spec_path] = address_map
    parse_finished_event.set()
    return address_map

  def addresses_in_spec_path(self, spec_path):
    return self.address_map_from_spec_path(spec_path).keys()

  def spec_to_address(self, spec, relative_to=''):
    spec_path, name = parse_spec(spec, relative_to=relative_to)
    build_file = BuildFile.from_cache(self.root_dir, spec_path)
    return BuildFileAddress(build_file, name)

  def specs_to_addresses(self, specs, relative_to=''):
    for spec in specs:
      yield self.spec_to_address(spec, relative_to=relative_to)

  def scan_addresses(self, root=None):
    addresses = set()
    for build_file in BuildFile.scan_buildfiles(root or get_buildroot()):
      for address in self.addresses_in_spec_path(build_file.spec_path):
        addresses.add(address)
    return addresses

