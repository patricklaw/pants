# coding=utf-8
# Copyright 2014 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (nested_scopes, generators, division, absolute_import, with_statement,
                        print_function, unicode_literals)

import os
import pytest

from pants.base.build_environment import get_buildroot
from pants.util.contextutil import temporary_dir
from pants.util.dirutil import safe_rmtree
from pants_test.pants_run_integration_test import PantsRunIntegrationTest
from pants_test.tasks.test_base import is_exe

def shared_artifacts(version):
  return {'com/pants/testproject/publish/hello-greet/{0}/'.format(version):
          ['ivy-{0}.xml'.format(version),
            'hello-greet-{0}.jar'.format(version),
            'hello-greet-{0}.pom'.format(version),
            'hello-greet-{0}-sources.jar'.format(version)]}

class JarPublishIntegrationTest(PantsRunIntegrationTest):
  SCALADOC = is_exe('scaladoc')
  JAVADOC = is_exe('javadoc')

  # This is where all pushdb properties files will end up.
  @property
  def pushdb_root(self):
    return os.path.join(get_buildroot(), 'testprojects', 'ivy', 'pushdb')

  def setUp(self):
    safe_rmtree(self.pushdb_root)

  def tearDown(self):
    safe_rmtree(self.pushdb_root)

  @pytest.mark.skipif('not JarPublishIntegrationTest.SCALADOC',
                      reason='No scaladoc binary on the PATH.')
  def test_scala_publish(self):
    unique_artifacts = {'com/pants/testproject/publish/jvm-example-lib/0.0.1-SNAPSHOT':
                        ['ivy-0.0.1-SNAPSHOT.xml',
                         'jvm-example-lib-0.0.1-SNAPSHOT.jar',
                         'jvm-example-lib-0.0.1-SNAPSHOT.pom',
                         'jvm-example-lib-0.0.1-SNAPSHOT-sources.jar'],
                        'com/pants/testproject/publish/hello/welcome/0.0.1-SNAPSHOT':
                        ['ivy-0.0.1-SNAPSHOT.xml',
                         'welcome-0.0.1-SNAPSHOT.jar',
                         'welcome-0.0.1-SNAPSHOT.pom',
                         'welcome-0.0.1-SNAPSHOT-sources.jar'],}
    self.publish_test('testprojects/src/scala/com/pants/testproject/publish:jvm-run-example-lib',
                      dict(unique_artifacts.items() + shared_artifacts('0.0.1-SNAPSHOT').items()),
                      ['com.pants.testproject.publish/hello-greet/publish.properties',
                       'com.pants.testproject.publish/jvm-example-lib/publish.properties',
                       'com.pants.testproject.publish.hello/welcome/publish.properties'],
                      extra_options=['--doc-scaladoc-skip'],
                      expected_primary_artifact_count=3)

  @pytest.mark.skipif('not JarPublishIntegrationTest.JAVADOC',
                      reason='No javadoc binary on the PATH.')
  def test_java_publish(self):
    self.publish_test('testprojects/src/java/com/pants/testproject/publish/hello/greet',
                      shared_artifacts('0.0.1-SNAPSHOT'),
                      ['com.pants.testproject.publish/hello-greet/publish.properties'],)

  def test_named_snapshot(self):
    name = "abcdef0123456789"
    self.publish_test('testprojects/src/java/com/pants/testproject/publish/hello/greet',
                      shared_artifacts(name),
                      ['com.pants.testproject.publish/hello-greet/publish.properties'],
                      extra_options=['--publish-named-snapshot=%s' % name])

  def publish_test(self, target, artifacts, pushdb_files, extra_options=None,
                   expected_primary_artifact_count=1):
    """Tests that publishing the given target results in the expected output.

    :param target: Target to test
    :param artifacts: A map from directories to a list of expected filenames
    :param extra_options: Extra options to the pants run
    :param expected_primary_artifact_count: Number of artifacts we expect to be published."""

    with temporary_dir() as publish_dir:
      options = ['--publish-local=%s' % publish_dir,
                 '--no-publish-dryrun',
                 '--publish-force']
      if extra_options:
        options.extend(extra_options)

      yes = 'y' * expected_primary_artifact_count
      pants_run = self.run_pants(['goal', 'publish', target] + options, stdin_data=yes)
      self.assertEquals(pants_run.returncode, self.PANTS_SUCCESS_CODE,
                        "goal publish expected success, got {0}\n"
                        "got stderr:\n{1}\n"
                        "got stdout:\n{2}\n".format(pants_run.returncode,
                                                    pants_run.stderr_data,
                                                    pants_run.stdout_data))

      # New pushdb file should be created for all artifacts.
      for pushdb_file in pushdb_files:
        self.assertTrue(os.path.exists(os.path.join(self.pushdb_root, pushdb_file)))

      for directory, artifact_list in artifacts.items():
        for artifact in artifact_list:
          artifact_path = os.path.join(publish_dir, directory, artifact)
          self.assertTrue(os.path.exists(artifact_path))

