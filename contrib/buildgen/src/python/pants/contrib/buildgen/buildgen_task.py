# coding=utf-8
# Copyright 2014 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (absolute_import, division, generators, nested_scopes, print_function,
                        unicode_literals, with_statement)

import sys

import colors
from pants.backend.core.tasks.task import Task
from pants.backend.jvm.targets.jar_library import JarLibrary
from pants.backend.jvm.targets.scala_library import ScalaLibrary
from pants.base.build_file_manipulator import BuildFileManipulator

from pants.contrib.spindle.codegen_task import ScalaRecordLibrary


class BuildgenTask(Task):
  def __init__(self, context, workdir):
    super(BuildgenTask, self).__init__(context, workdir)
    self._target_alias_whitelist = set([
      'java_tests',
      'junit_tests',
      'scala_library',
      'scala_record_library',
      'scalac_plugin',
    ])
    self._dependency_types_managed = (
      JarLibrary,
      ScalaLibrary,
      ScalaRecordLibrary,
    )

  @property
  def dryrun(self):
    return self.get_options().dryrun

  @property
  def config_section(self):
    return 'buildgen'

  @classmethod
  def prepare(cls, options, round_manager):
    round_manager.require_data('scala')
    round_manager.require_data('java')
    round_manager.require_data('java_source_to_exported_symbols')
    round_manager.require_data('scala_source_to_exported_symbols')
    round_manager.require_data('scala_source_to_used_symbols')
    round_manager.require_data('source_to_addresses_mapper')
    round_manager.require_data('concrete_target_to_derivatives')

  def adjust_target_build_file(self, target, computed_dep_addresses):
    """Makes a BuildFileManipulator and adjusts the BUILD file to reflect the computed addresses"""
    manipulator = BuildFileManipulator.load(target.address.build_file,
                                            target.address.target_name,
                                            self._target_alias_whitelist)

    existing_dep_addresses = manipulator._dependencies_by_address.keys()

    for address in existing_dep_addresses:
      if not self.context.build_graph.get_target(address):
        self.context.build_graph.inject_address(address)

    existing_deps = [self.context.build_graph.get_target(address)
                     for address in existing_dep_addresses]
    ignored_deps = [dep for dep in existing_deps
                    if not isinstance(dep, self._dependency_types_managed)]

    manipulator.clear_unforced_dependencies()
    for ignored_dep in ignored_deps:
      manipulator.add_dependency(ignored_dep.address)
    for address in computed_dep_addresses:
      manipulator.add_dependency(address)

    final_dep_addresses = manipulator._dependencies_by_address.keys()

    style_only = set(final_dep_addresses) == set(existing_dep_addresses)

    diff_lines = manipulator.diff_lines()
    if diff_lines:
      if self.dryrun:
        msg = colors.yellow('DRY RUN, would have written this diff:')
      elif self.get_options().stylerun and style_only:
        msg = colors.green('STYLE RUN, about to write this (style only) diff:')
      else:
        msg = colors.blue('REAL RUN, about to write the following diff:')
      sys.stderr.write('\n\n' + msg + '\n')
      sys.stderr.write(colors.yellow('*' * 40 + '\n'))
      sys.stderr.write('target at: ')
      sys.stderr.write(str(target.address) + '\n')
      for line in diff_lines:
        color_fn = lambda x: x
        if line.startswith('+') and not line.startswith('+++'):
          color_fn = colors.green
        elif line.startswith('-') and not line.startswith('---'):
          color_fn = colors.red
        sys.stderr.write(color_fn(line) + '\n')
      sys.stderr.write(colors.yellow('*' * 40 + '\n'))
      if not self.dryrun or (self.get_options().stylerun and style_only):
        with open(manipulator.build_file.full_path, 'w') as f:
          f.write('\n'.join(manipulator.build_file_lines()))

  @property
  def _concrete_target_to_derivatives(self):
    return self.context.products.get_data('concrete_target_to_derivatives')

  def execute(self):
    def task_targets():
      for target in self.context.target_roots:
        if isinstance(target, self.types_operated_on):
          yield target
    targets = sorted(list(task_targets()))
    print('\n{0} will operate on the following targets:'.format(type(self).__name__))
    for target in targets:
      print('* {0}'.format(target.address.reference()))
    for target in targets:
      self.buildgen_target(target)
