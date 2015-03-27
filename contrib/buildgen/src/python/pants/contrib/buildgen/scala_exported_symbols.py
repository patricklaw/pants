# coding=utf-8
# Copyright 2014 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (absolute_import, division, generators, nested_scopes, print_function,
                        unicode_literals, with_statement)

import os

from pants.backend.jvm.targets.java_tests import JavaTests
from pants.backend.jvm.targets.scala_library import ScalaLibrary
from pants.backend.jvm.tasks.nailgun_task import NailgunTask

from pants.contrib.buildgen.scalac_buildgen_task_mixin import ScalacBuildgenTaskMixin
from pants.contrib.buildgen.source_analysis_task import SourceAnalysisTask


class MapScalaExportedSymbols(NailgunTask, SourceAnalysisTask, ScalacBuildgenTaskMixin):
  """Provides a product mapping source files to the symbols importable from that source."""
  @classmethod
  def analysis_product_name(cls):
    return 'scala_source_to_exported_symbols'

  @property
  def claimed_target_types(self):
    return (ScalaLibrary, JavaTests)

  @property
  def config_section(self):
    return self.options_scope

  @classmethod
  def register_options(cls, register):
    super(MapScalaExportedSymbols, cls).register_options(register)
    cls.register_scalac_buildgen_jvm_tools(register)

  def is_analyzable(self, source):
    return os.path.splitext(source)[1] == '.scala'

  @classmethod
  def prepare(cls, options, round_manager):
    super(MapScalaExportedSymbols, cls).prepare(options, round_manager)
    round_manager.require_data('jvm_build_tools_classpath_callbacks')
    round_manager.require_data('scala')

  def analyze_sources(self, sources):
    return self.map_exported_symbols(sources, self.runjava)
