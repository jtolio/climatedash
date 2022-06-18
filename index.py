#!/usr/bin/env python3

import dash
from dash import dcc
from dash import html
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import uel
from urllib.parse import parse_qs

app = dash.Dash(__name__, title="Climate projections")

df = pd.read_csv("data.tsv", sep="\t")

timeChooserNames = {
    "2010 value": "2010",
    "2050 value": "2050",
    "2010-2050 change": "2050d",
    "2090 value": "2090",
    "2010-2090 change": "2090d",
}

valueChooserNames = {
    "Average precipitation (in/year)": "prec_avg",
    "Average annual days with no precipitation": "prec_days_at_or_below_0",
    "Average surface downwelling shortwave radiation (W/m^2)": "rsds_avg",
    "Average wind speed (mph)": "sfcWind_avg",
    "Average annual max daily average wind speed (mph)": "sfcWind_avg_max",
    "Average annual max temperature (deg F)": "tmax_avg_max",
    "Average annual days above 95 F": "tmax_days_above_35",
    "Average temperature (deg F)": "tmean_avg",
    "Average annual min temperature (deg F)": "tmin_avg_min",
    "Average annual days at or below freezing": "tmin_days_at_or_below_0",
    "Average wet-bulb temperature (Stull method, deg F)": "wetbulb_avg",
    "Average annual max daily average wet-bulb temperature (Stull method, deg F)": "wetbulb_avg_max",
    "Average annual min daily average wet-bulb temperature (Stull method, deg F)": "wetbulb_avg_min",
    "Average annual days above wet-bulb temperature 78.8 F (Stull method)": "wetbulb_days_above_26",
    "Elevation (ft)": "elevation",
    "FIPS County Code": "fips",
}

presentValuesOnly = set(["elevation", "fips"])

unitConversions = {
    "mm/day->in/year": lambda x: (x / 25.4) * 365.25,
    "in/year->mm/day": lambda x: (x / 365.25) * 25.4,
    "m->ft": lambda x: x * 3.28084,
    "ft->m": lambda x: x / 3.28084,
    "C->F": lambda x: x * 9 / 5 + 32,
    "F->C": lambda x: (x - 32) * 5 / 9,
    "m/s->mph": lambda x: x * 2.23694,
    "mph->m/s": lambda x: x / 2.23694,
}

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

app.layout = html.Div(
    children=[
        dcc.Location(id="url"),
        html.Div(
            children=[
                dcc.Dropdown(
                    list(valueChooserNames.keys()),
                    list(valueChooserNames.keys())[0],
                    id="value-chooser",
                    searchable=True,
                ),
                dcc.Dropdown(
                    list(timeChooserNames.keys()),
                    list(timeChooserNames.keys())[1],
                    id="time-chooser",
                    searchable=True,
                ),
                html.Div(id="filter-container", children=[]),
                html.Div(
                    [html.Button("Add Filter", id="add-filter-button", n_clicks=0)],
                ),
            ]
        ),
        dcc.Graph(
            id="climatemap",
            style={"height": "80vh"},
            config={"displaylogo": False},
        ),
    ]
)


@app.callback(
    [
        dash.Output({"type": "filter", "index": dash.MATCH}, "children"),
        dash.Output({"type": "filter", "index": dash.MATCH}, "style"),
    ],
    [
        dash.Input({"type": "remove", "index": dash.MATCH}, "n_clicks"),
    ],
    [dash.State({"type": "filter", "index": dash.MATCH}, "children")],
)
def remove_filter(n_clicks, children):
    if n_clicks > 0:
        return [], {"display": "none"}
    return children, {}


