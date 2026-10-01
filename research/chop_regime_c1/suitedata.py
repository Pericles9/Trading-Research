"""
Chop regime C1 -- the suite's data encoding, shared by T7 (sizing the embedded sample) and T8 (writing the page).

Every array is a typed array: byte-plane shuffled (the bytes of each element split into planes, which gzip compresses far
better for floats), gzip-compressed, base64. The page decodes with the browser's built-in DecompressionStream (no
library, D14). Decoding is lossless: what the page filters is exactly what the pipeline measured (float32 for measures,
integer codes for labels).
"""
from __future__ import annotations

import base64
import gzip

import numpy as np

DT = {"f4": np.float32, "u1": np.uint8, "u2": np.uint16, "u4": np.uint32, "i4": np.int32}


def encode(a: np.ndarray, dtype: str) -> dict:
    a = np.ascontiguousarray(np.asarray(a).astype(DT[dtype]))
    w = a.dtype.itemsize
    raw = a.view(np.uint8).reshape(-1, w).T.copy().tobytes() if w > 1 else a.tobytes()
    z = gzip.compress(raw, compresslevel=6, mtime=0)
    return {"t": dtype, "n": int(a.size), "b": base64.b64encode(z).decode("ascii")}


def decode(e: dict) -> np.ndarray:
    """Python mirror of the page's decoder (used by the build's round-trip assertion)."""
    raw = gzip.decompress(base64.b64decode(e["b"]))
    dt = np.dtype(DT[e["t"]])
    w = dt.itemsize
    b = np.frombuffer(raw, dtype=np.uint8)
    if w > 1:
        b = b.reshape(w, -1).T.copy()
    return b.reshape(-1).view(dt)[: e["n"]]


def size_of(enc: dict) -> int:
    return sum(len(v["b"]) for v in enc.values())


JS_DECODER = r"""
async function decodeArr(e){
  const bin = await (await fetch('data:application/octet-stream;base64,' + e.b)).arrayBuffer();
  const ds = new DecompressionStream('gzip');
  const raw = new Uint8Array(await new Response(new Blob([bin]).stream().pipeThrough(ds)).arrayBuffer());
  const C = {f4: Float32Array, u1: Uint8Array, u2: Uint16Array, u4: Uint32Array, i4: Int32Array}[e.t];
  const w = C.BYTES_PER_ELEMENT, n = e.n;
  if (w === 1) return new C(raw.buffer, 0, n);
  const out = new Uint8Array(n * w);
  for (let p = 0; p < w; p++) { const off = p * n; for (let i = 0; i < n; i++) out[i * w + p] = raw[off + i]; }
  return new C(out.buffer);
}
async function decodeAll(obj){ const keys = Object.keys(obj); const vals = await Promise.all(keys.map(k => decodeArr(obj[k]))); const r = {}; keys.forEach((k, i) => r[k] = vals[i]); return r; }
"""
