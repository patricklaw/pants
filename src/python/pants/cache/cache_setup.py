# coding=utf-8
# Copyright 2014 Pants project contributors (see CONTRIBUTORS.md).
# Licensed under the Apache License, Version 2.0 (see LICENSE).

from __future__ import (nested_scopes, generators, division, absolute_import, with_statement,
                        print_function, unicode_literals)

import os
import urlparse

from pants.cache.local_artifact_cache import LocalArtifactCache, TempLocalArtifactCache
from pants.cache.pinger import Pinger
from pants.cache.restful_artifact_cache import RESTfulArtifactCache


def select_best_url(spec, pinger, log):
  urls = spec.split('|')
  if len(urls) == 1:
    return urls[0]  # No need to ping if we only have one option anyway.
  netlocs = map(lambda url: urlparse.urlparse(url)[1], urls)
  pingtimes = pinger.pings(netlocs)  # List of pairs (host, time in ms).
  log.debug('Artifact cache server ping times: %s' %
            ', '.join(['%s: %3f secs' % p for p in pingtimes]))
  argmin = min(xrange(len(pingtimes)), key=lambda i: pingtimes[i][1])
  best_url = urls[argmin]
  if pingtimes[argmin][1] == Pinger.UNREACHABLE:
    return None  # No reachable artifact caches.
  log.debug('Best artifact cache is %s' % best_url)
  return best_url


def create_artifact_cache(log, artifact_root, spec, task_name, compression,
                          action='using', local=None):
  """Returns an artifact cache for the specified spec.

  spec can be:
    - a path to a file-based cache root.
    - a URL of a RESTful cache root.
    - a bar-separated list of URLs, where we'll pick the one with the best ping times.
    - A list or tuple of two specs, local, then remote, each as described above
  """
  if not spec:
    raise ValueError('Empty artifact cache spec')
  if isinstance(spec, basestring):
    if spec.startswith('/') or spec.startswith('~'):
      path = os.path.join(spec, task_name)
      log.info('%s %s local artifact cache at %s' % (task_name, action, path))
      return LocalArtifactCache(artifact_root, path, compression)
    elif spec.startswith('http://') or spec.startswith('https://'):
      # Caches are supposed to be close, and we don't want to waste time pinging on no-op builds.
      # So we ping twice with a short timeout.
      pinger = Pinger(timeout=0.5, tries=2)
      best_url = select_best_url(spec, pinger, log)
      if best_url:
        url = best_url.rstrip('/') + '/' + task_name
        log.info('%s %s remote artifact cache at %s' % (task_name, action, url))
        local = local or TempLocalArtifactCache(artifact_root)
        return RESTfulArtifactCache(artifact_root, url, local)
      else:
        log.warn('%s has no reachable artifact cache in %s.' % (task_name, spec))
        return None
    else:
      raise ValueError('Invalid artifact cache spec: %s' % spec)
  elif isinstance(spec, (list, tuple)) and len(spec) is 1:
    return create_artifact_cache(log, artifact_root, spec[0], task_name, compression, action)
  elif isinstance(spec, (list, tuple)) and len(spec) is 2:
    first = create_artifact_cache(log, artifact_root, spec[0], task_name, compression, action)
    if not isinstance(first, LocalArtifactCache):
      raise ValueError('first of two cache specs must be a local cache path')
    return create_artifact_cache(log, artifact_root, spec[1], task_name, compression, action, first)
  else:
    raise ValueError('Invalid artifact cache spec: %s' % spec)
