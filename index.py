#!/usr/bin/env python3

import os
import dash
from dash import dcc
from dash import html
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from urllib.parse import parse_qs

import uel, uel_conjunct
from data import (
    valueChooserNames,
    timeChooserNames,
    varname,
    df,
    UEL_ENV,
    UEL_ENV_CHECK,
    comparators,
    presentValuesOnly,
    valueChooserVals,
    timeChooserVals,
)

app = dash.Dash(
    __name__,
    title="JT's Climate Dashboard",
    external_stylesheets=[dbc.themes.BOOTSTRAP],
)


app.layout = html.Div(
    [
        dbc.Container(
            [
                html.H1("JT's Climate Dashboard"),
                dcc.Location(id="url"),
            ]
        ),
        dbc.Row(
            [
                dbc.Col(
                    id="controls",
                    width=5,
                    className="p-5",
                ),
                dbc.Col(
                    [
                        dcc.Graph(
                            id="climatemap",
                            style={"width": "50vw"},
                            config={"displaylogo": False},
                        ),
                    ]
                ),
            ]
        ),
    ]
)


def draw_simple_ui(
    add_filter_clicks,
    selected_val,
    selected_time,
    filter_vals,
    filter_times,
    filter_comps,
    filter_limits,
    filter_dels,
):
    selection_expr, filter_expr = "", ""
    if len(selected_val) != 1:
        selected_val = [list(valueChooserNames.values())[0]]
    is_present_only = selected_val[0] in presentValuesOnly
    selector_group = [
        dbc.Col(
            dbc.Select(
                options=[
                    {"label": k, "value": v} for k, v in valueChooserNames.items()
                ],
                value=selected_val[0],
                id={"type": "value-chooser", "index": 0},
            ),
            width=is_present_only and 12 or 9,
            style={"padding": "0 1px"},
        ),
    ]
    if not is_present_only:
        if len(selected_time) != 1 or selected_time[0] == "":
            selected_time = [list(timeChooserNames.values())[1]]
        selector_group.append(
            dbc.Col(
                dbc.Select(
                    options=[
                        {"label": k, "value": v} for k, v in timeChooserNames.items()
                    ],
                    value=selected_time[0],
                    id={"type": "time-chooser", "index": 0},
                ),
                width=3,
                style={"padding": "0 1px"},
            ),
        )
        selection_expr = "# %s, %s\n%s_%s " % (
            valueChooserVals[selected_val[0]],
            timeChooserVals[selected_time[0]],
            selected_val[0],
            selected_time[0],
        )
    else:
        selector_group.append(
            dbc.Input(
                id={"type": "time-chooser", "index": 0},
                value="",
                style={"display": "none"},
            )
        )
        selection_expr = "# %s\n%s" % (
            valueChooserVals[selected_val[0]],
            selected_val[0],
        )

    within_tab = [
        dbc.InputGroup(dbc.InputGroupText("Color", className="w-100")),
        dbc.Row(selector_group, style={"margin": "0 -1px"}),
        html.Br(),
        dbc.InputGroup(
            [
                dbc.InputGroupText("Filters", className="w-75"),
                dbc.Button(
                    "Add filter",
                    size="sm",
                    id={"type": "add-filter-btn", "index": os.urandom(32).hex()},
                    className="w-25",
                ),
            ]
        ),
    ]

    def draw_filter(value, time, comp, lim, index):
        nonlocal filter_expr
        if lim is not None:
            if filter_expr != "":
                filter_expr += "\nand\n"
            if value in presentValuesOnly:
                filter_expr += "# %s\n%s %s %s" % (
                    valueChooserVals[value],
                    value,
                    comp,
                    lim,
                )
            else:
                filter_expr += "# %s, %s\n%s_%s %s %s" % (
                    valueChooserVals[value],
                    timeChooserVals[time],
                    value,
                    time,
                    comp,
                    lim,
                )

        is_present_only = value in presentValuesOnly

        filter_group = [
            dbc.Col(
                dbc.Select(
                    options=[
                        {"label": k, "value": v} for k, v in valueChooserNames.items()
                    ],
                    value=value,
                    id={"type": "filter-value", "index": index},
                    className="w-100",
                ),
                style={"padding": "0 1px"},
                width=is_present_only and 7 or 5,
            ),
        ]

        if not is_present_only:
            filter_group.append(
                dbc.Col(
                    dbc.Select(
                        options=[
                            {"label": k, "value": v}
                            for k, v in timeChooserNames.items()
                        ],
                        value=time,
                        id={"type": "filter-time", "index": index},
                        className="w-100",
                    ),
                    style={"padding": "0 1px"},
                    width=2,
                ),
            )
        else:
            filter_group.append(
                dbc.Input(
                    id={"type": "filter-time", "index": index},
                    value="",
                    style={"display": "none"},
                )
            )

        filter_group.extend(
            [
                dbc.Col(
                    dbc.Select(
                        options=[{"label": v, "value": v} for v in comparators],
                        value=comp,
                        id={"type": "filter-comp", "index": index},
                        className="w-100",
                    ),
                    style={"padding": "0 1px"},
                    width=2,
                ),
                dbc.Col(
                    dbc.Input(
                        type="number",
                        value=lim,
                        id={"type": "filter-limit", "index": index},
                        className="w-100",
                    ),
                    style={"padding": "0 1px"},
                    width=2,
                ),
                dbc.Col(
                    dbc.Button(
                        children=["x"],
                        id={"type": "filter-del", "index": index},
                        className="w-100",
                    ),
                    style={"padding": "0 1px"},
                    width=1,
                ),
            ]
        )

        within_tab.extend(
            [
                dbc.Row(filter_group, style={"margin": "0 -1px"}),
            ]
        )

    deletes = 0
    for i, (
        filter_val,
        filter_time,
        filter_comp,
        filter_limit,
        filter_del,
    ) in enumerate(
        zip(filter_vals, filter_times, filter_comps, filter_limits, filter_dels)
    ):
        if filter_del is not None and filter_del > 0:
            deletes += 1
        else:
            draw_filter(filter_val, filter_time, filter_comp, filter_limit, i - deletes)

    if sum([x for x in add_filter_clicks if x is not None]) > 0:
        draw_filter(
            list(valueChooserNames.values())[0],
            list(timeChooserNames.values())[1],
            comparators[0],
            None,
            len(filter_vals) - deletes,
        )

    within_tab.extend(
        [
            html.Br(),
            dbc.Textarea(
                id={"type": "selection-box", "index": 0},
                disabled=True,
                style={"display": "none"},
                value=selection_expr,
                rows=2,
            ),
            dbc.Textarea(
                id={"type": "filter-box", "index": 0},
                disabled=True,
                style={"display": "none"},
                value=filter_expr,
                rows=len(filter_expr.split("\n")),
            ),
        ]
    )

    return within_tab, selection_expr, filter_expr


