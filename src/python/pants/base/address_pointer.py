# coding=utf-8
# Copyright 2014 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (nested_scopes, generators, division, absolute_import, with_statement,
                        print_function, unicode_literals)

from functools import partial

# from peak.util.proxies import LazyProxy


class AddressPointer(object):
  def __init__(self, rel_path, resolve_callback, parse_finished_event):
    self._rel_path = rel_path
    self._resolve_callback = resolve_callback
    self._parse_finished_event = parse_finished_event

  def __call__(self, spec):
    def proxy_callback():
      address = SyntheticAddress(spec, relative_to=self._rel_path)
      if not self._parse_finished_event.is_set():
        raise Exception('Attempted to dereference AddressPointer to {address} before {build_file}'
                        'was finished parsing.'
                        .format(address=address, build_file=self._parse_context.build_file))
      return self._resolve_callback(address)
    return LazyProxy(proxy_callback)
