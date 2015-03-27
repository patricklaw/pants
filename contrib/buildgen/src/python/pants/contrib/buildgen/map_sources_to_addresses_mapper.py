# coding=utf-8
# Copyright 2014 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (absolute_import, division, generators, nested_scopes, print_function,
                        unicode_literals, with_statement)

from pants.backend.core.tasks.task import Task
from pants.base.lazy_source_mapper import LazySourceMapper


class MapSourcesToAddressesMapper(Task):
  """A prefix tree mapping JVM symbols to sources that export that symbol."""

  @classmethod
  def product_types(cls):
    return [
      'source_to_addresses_mapper',
    ]

  @classmethod
  def prepare(cls, options, round_manager):
    round_manager.require_data('scala')
    round_manager.require_data('java')

  def execute(self):
    products = self.context.products
    source_to_addresses_mapper = LazySourceMapper(
      self.context.address_mapper,
      self.context.build_graph,
      stop_after_match=True,
    )
    for target in self.context.build_graph.targets():
      for source in target.sources_relative_to_buildroot():
        source_to_addresses_mapper._source_to_address[source].add(target.address)
    products.safe_create_data('source_to_addresses_mapper',
                              lambda: source_to_addresses_mapper)
