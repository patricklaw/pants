# coding=utf-8
# Copyright 2014 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (nested_scopes, generators, division, absolute_import, with_statement,
                        print_function, unicode_literals)

import os
from textwrap import dedent
import unittest2

import pytest

from pants.backend.core.targets.dependencies import Dependencies
from pants.base.address_mapper import AddressMapper
from pants.base.addressable import Addressable

from pants_test.base_test import BaseTest


class AddressMapperTest(BaseTest):
  def setUp(self):
    super(AddressMapperTest, self).setUp()

  def test_target_addressable(self):
    build_file = self.add_to_build_file('BUILD', dedent(
      '''
      dependencies(
        name = 'foozle'
      )

      name('bar', 'arbitrary object')

      dependencies(
        name = 'baz',
        fake_arg = P(':bar'),
      )
      '''
    ))

    with pytest.raises(AddressMapper.AddressLookupError):
      self.address_mapper.resolve_spec('//:bad_spec')

    dependencies_addressable = self.address_mapper.resolve_spec('//:foozle')
    self.assertEqual(dependencies_addressable.target_type, Dependencies)

    named_str = self.address_mapper.resolve_spec('//:bar')
    self.assertEqual(named_str, 'arbitrary object')

    with_pointer = self.address_mapper.resolve_spec('//:baz')
    self.assertEqual(with_pointer.kwargs['fake_arg'], named_str)