def draw_advanced_ui(selection_box, filter_box):
    if len(selection_box) != 1:
        selection_box = [""]
    if len(filter_box) != 1:
        filter_box = [""]

    selection_error_div = html.P(style={"color": "red"})
    filter_error_div = html.P(style={"color": "red"})

    return (
        [
            dbc.InputGroup(
                [
                    dbc.InputGroupText("Color", className="w-100"),
                    dbc.Textarea(
                        id={"type": "selection-box", "index": 0},
                        value=selection_box[0],
                        rows=2,
                        className="w-100",
                    ),
                ]
            ),
            selection_error_div,
            html.Br(),
            dbc.InputGroup(
                [
                    dbc.InputGroupText("Filters", className="w-100"),
                    dbc.Textarea(
                        id={"type": "filter-box", "index": 0},
                        value=filter_box[0],
                        rows=8,
                        className="w-100",
                    ),
                ]
            ),
            filter_error_div,
        ],
        selection_box[0],
        filter_box[0],
        selection_error_div,
        filter_error_div,
    )


@app.callback(
    [
        dash.Output("controls", "children"),
        dash.Output("climatemap", "figure"),
    ],
    [
        dash.Input("url", "search"),
        dash.Input({"type": "complexity-tabs", "index": dash.ALL}, "active_tab"),
        dash.Input({"type": "add-filter-btn", "index": dash.ALL}, "n_clicks"),
        dash.Input({"type": "value-chooser", "index": dash.ALL}, "value"),
        dash.Input({"type": "time-chooser", "index": dash.ALL}, "value"),
        dash.Input({"type": "filter-value", "index": dash.ALL}, "value"),
        dash.Input({"type": "filter-time", "index": dash.ALL}, "value"),
        dash.Input({"type": "filter-comp", "index": dash.ALL}, "value"),
        dash.Input({"type": "filter-limit", "index": dash.ALL}, "value"),
        dash.Input({"type": "filter-del", "index": dash.ALL}, "n_clicks"),
        dash.Input({"type": "last-tab", "index": dash.ALL}, "value"),
        dash.Input({"type": "selection-box", "index": dash.ALL}, "value"),
        dash.Input({"type": "filter-box", "index": dash.ALL}, "value"),
    ],
)
def draw_ui(
    query,
    ui_tab,
    add_filter_clicks,
    selected_val,
    selected_time,
    filter_vals,
    filter_times,
    filter_comps,
    filter_limits,
    filter_dels,
    last_tab,
    selection_box,
    filter_box,
):
    if len(ui_tab) == 0 and len(last_tab) == 0:
        query = parse_qs(query.lstrip("?"))
        if "selection" in query:
            last_tab = ["tab-advanced"]
            if "tab" in query and query["tab"][-1] == "advanced":
                ui_tab = ["tab-advanced"]
            else:
                ui_tab = ["tab-simple"]
            selection_box = [query["selection"][-1]]
            if "filter" in query:
                filter_box = [query["filter"][-1]]

    if (
        len(ui_tab) == 1
        and len(last_tab) == 1
        and ui_tab[0] == "tab-simple"
        and last_tab[0] == "tab-advanced"
    ):
        good_for_simple = True
        if len(selection_box) != 1:
            good_for_simple = False
        if len(filter_box) != 1:
            good_for_simple = False
        if good_for_simple:
            try:
                selection_parsed = uel_conjunct.identifier_parse(selection_box[0])
                selection_parsed.run(UEL_ENV_CHECK)
                filter_parsed = None
                if filter_box[0].strip() != "":
                    filter_parsed = uel_conjunct.conjunction_parse(filter_box[0])
                    filter_parsed.run(UEL_ENV_CHECK)
            except (uel.ParserError, uel.UnboundVariableError):
                good_for_simple = False

        if not good_for_simple:
            ui_tab = ["tab-advanced"]
        else:
            add_filter_clicks = []

            def parsevar(name):
                if name in presentValuesOnly:
                    return name, ""
                return name.rsplit("_", 1)

            valname, timename = parsevar(selection_parsed.name)
            selected_val = [valname]
            selected_time = [timename]
            filter_vals, filter_times, filter_comps, filter_limits = [], [], [], []
            filter_dels = []

            def walk_conjunctions(expr):
                if isinstance(expr, uel.OpAnd):
                    walk_conjunctions(expr.lhs)
                    walk_conjunctions(expr.rhs)
                    return
                assert expr.op in comparators
                name, time = parsevar(expr.lhs.name)
                filter_vals.append(name)
                filter_times.append(time)
                filter_comps.append(expr.op)
                filter_limits.append(expr.rhs.run({}))
                filter_dels.append(None)

            if filter_parsed is not None:
                walk_conjunctions(filter_parsed)

    selection_expr = ""
    filter_expr = ""
    selected_tab = "tab-simple"
    selection_error_div, filter_error_div = None, None
    if len(ui_tab) == 1 and ui_tab[0] == "tab-advanced":
        selected_tab = "tab-advanced"
        (
            within_tab,
            selection_expr,
            filter_expr,
            selection_error_div,
            filter_error_div,
        ) = draw_advanced_ui(selection_box, filter_box)
    else:
        within_tab, selection_expr, filter_expr = draw_simple_ui(
            add_filter_clicks,
            selected_val,
            selected_time,
            filter_vals,
            filter_times,
            filter_comps,
            filter_limits,
            filter_dels,
        )

    map_graph, selection_error, filter_error = update_map(selection_expr, filter_expr)
    if selection_error_div is not None:
        selection_error_div.children = [selection_error]
    if filter_error_div is not None:
        filter_error_div.children = [filter_error]

    return [
        dbc.Card(
            [
                dbc.CardHeader(
                    dbc.Tabs(
                        [
                            dbc.Tab(label="Simple", tab_id="tab-simple"),
                            dbc.Tab(label="Advanced", tab_id="tab-advanced"),
                        ],
                        id={"type": "complexity-tabs", "index": 0},
                        active_tab=selected_tab,
                    )
                ),
                dbc.CardBody(html.Div(within_tab)),
            ]
        ),
        dbc.Input(
            id={"type": "last-tab", "index": 0},
            value=selected_tab,
            style={"display": "none"},
        ),
    ], map_graph


