# coding=utf-8
# Copyright 2014 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (nested_scopes, generators, division, absolute_import, with_statement,
                        print_function, unicode_literals)

from twitter.common.lang import Compatibility

from pants.base.address import SyntheticAddress
from pants.base.build_environment import get_buildroot
from pants.base.payload_field import SourcesField
from pants.base.target import Target


class WikiArtifact(object):
  """Binds a single documentation page to a wiki instance.

  This object allows you to specify which wiki a page should be published to, along with additional
  wiki-specific parameters, such as the title, parent page, etc.
  """

  def __init__(self, wiki, **kwargs):
    """
    :param wiki: target spec of a ``wiki``.
    :param kwargs: a dictionary that may contain configuration directives for your particular wiki.
      For example, the following keys are supported for Atlassian's Confluence:

      * ``space`` -- A wiki space in which to place the page (used in Confluence)
      * ``title`` -- A title for the wiki page
      * ``parent`` -- The title of a wiki page that will denote this page as a child.
    """
    self.wiki = wiki
    self.config = kwargs

  def __hash__(self):
    return hash((self.wiki, self.config))


class Wiki(Target):
  """Target that identifies a wiki where pages can be published."""

  def __init__(self, name, url_builder, **kwargs):
    """
    :param url_builder: Function that accepts a page target and an optional wiki config dict.
    """
    super(Wiki, self).__init__(name, **kwargs)
    self.url_builder = url_builder


class Page(Target):
  """Describes a single documentation page.

  Here is an example, that shows a markdown page providing a wiki page on an Atlassian Confluence
  wiki: ::

     page(name='mypage',
       source='mypage.md',
       provides=[
         wiki_artifact(wiki='address/of/my/wiki/target',
                       space='my_space',
                       title='my_page',
                       parent='my_parent'),
       ],
     )

  A ``page`` can have more than one ``wiki_artifact`` in its ``provides``
  (there might be more than one place to publish it).
  """

  class ProvidesSetField(tuple, PayloadField):


  def __init__(self, source, resources=None, provides=None, **kwargs):
    """
    :param source: Source of the page in markdown format.
    :param resources: An optional list of Resources objects.
    """
    sources_rel_path = sources_rel_path or address.spec_path
    self.payload.add_fields({
      'sources': SourcesField(sources=self.assert_list(sources),
                              sources_rel_path=sources_rel_path),
      'provides': self.ProvidesSetField(provides or []),
    })
    self._resource_specs = resources or []
    super(Page, self).__init__(payload=payload, **kwargs)

    if provides and not isinstance(provides[0], WikiArtifact):
      raise ValueError('Page must provide a wiki_artifact. Found instead: %s' % provides)

  @property
  def source(self):
    return list(self.payload.sources)[0]

  # This callback needs to yield every 'pants(...)' pointer that we need to have resolved into the
  # build graph. This includes wiki objects in the provided WikiArtifact objects, and any 'pants()'
  # pointers inside of the documents themselves (yes, this can happen).
  @property
  def traversable_specs(self):
    if self.payload.provides:
      for wiki_artifact in self.payload.provides:
        yield wiki_artifact.wiki

  @property
  def traversable_dependency_specs(self):
    for spec in super(Page, self).traversable_specs:
      yield spec
    for resource_spec in self._resource_specs:
      yield resource_spec

  # This callback is used to link up the provided WikiArtifact objects to Wiki objects. In the build
  # file, a 'pants(...)' pointer is specified to the Wiki object. In this method, this string
  # pointer is resolved in the build graph, and an actual Wiki object is swapped in place of the
  # string.
  @property
  def provides(self):
    return self.payload.provides
