#!/usr/bin/env python3

import os, sys, numpy

from netCDF4 import Dataset

timeframes = [
    "2009-01-01T12:00:00Z.2012-01-01T12:00:00Z",
    "2049-01-01T12:00:00Z.2052-01-01T12:00:00Z",
    "2089-01-01T12:00:00Z.2092-01-01T12:00:00Z",
]
timeframe_names = ["2010", "2050", "2090"]
timedelta_names = ["2050d", "2090d"]
grid = "NAM-22i"
scenario = "rcp85"
granularity = "day"
bias = "mbcn-gridMET"
root = "./data"

models = {
    "NAM-22i": (
        ("CanESM2", "CRCM5-UQAM"),
        ("CanESM2", "CanRCM4"),
        ("GEMatm-Can", "CRCM5-UQAM"),
        ("GEMatm-MPI", "CRCM5-UQAM"),
        ("GFDL-ESM2M", "WRF"),
        ("MPI-ESM-LR", "CRCM5-UQAM"),
        ("MPI-ESM-LR", "WRF"),
        ("MPI-ESM-MR", "CRCM5-UQAM"),
        # missing bias correction
        # ("CNRM-CM5", "CRCM5-OUR"),
        # ("CanESM2", "CRCM5-OUR"),
        # ("CanESM2", "RCA4"),
        # ("GFDL-ESM2M", "CRCM5-OUR"),
        # ("MPI-ESM-LR", "CRCM5-OUR"),
    ),
    "NAM-44i": (
        ("CanESM2", "CRCM5-UQAM"),
        ("CanESM2", "CanRCM4"),
        ("CanESM2", "RCA4"),
        ("EC-EARTH", "HIRHAM5"),
        ("EC-EARTH", "RCA4"),
        ("GEMatm-Can", "CRCM5-UQAM"),
        ("GEMatm-MPI", "CRCM5-UQAM"),
        ("GFDL-ESM2M", "WRF"),
        ("MPI-ESM-LR", "CRCM5-UQAM"),
        ("MPI-ESM-LR", "WRF"),
        ("MPI-ESM-MR", "CRCM5-UQAM"),
        # missing bias correction
        # ("CNRM-CM5", "CRCM5-OUR"),
        # ("CanESM2", "CRCM5-OUR"),
        # ("GFDL-ESM2M", "CRCM5-OUR"),
        # ("MPI-ESM-LR", "CRCM5-OUR"),
    ),
}


def stull_wetbulb(temp_c, relhum_pc):
    # https://open.library.ubc.ca/media/stream/pdf/52383/1.0041967/1
    # example from paper: stull_wetbulb(20, 50) should be 13.7
    return (
        numpy.multiply(
            temp_c,
            numpy.arctan(
                0.151977 * numpy.float_power(numpy.add(relhum_pc, 8.313659), 0.5)
            ),
        )
        + numpy.arctan(numpy.add(temp_c, relhum_pc))
        - numpy.arctan(numpy.add(relhum_pc, -1.676331))
        + 0.00391838
        * numpy.float_power(relhum_pc, 1.5)
        * numpy.arctan(numpy.multiply(0.023101, relhum_pc))
        - 4.686035
    )


def assertEqual(x, y):
    if x != y:
        raise Exception("%r != %r", x, y)


def assertArrayEqual(x, y):
    if x.shape != y.shape:
        raise Exception("shape %r != %r", x.shape, y.shape)
    if not numpy.all(numpy.equal(x, y)):
        raise Exception("arrays not equal")


def assertIn(x, ys):
    if x not in ys:
        raise Exception("%r not in %r", x, ys)


def doublecheck(ds, var, units):
    assertEqual(ds.variables["lon"].units, "degrees_east")
    assertEqual(ds.variables["lat"].units, "degrees_north")
    assertIn(
        ds.variables["time"].units,
        (
            "days since 1949-12-01 00:00:00",
            "days since 1949-12-01",
            "days since 1949-12-1 00:00:00",
        ),
    )
    assertEqual(ds.variables[var].units, units)
    assertEqual(len(ds.variables["lon"].shape), 1)
    assertEqual(len(ds.variables["lat"].shape), 1)
    assertEqual(len(ds.variables["time"].shape), 1)
    assertEqual(len(ds.variables[var].shape), 3)
    assertEqual(
        ds.variables[var].shape,
        (
            ds.variables["time"].shape[0],
            ds.variables["lat"].shape[0],
            ds.variables["lon"].shape[0],
        ),
    )


