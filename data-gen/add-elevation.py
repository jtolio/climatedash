#!/usr/bin/env python3

import sys, time, requests

BATCH_SIZE = 80
DATASET = "https://api.opentopodata.org/v1/aster30m"
CACHE = "elevation-cache.tsv"
SLEEP = 2.5

mem_cache = {}
with open(CACHE) as fh:
    for line in fh:
        lat, lon, elevation = map(float, line.rstrip().split("\t"))
        mem_cache[(lat, lon)] = elevation


def local_lookup(lat, lon):
    return mem_cache.get((lat, lon), None)


def local_save(lat, lon, elevation):
    with open(CACHE, "a") as fh:
        fh.write("\t".join(map(str, [lat, lon, elevation])) + "\n")
    mem_cache[(lat, lon)] = elevation


def elevations(locs):
    results = {}
    query = []
    for loc in locs:
        val = local_lookup(*loc)
        if val is None:
            query.append(loc)
        else:
            results[loc] = val
    if len(query) > 0:
        resp = requests.get(
            "%s?locations=%s"
            % (DATASET, "|".join("%s,%s" % (lat, lon) for (lat, lon) in query))
        )
        time.sleep(SLEEP)
        assert 200 <= resp.status_code < 300
        data = resp.json()
        for subdata in data["results"]:
            loc = (subdata["location"]["lat"], subdata["location"]["lng"])
            val = subdata["elevation"]
            if val is None:
                val = float("NaN")
            results[loc] = val
            local_save(*loc, val)
    return [results[loc] for loc in locs]


def process_batch(col, batch):
    vals = elevations(
        [(float(line[col["lat"]]), float(line[col["lon"]])) for line in batch]
    )
    for line, elevation in zip(batch, vals):
        print("\t".join(line + [str(elevation)]))


def main():
    tsv = iter(sys.stdin)
    header = next(tsv).rstrip().split("\t")
    col = dict((v, k) for k, v in enumerate(header))
    print("\t".join(header + ["elevation"]))

    current_batch = []
    while True:
        try:
            line = next(tsv).rstrip().split("\t")
        except StopIteration:
            break
        current_batch.append(line)
        if len(current_batch) >= BATCH_SIZE:
            process_batch(col, current_batch)
            current_batch = []
    if len(current_batch) > 0:
        process_batch(col, current_batch)


if __name__ == "__main__":
    main()
