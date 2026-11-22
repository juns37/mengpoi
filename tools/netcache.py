"""Cache hasil DNS (resolver HP sering gagal kalau di-hit paralel)."""
import socket, time
_orig, _cache = socket.getaddrinfo, {}


def _cached(host, port, *a, **k):
    key = (host, port) + a + tuple(sorted(k.items()))
    if key in _cache:
        return _cache[key]
    for n in range(8):
        try:
            res = _orig(host, port, *a, **k)
            res = [r for r in res if r[0] == socket.AF_INET] or res  # prefer IPv4
            _cache[key] = res
            return res
        except socket.gaierror:
            time.sleep(min(2 ** n, 20))
    raise socket.gaierror(f"DNS gagal: {host}")


socket.getaddrinfo = _cached