@app.callback(
    dash.Output("filter-container", "children"),
    [
        dash.Input("add-filter-button", "n_clicks"),
    ],
    [dash.State("filter-container", "children")],
)
def add_filter(n_clicks, children):
    if n_clicks == 0:
        return children
    new_element = html.Div(
        id={"type": "filter", "index": n_clicks},
        children=[
            html.Table(
                [
                    html.Tr(
                        [
                            html.Td(
                                [
                                    dcc.Dropdown(
                                        id={"type": "variable", "index": n_clicks},
                                        options=list(valueChooserNames.keys()),
                                        value=list(valueChooserNames.keys())[0],
                                        persistence=True,
                                        persistence_type="session",
                                    ),
                                ],
                                style={"width": 400},
                            ),
                            html.Td(
                                [
                                    dcc.Dropdown(
                                        id={"type": "time", "index": n_clicks},
                                        options=list(timeChooserNames.keys()),
                                        value=list(timeChooserNames.keys())[1],
                                        persistence=True,
                                        persistence_type="session",
                                    ),
                                ],
                                style={"width": 150},
                            ),
                            html.Td(
                                [
                                    dcc.Dropdown(
                                        id={"type": "comparison", "index": n_clicks},
                                        options=list(comparators.keys()),
                                        value=list(comparators.keys())[0],
                                        persistence=True,
                                        persistence_type="session",
                                    ),
                                ],
                                style={"width": 75},
                            ),
                            html.Td(
                                [
                                    dcc.Input(
                                        id={"type": "value", "index": n_clicks},
                                        type="number",
                                    ),
                                ]
                            ),
                            html.Td(
                                [
                                    html.Button(
                                        "x",
                                        id={"type": "remove", "index": n_clicks},
                                        n_clicks=0,
                                    ),
                                ]
                            ),
                        ]
                    )
                ]
            )
        ],
        style={"padding-top": 25},
    )
    children.append(new_element)
    return children


comparators = {
    "<": lambda x, y: x < y,
    "<=": lambda x, y: x <= y,
    "==": lambda x, y: x == y,
    ">=": lambda x, y: x >= y,
    ">": lambda x, y: x > y,
    "!=": lambda x, y: x != y,
}


def varname_lookup(valname, timename):
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


def set_in_env(var, time_suffix):
    if time_suffix is None:
      varname = var
    else:
      varname = "%s_%s" % (var, time_suffix)
    display_conversion = unitDisplays.get(var, None)
    if display_conversion is None:
        UEL_ENV[varname] = df[varname]
        return
    UEL_ENV[varname] = unitConversions["%s->%s" % display_conversion](df[varname])


for var in valueChooserNames.values():
    if var in presentValuesOnly:
        set_in_env(var, None)
    else:
        for time_suffix in timeChooserNames.values():
            set_in_env(var, time_suffix)


@app.callback(
    dash.Output("climatemap", "figure"),
    [
        dash.Input("url", "search"),
        dash.Input("value-chooser", "value"),
        dash.Input("time-chooser", "value"),
        dash.Input({"type": "variable", "index": dash.ALL}, "value"),
        dash.Input({"type": "time", "index": dash.ALL}, "value"),
        dash.Input({"type": "comparison", "index": dash.ALL}, "value"),
        dash.Input({"type": "value", "index": dash.ALL}, "value"),
    ],
)
def update_figure(
    query_string,
    valname,
    timename,
    filter_variables,
    filter_times,
    filter_comparisons,
    filter_values,
):
    query_string = parse_qs(query_string.lstrip("?"))

    if "value" not in query_string:
        query_string["value"] = [varname_lookup(valname, timename)]

    if "filter" not in query_string:
        filter = "true"
        for (filter_variable, filter_time, filter_comp, filter_val) in zip(
            filter_variables, filter_times, filter_comparisons, filter_values
        ):
            if filter_val is None:
                continue
            filter += (
                " and "
                + varname_lookup(filter_variable, filter_time)
                + filter_comp
                + repr(filter_val)
            )
        query_string["filter"] = [filter]

    data = df
    print("showing", query_string["value"][0])
    data_col = uel.uel_eval(query_string["value"][0], UEL_ENV)
    print("filtering", query_string["filter"][0])
    if query_string["filter"][0] != "true":
      filter = uel.uel_eval(query_string["filter"][0], UEL_ENV)
      data = data[filter]
      data_col = data_col[filter]

    fig = go.Figure(
        data=go.Scattergeo(
            lon=data["lon"],
            lat=data["lat"],
            mode="markers",
            marker_showscale=True,
            marker_color=data_col,
            text=data_col,
        )
    )

    fig.update_layout(
        geo_scope="usa",
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        modebar_remove=["select2d", "lasso2d"],
        uirevision="static",
    )

    return fig


server = app.server
if __name__ == "__main__":
    app.run_server(debug=True)
