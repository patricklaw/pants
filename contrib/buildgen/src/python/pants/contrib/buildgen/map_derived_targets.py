# coding=utf-8
# Copyright 2014 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (absolute_import, division, generators, nested_scopes, print_function,
                        unicode_literals, with_statement)

from collections import defaultdict

from pants.backend.core.tasks.task import Task


class MapDerivedTargets(Task):
  """Provides a product mapping concrete targets to all of their synthetic derivatives."""

  @classmethod
  def product_types(cls):
    return [
      'concrete_target_to_derivatives',
    ]

  @classmethod
  def prepare(cls, options, round_manager):
    round_manager.require_data('java')
    round_manager.require_data('scala')

  def execute(self):
    concrete_target_to_derivatives = defaultdict(set)
    for target in self.context.build_graph.targets():
      if target.concrete_derived_from != target:
        concrete_target_to_derivatives[target.concrete_derived_from].add(target)
    products = self.context.products
    products.safe_create_data('concrete_target_to_derivatives',
                              lambda: concrete_target_to_derivatives)