def loadfile(path):
    print(path, file=sys.stderr)
    return Dataset(path, "r")


def wetbulb(var, units, gcm, rcm, grid, scenario, granularity, bias, timerange):
    tmean = loadfile(
        os.path.join(
            root,
            f"tmean.{scenario}.{gcm}.{rcm}.{granularity}.{grid}.{bias}.{timerange}.nc",
        )
    )
    doublecheck(tmean, "tmean", "degC")
    relhum = loadfile(
        os.path.join(
            root,
            f"hurs.{scenario}.{gcm}.{rcm}.{granularity}.{grid}.{bias}.{timerange}.nc",
        )
    )
    doublecheck(relhum, "hurs", "%")
    assertArrayEqual(tmean.variables["lon"], relhum.variables["lon"])
    assertArrayEqual(tmean.variables["lat"], relhum.variables["lat"])
    assertArrayEqual(tmean.variables["time"], relhum.variables["time"])
    values = stull_wetbulb(tmean.variables["tmean"], relhum.variables["hurs"])
    mask = numpy.any(numpy.isnan(tmean.variables["tmean"]), axis=0) | numpy.any(
        numpy.isnan(relhum.variables["hurs"]), axis=0
    )
    return values, mask, tmean.variables["lat"], tmean.variables["lon"]


def directload(var, units, gcm, rcm, grid, scenario, granularity, bias, timerange):
    ds = loadfile(
        os.path.join(
            root,
            f"{var}.{scenario}.{gcm}.{rcm}.{granularity}.{grid}.{bias}.{timerange}.nc",
        )
    )
    doublecheck(ds, var, units)
    mask = numpy.any(numpy.isnan(ds.variables[var]), axis=0)
    return ds.variables[var], mask, ds.variables["lat"], ds.variables["lon"]


def annualdaysabovex(var, x):
    years = var.shape[0] / 365.0
    return numpy.sum(numpy.greater(var, x).astype(int), axis=0) / years


def annualdaysatorbelowx(var, x):
    years = var.shape[0] / 365.0
    return numpy.sum(numpy.less_equal(var, x).astype(int), axis=0) / years


def ensemblemean(models, generator):
    sofar_data = None
    sofar_mask = None
    sofar_lat = None
    sofar_lon = None
    for gcm, rcm in models:
        data, mask, lat, lon = generator(gcm, rcm)
        if sofar_data is None:
            sofar_data = data
            sofar_mask = mask
            sofar_lat, sofar_lon = lat, lon
            continue
        sofar_data += data
        sofar_mask |= mask
        assertArrayEqual(sofar_lat, lat)
        assertArrayEqual(sofar_lon, lon)
    return sofar_data / float(len(models)), sofar_mask, sofar_lat, sofar_lon


def calc_deltas(timeframes, generator):
    beginning, mask, lat, lon = generator(timeframes[0])
    absolutes = [beginning]
    deltas = []
    for end_timeframe in timeframes[1:]:
        end, end_mask, end_lat, end_lon = generator(end_timeframe)
        assertArrayEqual(lat, end_lat)
        assertArrayEqual(lon, end_lon)
        mask |= end_mask
        absolutes.append(end)
        deltas.append(end - beginning)
    return absolutes, deltas, mask, lat, lon


def add_to_db(name, database, absolutes, deltas, mask, lat, lon):
    for i, absolute in enumerate(absolutes):
        database["header"].append("%s_%s" % (name, timeframe_names[i]))
    for i, delta in enumerate(deltas):
        database["header"].append("%s_%s" % (name, timedelta_names[i]))
    for y in range(len(lat)):
        for x in range(len(lon)):
            if not mask[y][x]:
                key = (str(lat[y]), str(lon[x]))
                if key not in database:
                    database[key] = {}
                for i, absolute in enumerate(absolutes):
                    kname = "%s_%s" % (name, timeframe_names[i])
                    database[key][kname] = absolute[y, x]
                for i, delta in enumerate(deltas):
                    kname = "%s_%s" % (name, timedelta_names[i])
                    database[key][kname] = delta[y, x]


