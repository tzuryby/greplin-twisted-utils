# Copyright 2010 Greplin, Inc.  All Rights Reserved.

"""DNS resolver that uses a short lived local cache to improve performance."""

from greplin import stats
from greplin.defer import lazymap

from twisted.internet import defer, interfaces
from twisted.python.failure import Failure

from zope.interface import implements

import time



class CachingDNS(object):
  """DNS resolver that uses a short lived local cache to improve performance."""
  implements(interfaces.IResolverSimple)


  fetchesStat = stats.IntStat('fetches')

  requestsStat = stats.IntStat('requests')

  countByNameStat = stats.IntDictStat('countByName')


  def __init__(self, original, timeout = 60):
    stats.init(self, '/dns')
    self._original = original
    self._timeout = timeout
    self._cache = lazymap.DeferredMap(self.__fetchHost)


  def __fetchHost(self, args):
    """Actually fetches the host name."""
    self.fetchesStat += 1
    return self._original.getHostByName(*args).addCallback(lambda x: (x, time.time()))


  def getHostByName(self, name, *args):
    """Gets a host by name."""
    self.countByNameStat[name] += 1
    self.requestsStat += 1
    key = (name,) + args
    if key in self._cache:
      # If we failed last time, try again
      if isinstance(self._cache[key], Failure):
        del self._cache[key]
      # Check for a cache hit.
      elif time.time() > self._cache[key][1] + self._timeout:
        # Ensure the item hasn't expired.
        del self._cache[key]
      else:
        # If the item is in cache and not expired, return it immediately.
        return defer.succeed(self._cache[key][0])

    # If it wasn't already in the cache, this always returns a deferred.
    return self._cache[key].addCallback(lambda x: x[0])