# coding=utf-8
# Copyright 2014 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (nested_scopes, generators, division, absolute_import, with_statement,
                        print_function, unicode_literals)

from pants.base.target import Target
from pants.base.payload_field import PythonRequirementsField


class PythonRequirementLibrary(Target):
  """Named target for some pip requirements."""
  def __init__(self, requirements=None, *args, **kwargs):
    """
    :param string name: The target name.
    :param requirements: pip requirements
    :type requirements: List of :ref:`python_requirement <bdict_python_requirement>`\s
    """
    self.payload.add_fields({
      'requirements': PythonRequirementsField(requirements or []),
    })
    super(PythonRequirementLibrary, self).__init__(*args, **kwargs)
