# coding=utf-8
# Copyright 2014 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (absolute_import, division, generators, nested_scopes, print_function,
                        unicode_literals, with_statement)

import os
from collections import defaultdict
from os import path as P

from pants.backend.core.tasks.task import Task
from pants.backend.jvm.targets.java_library import JavaLibrary
from pants.base.build_environment import get_buildroot
from pants.base.source_root import SourceRoot


class MapJavaExportedSymbols(Task):
  """A naive map of java sources to the symbols they export.

    We just assume that each java source file represents a single symbol
    defined by the directory structure (from the source root) and terminating in the name of the
    file with '.java' stripped off.
    """

  @classmethod
  def product_types(cls):
    return [
      'java_source_to_exported_symbols',
    ]

  @classmethod
  def prepare(cls, options, round_manager):
    round_manager.require_data('java')

  def execute(self):
    java_source_to_exported_symbols = defaultdict(set)
    source_roots = set(SourceRoot.all_roots().keys())
    for source_root in source_roots:
      abs_source_root = P.join(get_buildroot(), source_root)
      for root, _, files in os.walk(abs_source_root):
        buildroot_relative_dir = P.relpath(root, get_buildroot())
        source_root_relative_dir = P.relpath(root, abs_source_root)
        for source_candidate in files:
          if P.splitext(source_candidate)[1] == '.java':
            source_path = P.join(buildroot_relative_dir, source_candidate)
            terminal_symbol = source_candidate[:-len('.java')]
            # for src/jvm/StartJetty.java, the only unqualified symbol in our codebase
            if source_root_relative_dir == '.':
              fq_symbol = terminal_symbol
            else:
              prefix_symbol = source_root_relative_dir.replace('/', '.')
              fq_symbol = '.'.join([prefix_symbol, terminal_symbol])
            java_source_to_exported_symbols[source_path].update([fq_symbol])

    def is_synthetic_java_lib(t):
      return isinstance(t, JavaLibrary) and t.concrete_derived_from.address != t.address

    # We map java targets produced by codegen since they don't necessarily have an
    # explicit source root.  However I think that source roots are supposed to be
    # added by synthetic target creation, so this seems off to me.
    for synthetic_target in self.context.build_graph.targets(is_synthetic_java_lib):
      for source_candidate in synthetic_target.sources_relative_to_source_root():
        source_root_relative_dir = P.dirname(source_candidate)
        if P.splitext(source_candidate)[1] == '.java':
          terminal_symbol = source_candidate[:-len('.java')]
          if source_root_relative_dir == '.':
            fq_symbol = terminal_symbol
          else:
            prefix_symbol = source_root_relative_dir.replace('/', '.')
            fq_symbol = '.'.join([prefix_symbol, terminal_symbol])
          source_relative_to_buildroot = P.join(synthetic_target.target_base, source_candidate)
          java_source_to_exported_symbols[source_relative_to_buildroot].update([fq_symbol])

    products = self.context.products
    products.safe_create_data('java_source_to_exported_symbols',
                              lambda: java_source_to_exported_symbols)
