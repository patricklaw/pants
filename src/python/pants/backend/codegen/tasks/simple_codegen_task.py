# coding=utf-8
# Copyright 2015 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (absolute_import, division, generators, nested_scopes, print_function,
                        unicode_literals, with_statement)

import os

from pants.backend.core.tasks.task import Task
from pants.base.address import SyntheticAddress
from pants.base.build_environment import get_buildroot


class SimpleCodegenTask(Task):
  @classmethod
  def get_fingerprint_strategy(cls):
    return None

  @property
  def synthetic_target_extra_dependencies(self):
    return []

  def execute(self):
    targets = self.codegen_targets()
    with self.invalidated(targets,
                          invalidate_dependents=True,
                          fingerprint_strategy=self.get_fingerprint_strategy()) as invalidation_check:
      for vts in invalidation_check.invalid_vts_partitioned:
        invalid_targets = vts.targets
        self.execute_codegen(invalid_targets)

      invalid_vts_by_target = dict([(vt.target, vt) for vt in invalidation_check.invalid_vts])
      vts_artifactfiles_pairs = []

      for target in targets:
        synthetic_name = target.id
        sources_rel_path = os.path.relpath(self.workdir, get_buildroot())
        spec_path = '{0}{1}'.format(type(self).__name__, sources_rel_path)
        synthetic_address = SyntheticAddress(spec_path, synthetic_name)
        generated_sources = self.sources_generated_by_target(target)
        relative_generated_sources = [os.path.relpath(src, self.workdir)
                                      for src in generated_sources]

        synthetic_target = self.context.add_new_target(
          address=synthetic_address,
          target_type=self.synthetic_target_type,
          dependencies=self.synthetic_target_extra_dependencies,
          sources_rel_path=sources_rel_path,
          sources=relative_generated_sources,
          derived_from=target,
        )

        build_graph = self.context.build_graph

        # NOTE(pl): This bypasses the convenience function (Target.inject_dependency) in order
        # to improve performance.  Note that we can walk the transitive dependee subgraph once
        # for transitive invalidation rather than walking a smaller subgraph for every single
        # dependency injected.
        for dependent_address in build_graph.dependents_of(target.address):
          build_graph.inject_dependency(
            dependent=dependent_address,
            dependency=synthetic_target.address,
          )
        # NOTE(pl): See the above comment.  The same note applies.
        for concrete_dependency_address in build_graph.dependencies_of(target.address):
          build_graph.inject_dependency(
            dependent=synthetic_target.address,
            dependency=concrete_dependency_address,
          )
        build_graph.walk_transitive_dependee_graph(
          build_graph.dependencies_of(target.address),
          work=lambda t: t.mark_transitive_invalidation_hash_dirty(),
        )

        if target in self.context.target_roots:
          self.context.target_roots.append(synthetic_target)
        if target in invalid_vts_by_target:
          vts_artifactfiles_pairs.append((invalid_vts_by_target[target], generated_sources))

      if self.artifact_cache_writes_enabled():
        self.update_artifact_cache(vts_artifactfiles_pairs)