def calc_days_above(database, varname, threshold, units, loader=directload):
    def timeframegen(timerange):
        def modelgenerator(gcm, rcm):
            data, mask, lat, lon = loader(
                varname, units, gcm, rcm, grid, scenario, granularity, bias, timerange
            )
            return annualdaysabovex(data, threshold), mask, lat, lon

        return ensemblemean(models[grid], modelgenerator)

    absolutes, deltas, mask, lat, lon = calc_deltas(timeframes, timeframegen)
    add_to_db(
        "%s_days_above_%d" % (varname, threshold),
        database,
        absolutes,
        deltas,
        mask,
        lat,
        lon,
    )


def calc_days_at_or_below(database, varname, threshold, units, loader=directload):
    def timeframegen(timerange):
        def modelgenerator(gcm, rcm):
            data, mask, lat, lon = loader(
                varname, units, gcm, rcm, grid, scenario, granularity, bias, timerange
            )
            return annualdaysatorbelowx(data, threshold), mask, lat, lon

        return ensemblemean(models[grid], modelgenerator)

    absolutes, deltas, mask, lat, lon = calc_deltas(timeframes, timeframegen)
    add_to_db(
        "%s_days_at_or_below_%d" % (varname, threshold),
        database,
        absolutes,
        deltas,
        mask,
        lat,
        lon,
    )


def avg_year_summary(var, summary_fn):
    years = int(var.shape[0] / 365)
    assert years == 3
    total = None
    for year in range(years):
        year_data = summary_fn(var[year * 365 : (year + 1) * 365, :, :], axis=0)
        if total is None:
            total = year_data
        else:
            total = total + year_data
    return total / years


def calc_avg_min(database, varname, units, loader=directload):
    def timeframegen(timerange):
        def modelgen(gcm, rcm):
            data, mask, lat, lon = loader(
                varname, units, gcm, rcm, grid, scenario, granularity, bias, timerange
            )
            return avg_year_summary(data, numpy.amin), mask, lat, lon

        return ensemblemean(models[grid], modelgen)

    absolutes, deltas, mask, lat, lon = calc_deltas(timeframes, timeframegen)
    add_to_db("%s_avg_min" % varname, database, absolutes, deltas, mask, lat, lon)


def calc_avg_max(database, varname, units, loader=directload):
    def timeframegen(timerange):
        def modelgen(gcm, rcm):
            data, mask, lat, lon = loader(
                varname, units, gcm, rcm, grid, scenario, granularity, bias, timerange
            )
            return avg_year_summary(data, numpy.amax), mask, lat, lon

        return ensemblemean(models[grid], modelgen)

    absolutes, deltas, mask, lat, lon = calc_deltas(timeframes, timeframegen)
    add_to_db("%s_avg_max" % varname, database, absolutes, deltas, mask, lat, lon)


def calc_avg(database, varname, units, loader=directload):
    def timeframegen(timerange):
        def modelgen(gcm, rcm):
            data, mask, lat, lon = loader(
                varname, units, gcm, rcm, grid, scenario, granularity, bias, timerange
            )
            return numpy.sum(data, axis=0) / data.shape[0], mask, lat, lon

        return ensemblemean(models[grid], modelgen)

    absolutes, deltas, mask, lat, lon = calc_deltas(timeframes, timeframegen)
    add_to_db("%s_avg" % varname, database, absolutes, deltas, mask, lat, lon)


def write_db(database):
    print("\t".join(database["header"]))
    for key, vals in database.items():
        if key == "header":
            continue
        print("\t".join(list(key) + [str(vals[h]) for h in database["header"][2:]]))


database = {"header": ["lat", "lon"]}
calc_avg(database, "sfcWind", "m s-1")
calc_avg_max(database, "sfcWind", "m s-1")
calc_avg(database, "rsds", "W m-2")
calc_days_above(database, "wetbulb", 26, "degC", loader=wetbulb)
calc_avg_min(database, "wetbulb", "degC", loader=wetbulb)
calc_avg_max(database, "wetbulb", "degC", loader=wetbulb)
calc_avg(database, "wetbulb", "degC", loader=wetbulb)
calc_avg(database, "tmean", "degC")
calc_days_above(database, "tmax", 35, "degC")
calc_avg_max(database, "tmax", "degC")
calc_days_at_or_below(database, "tmin", 0, "degC")
calc_avg_min(database, "tmin", "degC")
calc_days_at_or_below(database, "prec", 0, "mm/day")
calc_avg(database, "prec", "mm/day")
write_db(database)
