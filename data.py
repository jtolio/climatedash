#!/usr/bin/env python3

import pandas as pd
import numpy as np


import uel


df = pd.read_csv("data.tsv", sep="\t")

timeChooserNames = {
    "2010 value": "2010",
    "2050 value": "2050",
    "2010-2050 change": "2050d",
    "2090 value": "2090",
    "2010-2090 change": "2090d",
}

timeChooserVals = {v: k for k, v in timeChooserNames.items()}

deltaNames = set(["2050d", "2090d"])

valueChooserNames = {
    "Average precipitation (in/year)": "prec_avg",
    "Average annual days with no precipitation": "prec_days_at_or_below_0",
    "Average surface downwelling shortwave radiation (W/m^2)": "rsds_avg",
    "Average wind speed (mph)": "sfcWind_avg",
    "Average annual max daily average wind speed (mph)": "sfcWind_avg_max",
    "Average annual max temperature (deg F)": "tmax_avg_max",
    "Average annual days above 95 F": "tmax_days_above_95",
    "Average temperature (deg F)": "tmean_avg",
    "Average annual min temperature (deg F)": "tmin_avg_min",
    "Average annual days at or below freezing": "tmin_days_at_or_below_32",
    "Average wet-bulb temperature (Stull method, deg F)": "wetbulb_avg",
    "Average annual max daily average wet-bulb temperature (Stull method, deg F)": "wetbulb_avg_max",
    "Average annual min daily average wet-bulb temperature (Stull method, deg F)": "wetbulb_avg_min",
    "Average annual days above wet-bulb temperature 78.8 F (Stull method)": "wetbulb_days_above_78_8",
    "Elevation (ft)": "elevation",
    "FIPS County Code": "fips",
}

valueChooserVals = {v: k for k, v in valueChooserNames.items()}

presentValuesOnly = set(["elevation", "fips"])

unitConversions = {
    "mm/day->in/year": lambda x: (x / 25.4) * 365.25,
    "m->ft": lambda x: x * 3.28084,
    "C->F": lambda x: x * 9 / 5 + 32,
    "dC->dF": lambda x: x * 9 / 5,
    "m/s->mph": lambda x: x * 2.23694,
}

varnameConversions = {}

for fname, cname in (
    ("tmax_days_above_95", "tmax_days_above_35"),
    ("wetbulb_days_above_78_8", "wetbulb_days_above_26"),
    ("tmin_days_at_or_below_32", "tmin_days_at_or_below_0"),
):
    for t in timeChooserVals:
        varnameConversions[fname + "_" + t] = cname + "_" + t

unitDisplays = {
    "sfcWind_avg": ("m/s", "mph"),
    "sfcWind_avg_max": ("m/s", "mph"),
    "tmax_avg_max": ("C", "F"),
    "tmean_avg": ("C", "F"),
    "tmin_avg_min": ("C", "F"),
    "wetbulb_avg": ("C", "F"),
    "wetbulb_avg_max": ("C", "F"),
    "wetbulb_avg_min": ("C", "F"),
    "elevation": ("m", "ft"),
    "prec_avg": ("mm/day", "in/year"),
}

comparators = ["<", "<=", "==", ">=", ">", "!="]


def varname(valname, timename):
    v = valueChooserNames[valname]
    if v in presentValuesOnly:
        return v
    return v + "_" + timeChooserNames[timename]


UEL_ENV = {
    uel.OpOr: np.logical_or,
    uel.OpAnd: np.logical_and,
    uel.ModNot: np.logical_not,
    "true": True,
    "false": False,
}

UEL_ENV_CHECK = {k: v for k, v in UEL_ENV.items()}


def set_in_env(var, time_suffix):
    if time_suffix is None:
        varname = var
    else:
        varname = "%s_%s" % (var, time_suffix)
    display_conversion = unitDisplays.get(var, None)
    if display_conversion is None:
        UEL_ENV[varname] = df[varnameConversions.get(varname, varname)]
    else:
        if (
            time_suffix in deltaNames
            and "d%s->d%s" % display_conversion in unitConversions
        ):
            UEL_ENV[varname] = unitConversions["d%s->d%s" % display_conversion](
                df[varnameConversions.get(varname, varname)]
            )
        else:
            UEL_ENV[varname] = unitConversions["%s->%s" % display_conversion](
                df[varnameConversions.get(varname, varname)]
            )
    UEL_ENV_CHECK[varname] = UEL_ENV[varname][:1]


for var in valueChooserNames.values():
    if var in presentValuesOnly:
        set_in_env(var, None)
    else:
        for time_suffix in timeChooserNames.values():
            set_in_env(var, time_suffix)
