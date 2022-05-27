#!/opt/homebrew/bin/python3

import dash
from dash import dcc
from dash import html
import plotly.graph_objects as go
import pandas as pd

app = dash.Dash(__name__, title="Climate projections")

df = pd.read_csv('data.tsv', sep='\t')

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
}

app.layout = html.Div(children=[
    html.Div(children=[
        dcc.Dropdown(list(valueChooserNames.keys()), 'Average daily precipitation (mm/day)', id='value-chooser', searchable=True),
        dcc.Dropdown(list(timeChooserNames.keys()), "2050 value", id='time-chooser', searchable=True),
    ]),

    dcc.Graph(
        id='climatemap',
        style={"height": "80vh"},
        config={"displaylogo": False},
    )
])

@app.callback(
    dash.Output('climatemap', 'figure'),
    [dash.Input('value-chooser', 'value'), dash.Input('time-chooser', 'value')],
)
def update_figure(valname, timename):
    varname = valueChooserNames[valname] + "-" + timeChooserNames[timename]
    fig = go.Figure(data=go.Scattergeo(
        lon = df['lon'],
        lat = df['lat'],
        mode='markers',
        marker_showscale=True,
        marker_color=df[varname],
        text=df[varname],
    ))

    fig.update_layout(
        geo_scope='usa',
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        modebar_remove=['select2d', 'lasso2d'],
        uirevision="static",
    )

    return fig

server = app.server
if __name__ == '__main__':
    app.run_server(debug=True)
