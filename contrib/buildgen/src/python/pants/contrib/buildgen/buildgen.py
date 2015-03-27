# coding=utf-8
# Copyright 2014 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (absolute_import, division, generators, nested_scopes, print_function,
                        unicode_literals, with_statement)

from subprocess import check_output

from pants.backend.core.tasks.task import Task
from pants.base.build_environment import get_buildroot
from pants.base.build_file import BuildFile
from pants.base.cmd_line_spec_parser import CmdLineSpecParser


class Buildgen(Task):
  @classmethod
  def register_options(cls, register):
    super(Buildgen, cls).register_options(register)
    register(
      "--dryrun",
      default=False,
      action="store_true",
      help="Displays diff without writing.",
    )

    register(
      "--stylerun",
      default=False,
      action="store_true",
      help="Only writes out changes that are style-only (deps remain the same).",
    )

    register(
      '--diffspec',
      default=None,
      action='store',
      help='git diffspecs for commits to read modified files from.',
    )

  @classmethod
  def alternate_target_roots(cls, options, address_mapper, build_graph):
    # NOTE(pl): This hack allows us to avoid sprinkling dummy tasks into every goal that we
    # need to be sure has its target roots modified.
    spec_parser = CmdLineSpecParser(
      get_buildroot(),
      address_mapper,
      spec_excludes=options.spec_excludes,
      exclude_target_regexps=options.exclude_target_regexp,
    )
    targets_required_downstream = set()
    source_dirs = [
      '3rdparty::',
      'lib::',
      'src::',
      'test::',
      'verification::',
    ]
    for address in spec_parser.parse_addresses(source_dirs):
      build_graph.inject_address_closure(address)
      targets_required_downstream.add(build_graph.get_target(address))
    return targets_required_downstream

  def targets_from_scm(self):
    diffspec = self.get_options().diffspec
    changed_sources = []
    if diffspec:
      git_diff_cmd = [
        'git',
        'diff-tree',
        '--no-commit-id',
        '--name-only',
        '-r',
        diffspec,
      ]
    else:
      untracked_cmd = [
        'git',
        'ls-files',
        '--other',
        '--exclude-standard',
      ]
      changed_sources.extend(filter(None, [l.strip() for l in check_output(untracked_cmd).split()]))
      git_merge_base_cmd = [
        'git',
        'merge-base',
        'HEAD',
        'origin/master',
      ]
      merge_base = check_output(git_merge_base_cmd).strip()
      git_diff_cmd = [
        'git',
        'diff',
        '--name-only',
        merge_base,
      ]
    changed_sources.extend(filter(None, [l.strip() for l in check_output(git_diff_cmd).split()]))
    source_mapper = self.context.products.get_data('source_to_addresses_mapper')
    global_options = self.context.options.for_global_scope()
    spec_parser = CmdLineSpecParser(
      get_buildroot(),
      self.context.address_mapper,
      spec_excludes=global_options.spec_excludes,
      exclude_target_regexps=global_options.exclude_target_regexp,
    )
    for candidate_source in changed_sources:
      try:
        addresses = source_mapper.target_addresses_for_source(candidate_source)
        for address in addresses:
          yield self.context.build_graph.get_target(address)
      except ValueError:
        # No target owned this changed source.  That's okay.  But maybe it's a BUILD file.
        try:
          candidate_build_file = BuildFile.from_cache(
            get_buildroot(),
            candidate_source,
          )
          if candidate_build_file.exists():
            # If this was a BUILD file, we conservatively assume that any target defined in it
            # might have been changed.
            all_owned_targets_spec = '{0}:'.format(candidate_build_file.spec_path)
            for address in spec_parser.parse_addresses(all_owned_targets_spec):
              yield self.context.build_graph.get_target(address)
        except BuildFile.MissingBuildFileError as e:
          # This wasn't a BUILD file.  That's fine.
          pass

  def execute(self):
    # NOTE(pl): We now rely on the fact that we've scheduled Buildgen (the dummy task in the
    # buildgen goal) to run before the real buildgen tasks, e.g. buildgen-scala, buildgen-thrift,
    # etc.  Since we are being run before the real tasks but after everything else upstream,
    # we can fix the target roots back up to be whatever the buildgen tasks are supposed to
    # operate on (instead of the entire build graph, which the upstream operated on).
    build_graph = self.context.build_graph
    bg_target_roots = set()
    global_options = self.context.options.for_global_scope()
    if self.context.options._target_specs:
      spec_parser = CmdLineSpecParser(
        get_buildroot(),
        self.context.address_mapper,
        spec_excludes=global_options.spec_excludes,
        exclude_target_regexps=global_options.exclude_target_regexp,
      )
      for spec in self.context.options._target_specs:
        for address in spec_parser.parse_addresses(spec):
          build_graph.inject_address_closure(address)
          bg_target_roots.add(build_graph.get_target(address))
    else:
      bg_target_roots.update(
        target for target in
        build_graph.transitive_dependees_of_addresses(t.address for t in self.targets_from_scm())
        if target.is_original
      )
    self.context._replace_targets(list(bg_target_roots))