def update_map(selection_expr, filter_expr):
    data_col, lat, lon = None, None, None

    selection_error = ""
    try:
        uel.uel_eval(selection_expr, UEL_ENV_CHECK)
    except (uel.UnboundVariableError, uel.ParserError, KeyError) as e:
        selection_error = str(e)
        selection_expr = ""

    filter_error = ""
    if filter_expr.strip() != "":
        try:
            uel.uel_eval(filter_expr, UEL_ENV_CHECK)
        except (uel.UnboundVariableError, uel.ParserError, KeyError) as e:
            filter_error = str(e)
            selection_expr = ""

    if selection_expr.strip() != "":
        data_col = uel.uel_eval(selection_expr, UEL_ENV)
        if data_col is not None:
            lat = df["lat"]
            lon = df["lon"]
            if filter_expr.strip() != "":
                filter = uel.uel_eval(filter_expr, UEL_ENV)
                try:
                  data_col = data_col[filter]
                  lat = lat[filter]
                  lon = lon[filter]
                except KeyError:
                  filter_error = "invalid filter"
                  data_col, lat, lon = None, None, None

    fig = go.Figure(
        data=go.Scattergeo(
            lat=lat,
            lon=lon,
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
    return fig, selection_error, filter_error


server = app.server
if __name__ == "__main__":
    app.run_server(debug=True)
