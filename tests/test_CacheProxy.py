from tests import cmsBuild
import re

from cmsBuild import CacheProxy
from cmsBuild import ArchitectureDecorator

cache = {}
proxy = CacheProxy (cache, ArchitectureDecorator ("slc4_ia32_gcc345"))
proxy["foo"] = "bar"
cache["foo"] = "foobar"

assert (proxy["foo"] == "bar")
assert (cache["foo"] == "foobar")
assert (proxy.has_key ("foo"))
assert (not proxy.has_key ("slc4_ia32_gcc345foo"))
assert (cache.has_key ("foo"))
assert (cache.has_key ("slc4_ia32_gcc345foo"))
