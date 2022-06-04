#!/usr/bin/env python3

import dash
from dash import dcc
from dash import html
import plotly.graph_objects as go
import pandas as pd

app = dash.Dash(__name__, title="Climate projections")

df = pd.read_csv("data.tsv", sep="\t")

timeChooserNames = {
    "2010 value": "time1",
    "2050 value": "time2",
    "2010-2050 change": "delta1",
    "2090 value": "time3",
    "2010-2090 change": "delta2",
}

valueChooserNames = {
    "Average daily precipitation (mm/day)": "prec_avg",
    "Average annual days with no precipitation": "prec_days_at_or_below_0",
    "Average surface downwelling shortwave radiation (W/m^2)": "rsds_avg",
    "Average wind speed (m/s)": "sfcWind_avg",
    "Average annual max daily average wind speed (m/s)": "sfcWind_avg_max",
    "Average annual max temperature (deg C)": "tmax_avg_max",
    "Average annual days above 35 C": "tmax_days_above_35",
    "Average temperature (deg C)": "tmean_avg",
    "Average annual min temperature (deg C)": "tmin_avg_min",
    "Average annual days at or below freezing": "tmin_days_at_or_below_0",
    "Average wet-bulb temperature (Stull method, deg C)": "wetbulb_avg",
    "Average annual max daily average wet-bulb temperature (Stull method, deg C)": "wetbulb_avg_max",
    "Average annual min daily average wet-bulb temperature (Stull method, deg C)": "wetbulb_avg_min",
    "Average annual days above wet-bulb temperature 26 C (Stull method)": "wetbulb_days_above_26",
    "Elevation (m)": "elevation",
}

presentValuesOnly = set(["elevation"])

app.layout = html.Div(
    children=[
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


@app.callback(
    dash.Output("climatemap", "figure"),
    [
        dash.Input("value-chooser", "value"),
        dash.Input("time-chooser", "value"),
        dash.Input({"type": "variable", "index": dash.ALL}, "value"),
        dash.Input({"type": "time", "index": dash.ALL}, "value"),
        dash.Input({"type": "comparison", "index": dash.ALL}, "value"),
        dash.Input({"type": "value", "index": dash.ALL}, "value"),
    ],
)
def update_figure(
    valname, timename, filter_variables, filter_times, filter_comparisons, filter_values
):
    if valueChooserNames[valname] in presentValuesOnly:
        varname = valueChooserNames[valname]
    else:
        varname = valueChooserNames[valname] + "-" + timeChooserNames[timename]

    data = df
    for (filter_variable, filter_time, filter_comp, filter_val) in zip(
        filter_variables, filter_times, filter_comparisons, filter_values
    ):
        if filter_val is None:
            continue
        data = data[
            comparators[filter_comp](
                data[
                    valueChooserNames[filter_variable]
                    + "-"
                    + timeChooserNames[filter_time]
                ],
                filter_val,
            )
        ]

    fig = go.Figure(
        data=go.Scattergeo(
            lon=data["lon"],
            lat=data["lat"],
            mode="markers",
            marker_showscale=True,
            marker_color=data[varname],
            text=data[varname],
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
