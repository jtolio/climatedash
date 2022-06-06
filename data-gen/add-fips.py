#!/usr/bin/env python3

import sys, time, requests

DATASET = "https://geo.fcc.gov/api/census/block/find"
CACHE = "fips-cache.tsv"
SLEEP = 0.1


mem_cache = {}
with open(CACHE) as fh:
    for line in fh:
        lat, lon, fips = map(float, line.rstrip().split("\t"))
        mem_cache[(lat, lon)] = fips


def local_lookup(lat, lon):
    return mem_cache.get((lat, lon), None)


def local_save(lat, lon, fips):
    with open(CACHE, "a") as fh:
        fh.write("\t".join(map(str, [lat, lon, fips])) + "\n")
    mem_cache[(lat, lon)] = fips


def fips(lat, lon):
    val = local_lookup(lat, lon)
    if val is not None:
        return val
    resp = requests.get(
        "%s?latitude=%s&longitude=%s&showall=true&format=json" % (DATASET, lat, lon)
    )
    time.sleep(SLEEP)
    assert 200 <= resp.status_code < 300
    data = resp.json()
    assert data["status"] == "OK", data["statusMessage"]
    val = data["County"]["FIPS"]
    if val == "" or val is None:
        val = float("NaN")
    else:
        val = float(val)
    local_save(lat, lon, val)
    return val


def main():
    tsv = iter(sys.stdin)
    header = next(tsv).rstrip().split("\t")
    col = dict((v, k) for k, v in enumerate(header))
    print("\t".join(header + ["fips"]))

    while True:
        try:
            line = next(tsv).rstrip().split("\t")
        except StopIteration:
            break
        lat, lon = (float(line[col["lat"]]), float(line[col["lon"]]))
        val = fips(lat, lon)
        print("\t".join(line + [str(val)]))


if __name__ == "__main__":
    main()
