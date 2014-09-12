# coding=utf-8
# Copyright 2014 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (nested_scopes, generators, division, absolute_import, with_statement,
                        print_function, unicode_literals)

import logging
import urlparse

import requests
from requests import RequestException

from pants.cache.artifact import TarballArtifact
from pants.cache.artifact_cache import ArtifactCache
from pants.cache.local_artifact_cache import TempLocalArtifactCache
from pants.util.contextutil import  temporary_dir, temporary_file, temporary_file_path

logger = logging.getLogger(__name__)

# Reduce the somewhat verbose logging of requests.
# TODO do this in a central place
logging.getLogger('requests').setLevel(logging.WARNING)

class RequestsSession(object):
  _session = None
  @classmethod
  def instance(cls):
    if cls._session is None:
      cls._session = requests.Session()
    return cls._session

class RESTfulArtifactCache(ArtifactCache):
  """An artifact cache that stores the artifacts on a RESTful service."""

  READ_SIZE_BYTES = 4 * 1024 * 1024

  def __init__(self, artifact_root, url_base, compress=True, local=None):
    """
    url_base: The prefix for urls on some RESTful service. We must be able to PUT and GET to any
              path under this base.
    compress: Whether to compress the artifacts before storing them.
    local: local artifact cache instance to for storing and creating artifacts
           if None, some operations will create one on the fly in a tempdir
    """
    ArtifactCache.__init__(self, artifact_root)
    parsed_url = urlparse.urlparse(url_base)
    if parsed_url.scheme == 'http':
      self._ssl = False
    elif parsed_url.scheme == 'https':
      self._ssl = True
    else:
      raise ValueError('RESTfulArtifactCache only supports HTTP and HTTPS')
    self._timeout_secs = 4.0
    self._netloc = parsed_url.netloc
    self._path_prefix = parsed_url.path.rstrip('/')
    self.compress = compress

    self._localcache = local or TempLocalArtifactCache(self.artifact_root, self.compress)

    if self.compress != self._localcache.compress:
      raise ValueError('RESTfulArtifactCache and Local cache must use same compression settings')

  def try_insert(self, cache_key, paths):
    # Delegate creation of artifact to local cache
    with self._localcache.create_and_insert(cache_key, paths) as tarfile:
      with open(tarfile, 'rb') as infile:
        remote_path = self._remote_path_for_key(cache_key)
        if not self._request('PUT', remote_path, body=infile):
          raise self.CacheError('Failed to PUT to %s. Error: 404' % self._url_string(remote_path))
        return True

  def has(self, cache_key):
    if self._localcache.has(cache_key):
      return True
    return self._request('HEAD', self._remote_path_for_key(cache_key)) is not None

  def use_cached_files(self, cache_key):
    if self._localcache.has(cache_key):
      return self._localcache.use_cached_files(cache_key)

    remote_path = self._remote_path_for_key(cache_key)
    try:
      response = self._request('GET', remote_path)
      if response is not None:
        # Delegate storage and extraction to local cache
        byte_iter = response.iter_content(self.READ_SIZE_BYTES)
        return self._localcache.read_and_extract(cache_key, byte_iter)

    except Exception as e:
      logger.warn('\nError while reading from remote artifact cache: %s\n' % e)

    return False

  def delete(self, cache_key):
    self._localcache.delete(cache_key)
    remote_path = self._remote_path_for_key(cache_key)
    self._request('DELETE', remote_path)

  def prune(self, age_hours):
    self._localcache.prune(age_hours)
    # Doesn't make sense for a client to prune a remote server.
    # Better to run tmpwatch on the server.
    pass

  def _remote_path_for_key(self, cache_key):
    # NB: use id AND hash, since different, but empty targets may have same hash
    return '%s/%s/%s%s' % (self._path_prefix, cache_key.id, cache_key.hash,
                               '.tar.gz' if self.compress else '.tar')

  # Returns a response if we get a 200, None if we get a 404 and raises an exception otherwise.
  def _request(self, method, path, body=None):
    url = self._url_string(path)
    logger.debug('Sending %s request to %s' % (method, url))

    session = RequestsSession.instance()

    try:
      response = None
      if 'PUT' == method:
        response = session.put(url, data=body, timeout=self._timeout_secs)
      elif 'GET' == method:
        response = session.get(url, timeout=self._timeout_secs, stream=True)
      elif 'HEAD' == method:
        response = session.head(url, timeout=self._timeout_secs)
      elif 'DELETE' == method:
        response = session.delete(url, timeout=self._timeout_secs)
      else:
        raise ValueError('Unknown request method %s' % method)

      # Allow all 2XX responses. E.g., nginx returns 201 on PUT. HEAD may return 204.
      if int(response.status_code / 100) == 2:
        return response
      elif response.status_code == 404:
        logger.debug('404 returned for %s request to %s' % (method, self._url_string(path)))
        return None
      else:
        raise self.CacheError('Failed to %s %s. Error: %d %s' % (method, self._url_string(path),
                                                                 response.status_code, response.reason))
    except RequestException as e:
      raise self.CacheError(e)

  def _url_string(self, path):
    return '%s://%s%s' % (('https' if self._ssl else 'http'), self._netloc, path)
