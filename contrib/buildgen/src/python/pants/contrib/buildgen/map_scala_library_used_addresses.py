# coding=utf-8
# Copyright 2014 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (absolute_import, division, generators, nested_scopes, print_function,
                        unicode_literals, with_statement)

import sys
from collections import defaultdict
from itertools import chain

import six

from pants.backend.core.tasks.task import Task
from pants.backend.jvm.targets.java_tests import JavaTests
from pants.backend.jvm.targets.scala_library import ScalaLibrary
from pants.base.address import SyntheticAddress


class Default(object):
  """A sentinel key.

  Default indicates that if subtrees don't match the rest of the symbol, the value mapped by
  Default should be used.
  """


class Skip(object):
  """A sentinel value.

  If a symbol maps to Skip, don't map it to anything, but don't consider it an error for the
  symbol to be unmapped.
  """


def check_manually_defined(symbol, subtree):
  """Return the target spec that has been manually curated to be the provider of this symbol.

  This references a manually curated prefix tree mapping symbols to target specs,
  or to the special `Skip` value.  `Default` can be used as a key to indicate that if the current
  subtree does not have a child matching the current symbol part, to take the value pointed at
  by `Default`.
  """
  if subtree == Skip:
    return Skip
  if isinstance(subtree, six.string_types) or subtree is None:
    return subtree

  parts = symbol.split('.')
  if not parts:
    raise ValueError('Came to the end of the symbol while still traversing tree.  Subtree '
                     'keys were {keys}'.format(keys=subtree.keys()))
  if parts[0] not in subtree:
    if Default in subtree:
      return subtree[Default]
    else:
      return None
  else:
    return check_manually_defined('.'.join(parts[1:]), subtree[parts[0]])


class MapScalaLibraryUsedAddresses(Task):
  """Consults the analysis products to map the addresses that all ScalaLibrary targets use.

  This includes synthetic targets that are the result of codegen.
  """

  @classmethod
  def product_types(cls):
    return [
      'scala_library_to_used_addresses',
    ]

  @classmethod
  def prepare(cls, options, round_manager):
    round_manager.require_data('scala_source_to_exported_symbols')
    round_manager.require_data('scala_source_to_used_symbols')
    round_manager.require_data('source_to_addresses_mapper')
    round_manager.require_data('jvm_symbol_to_source_tree')
    round_manager.require_data('scala')
    round_manager.require_data('java')

  def _symbols_used_by_scala_target(self, target):
    """Consults the analysis products and returns a set of all symbols used by a scala target."""
    products = self.context.products
    source_symbols_used_products = products.get_data('scala_source_to_used_symbols')
    used_symbols = set()
    for source in target.sources_relative_to_buildroot():
      if source in source_symbols_used_products:
        analysis = source_symbols_used_products[source]
        used_symbols.update(analysis['imported_symbols'])
        used_symbols.update(analysis['fully_qualified_names'])
    return used_symbols

  @property
  def _internal_symbol_tree(self):
    return self.context.products.get_data('jvm_symbol_to_source_tree')

  @property
  def _source_mapper(self):
    return self.context.products.get_data('source_to_addresses_mapper')

  def _is_test(self, target):
    """A little hack to determine if an address lives in one of the testing directories."""
    prefixes = ('test', 'verification', 'lib/fscommon/test')
    return target.concrete_derived_from.address.spec_path.startswith(prefixes)

  def _manually_defined_spec_to_address(self, spec):
    if '/' in spec:
      return SyntheticAddress.parse(spec)
    else:
      return SyntheticAddress.parse('3rdparty:{0}'.format(spec))

  def _scala_library_used_addresses(self, target):
    """Consults the analysis products to construct a set of addresses a scala library uses."""
    syms = self._symbols_used_by_scala_target(target)
    used_addresses = set()
    errors = []
    for symbol in syms:
      exact_matching_sources = self._internal_symbol_tree.get(symbol, exact=False)
      manually_defined_target = check_manually_defined(symbol)
      if manually_defined_target and exact_matching_sources:
        print(
          'ERROR: buildgen found both sources and manually defined third_party_map'
          ' targets for this symbol.\n'
          'Target: {0}\n'
          'Jvm symbol used by target: {1}\n'
          'Manually defined target for symbol: {3}\n'
          'Sources found defining symbol: \n{2}\n'
          .format(
            target.address.reference(),
            symbol,
            '\n'.join('  * {0}'.format(source) for source in exact_matching_sources),
            self._manually_defined_spec_to_address(manually_defined_target).reference(),
          )
        )
        errors.append((target.address.reference(), symbol))
        continue
      elif exact_matching_sources:
        addresses = set(chain.from_iterable(
          self._source_mapper.target_addresses_for_source(source)
          for source in exact_matching_sources
        ))
      elif manually_defined_target == Skip:
        continue
      elif manually_defined_target:
        addresses = [self._manually_defined_spec_to_address(manually_defined_target)]
      else:
        errors.append((target.address.reference(), symbol))
        continue
      for address in addresses:
        dep = self.context.build_graph.get_target(address)
        if address == target.address:
          pass
        elif self._is_test(dep) and not self._is_test(target):
          pass
        else:
          # In the end, we always actually depend on concrete targets.  But for now we preserve
          # the information that this dependency (could have been) synthetic, and let downstream
          # consumers normalize this to a concrete target if necessary.
          used_addresses.add(dep.address)
    
    if errors:
      print('ERROR: Failed to map these symbols used by the following target to a providing'
            ' target:', file=sys.stderr)
      for spec, symbol in errors:
        print("Symbol:", symbol)
        print("Target:", spec)
        print()
      raise Exception('Failed to map scala libraries to used symbols.  See error output above.')
    return used_addresses

  def execute(self):
    products = self.context.products
    scala_library_to_used_addresses = defaultdict(set)
    def is_scala_lib(t):
      return isinstance(t, (ScalaLibrary, JavaTests))
    for target in self.context.build_graph.targets(is_scala_lib):
      scala_library_to_used_addresses[target].update(self._scala_library_used_addresses(target))
    products.safe_create_data('scala_library_to_used_addresses',
                              lambda: scala_library_to_used_addresses)
