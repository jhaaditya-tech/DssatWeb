"""
This module contains
"""
import json

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from highcharts_core.chart import Chart
from highcharts_core.options import HighchartsOptions, Legend
from highcharts_core.options.series.bar import ColumnRangeSeries, ColumnSeries
from highcharts_core.options.series.scatter import ScatterSeries
from highcharts_core.options.plot_options.bar import ColumnRangeOptions

from dssat.run import GSRun
from DSSATTools import Weather
import dssat.database as db

import numpy as np
import pandas as pd

from datetime import datetime, timedelta
from itertools import product
import tempfile
import os
import shutil
from tqdm import tqdm

from dssat.ui.base import SimulationPars
from dssat.ui.plot import columnRange_data, process_overview
import geopandas as gpd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
f = open(str(BASE_DIR) + '/data.json', )
config = json.load(f)
MIN_SAMPLES = 4
MAX_SIM_LENGTH = 12 * 30  # This is maximum simulation lenght since planting.
SERIES_CI = [95, 75, 50, 25]
Q_RANGE_PLOTS = [(.5 - q / 200, .5 + q / 200) for q in SERIES_CI]
# COLORS = ["#99ff99", "#66ff66", "#33cc33", "#009933"]
COLORS = ["#66ff66", "#33cc33", "#009933", "#006600"]

Q_RANGE_PLOTS = (
    (0.005, 0.995), (0.05, 0.95), (0.125, 0.875), (0.25, 0.75),
)
DEV_STAGES = [
    'Emergence-End Juvenile', 'End Juvenil-Floral Init',
    'Floral Init-End Lf Grow', 'End Lf Grth-Beg Grn Fil',
    'Grain Filling Phase'
]
DEV_STAGES_LABELS = [
    "Emerg.-End<br>Juv.", "End Juv-<br>Flor Init", "Flor Init-<br>End Lf Gro",
    "End lf Gro-<br>Beg Grain<br>Fil", "Grain<br>Fill"
]
STRESS_COLUMNS = {
    "water": "watStress",
    "nitrogen": "nitroStress"
}
CAT_NAMES = ["Very low", "Low", "Normal", "High", "Very high"]
CAT_COLORS = ['#cc0000', "#ff9933", "#ffff66", "#99cc00", "#009933"]
BASELINE_YEARS = (2017, 2018, 2019, 2020, 2021)

QUANTILES_TO_COMPARE = np.arange(0.025, 1, 0.05)
SCHEMAS = ("kenya", "zimbabwe")


@csrf_exempt
def run_spatial_dssat(request, admin1):
    selector_pars = {"schema": "kenya", "admin1": None, "session": None}
    """
    Runs DSSAT in spatial mode for the defined country (schema) and admin
    subdivision (admin1).

    Arguments
    ----------
    dbname: str
        Name of the database
    schema: str
        Name of the schema (country)
    admin1: str
        Name of the administrative subdivision in that country
    nitrogen: list of tuples [(int, float), ...]
            A list of tuples where each tuple is one Nitrogen application. The
            tuple contains two values, where the first one indicates the application
            time (days after planting) and the second one the nitrogen rate (kg/ha).
    planting: datetime
        Planting date
    cultivar: str
        Cultivar code. It must be available on the DSSAT list of cultivars.
    nens: int
        Number of random samples within the region
    all_random: bool
        If false soil and weather are from the same pixel. If true soil and
        weather pixels are shuffled and randomly selected.
    overview: bool
        If true it will return the overview file string
    return_input: bool
        If True it will return a list with the path to the .SOL and .WTH and the
        model won't run. This is useful for calibration, as the inputs wound be
        queried from the db only once.
    connection:
        a psycopg2 connection object. It will be used instead of setting new
        conection to dbname
    **kwargs:
        kwargs to pass to the GSRun.run function
    """
    # Simulation will start 30 days prior (As sugested by Ines et al., 2013)
    # start_date = plantingdate
    plantingdate = datetime.strptime(request.POST.get('planting_date'), '%Y-%m-%d')
    con = False
    dbname = request.POST.get('dbname')
    schema = request.POST.get('schema')
    # admin1 = request.POST.get('admin11')
    all_random = True
    overview = False
    return_input = False
    nens = 50
    n_dap = request.POST.getlist('nitrogen_dap[]')
    n_rate = request.POST.getlist('nitrogen_rate[]')
    nitrogen = []
    for i in range(len(n_dap)):
        nitrogen.append((float(n_dap[i]), float(n_rate[i])))

    cultivar = request.POST.get('cultivar')

    start_date = plantingdate - timedelta(days=30)
    end_date = plantingdate + timedelta(days=MAX_SIM_LENGTH)
    close_connection = False
    if not con:
        con = db.connect(dbname)
        close_connection = True
    db.check_admin1_in_country(con, schema, admin1)
    # Get soils and verify a minimum number of pixel samples
    soils = db.get_soils(con, schema, admin1, 1)
    if len(soils) < MIN_SAMPLES:
        soils = db.get_soils(con, schema, admin1, 2)
        if len(soils) < MIN_SAMPLES:
            soils = db.get_soils(con, schema, admin1, None)
            assert len(soils) > MIN_SAMPLES, \
                f"Region is not large enough to have at least {MIN_SAMPLES} samples"

    pixels = soils.apply(lambda row: (row.lon, row.lat), axis=1)
    n_pixels = len(pixels)
    if all_random:
        # In case all pixel combinations are posible
        if n_pixels < np.sqrt(nens):
            pix_prod = list(product(pixels, pixels))
            soil_pixels = [p[0] for p in pix_prod]
            weather_pixels = [p[1] for p in pix_prod]
        else:
            soil_pixels = pixels.sample(nens, replace=n_pixels < nens)
            weather_pixels = pixels.sample(nens, replace=n_pixels < nens)
    else:
        nens = min(nens, n_pixels)
        soil_pixels = weather_pixels = pixels.sample(nens, replace=False)

    # tmpdir to save wth files
    if return_input:
        tmp_dir_name = tempfile.mkdtemp()
        input_files = []
    else:
        tmp_dir = tempfile.TemporaryDirectory()
        tmp_dir_name = tmp_dir.name
    # Add treatments
    gs = GSRun()

    # Check if TAVG and TAMP are in static table
    tav_exists = db.verify_static_par_exists(dbname, schema, "tav", con)
    tamp_exists = db.verify_static_par_exists(dbname, schema, "tamp", con)

    for (n, (soil, weather)) in tqdm(list(enumerate(zip(soil_pixels, weather_pixels)))):
        soil_profile = soils.loc[
            (soils.lon == soil[0]) & (soils.lat == soil[1]),
            "soil"
        ].values[0]
        weather_df = db.get_era5_for_point(
            con, schema, weather[0], weather[1],
            start_date, end_date
        )
        if tav_exists and tamp_exists:
            tav = db.get_static_par(con, schema, weather[0], weather[1], "tav")
            tamp = db.get_static_par(con, schema, weather[0], weather[1], "tamp")
        else:
            tav = None
            tamp = None

        if (weather_df is None) or (len(weather_df) < 1):
            # In the unlikely case that there is no data for that location.
            # This can occur in soil pixels that are near coasts or very close
            # to the domain's boundary
            continue
        weather_df["tmax"] -= 273.15
        weather_df["tmin"] -= 273.15
        weather_df["srad"] /= 1e6
        weather_df["rain"] = weather_df.rain.abs()

        # weather_df = weather_df.sort_index()
        weather_df.index = pd.to_datetime(weather_df.index)
        pars = {i: i.upper() for i in weather_df.columns}
        # Weather class checks data consistency. If some inconsistency is found
        # (for example Tmax < Tmin) it will raise an error. It is not unusual to
        # to find small inconsistencies in global datasets.  Then, in case that
        # there is an inconsitency, that pixel will be skiped.
        try:
            dssat_weather = Weather(
                weather_df, pars, weather[1], weather[0],
                tav=tav, amp=tamp
            )
        except AssertionError:
            continue
        dssat_weather._name = f"WS{n:02}{dssat_weather._name[4:]}"

        dssat_weather.write(tmp_dir_name)

        # Planting assuming emergence 5 days after planting
        planting = {
            "PDATE": plantingdate,
            # "EDATE": plantingdate + timedelta(days=5),
            "PLDP": 5
        }
        if return_input:
            input_files.append((
                (weather, os.path.join(tmp_dir_name, f"{dssat_weather._name}.WTH")),
                (soil, soil_profile)
            ))
            continue
        gs.add_treatment(
            soil_profile=soil_profile,
            weather=os.path.join(tmp_dir_name, f"{dssat_weather._name}.WTH"),
            nitrogen=nitrogen,
            planting=planting,
            cultivar=cultivar
        )
    if return_input:
        return input_files
    # Run DSSAT
    if close_connection:
        con.close()
    # Set automatic management
    planting_window_start = plantingdate - timedelta(days=15)
    planting_window_end = plantingdate + timedelta(days=15)
    sim_controls = {
        "PLANT": "F",  # Automatic, force in last day of window
        "PFRST": planting_window_start.strftime("%y%j"),
        "PLAST": planting_window_end.strftime("%y%j"),
        "PH2OL": 50, "PH2OU": 100, "PH2OD": 20,
        "PSTMX": 40, "PSTMN": 10
    }
    # Get run kwargs if defined
    sim_controls = sim_controls
    out = gs.run(
        start_date=start_date,
        sim_controls=sim_controls
    )
    tmp_dir.cleanup()
    # print("")
    if overview:
        print(out)
        return out, gs.overview
    return out
    # return JsonResponse({'out': out})


@csrf_exempt
def validation_chart_home():
    adminBase = 'Nakuru'
    # adminBase=admin1
    my_chart = Chart()
    my_chart.container = 'chart'
    my_chart.options = HighchartsOptions()
    my_chart.options.title = {
        'text': f'Observed and Simulated yield for the baseline scenario in {adminBase}',
        "style": {
            "font-size": "15px"
        }
    }
    my_chart.options.y_axis = {
        "title": {
            'text': 'Yield (kg/ha)',
            "style": {
                "font-size": "15px"
            }
        },
        "labels": {
            "style": {
                "font-size": "15px",
            }
        }
    }
    my_chart.options.x_axis = {
        "title": {
            'text': 'Year',
            "style": {
                "font-size": "15px",
            }
        },
        "labels": {
            "style": {
                "font-size": "15px",
            }
        }
    }
    my_chart.options.tooltip = {
        "header_format": '<span style="font-size: 12px; font-weight: bold">{point.key}</span><br/>',
        "point_format": '<span style="color:{point.color};font-size: 12px">\u25CF </span>' + \
                        '<span style="font-size: 12px">{series.name}</span><br/>'
    }
    my_chart.options.legend = Legend(
        label_format='<span style="font-size: 12px">{name}</span><br/>'
    )
    con = db.connect('dssatserv')
    schema = 'kenya'
    admin1 = adminBase
    baseline_data = db.fetch_baseline_run(con, schema, admin1)
    baseline_run = baseline_data.loc[
        baseline_data.year.isin(BASELINE_YEARS)
    ]

    baseline_stats = baseline_quantile_stats(baseline_run)
    validation_run = baseline_data.dropna()
    tmp_df = validation_run
    for n, qrange in enumerate(Q_RANGE_PLOTS):
        data = columnRange_data(tmp_df, qrange)
        column = ColumnRangeSeries().from_array(data)
        column.name = f"Simulated yield ({SERIES_CI[n]}% CI)"
        column.color = COLORS[n]
        column.grouping = False
        column.border_width = 0.
        my_chart.add_series(column)
    # Observed scatterplot
    data = tmp_df.groupby("year").obs.mean().round(3).reset_index().to_numpy()
    scatter = ScatterSeries().from_array(data)
    scatter.name = "Observed"
    scatter.color = "#ff3300"
    scatter.marker = {"symbol": "square", "radius": 6}

    my_chart.add_series(scatter)
    return my_chart


@csrf_exempt
def validation_chart(request, admin1):
    # admin1=request.POST.get('admin1')
    adminBase = admin1
    my_chart = Chart()
    tooltip = {
        "header_format": '<span style="font-size: 12px; font-weight: bold">{point.key}</span><br/>',
        "point_format": '<span style="color:{point.color};font-size: 12px">\u25CF </span>' + \
                        '<span style="font-size: 12px">{series.name}</span><br/>'
    }
    legend = Legend(
        label_format='<span style="font-size: 12px">{name}</span><br/>'
    )
    con = db.connect('dssatserv')
    schema = 'kenya'
    admin1 = adminBase
    baseline_data = db.fetch_baseline_run(con, schema, admin1)
    baseline_run = baseline_data.loc[
        baseline_data.year.isin(BASELINE_YEARS)
    ]
    pars = db.fetch_baseline_pars(con, schema, admin1)
    baseline_pars = SimulationPars(
        nitrogen_dap=(5, 30, 60),
        nitrogen_rate=tuple([pars["nitrogen"] / 3] * 3),
        cultivar=pars["cultivar"],
        planting_date=datetime(BASELINE_YEARS[-1], pars["planting_month"], 1)
    )
    cultivar = baseline_pars.cultivar
    plantingdate = baseline_pars.planting_date
    nitro = sum(baseline_pars.nitrogen_rate)
    tmp_df = db.fetch_cultivars(con, schema, admin1)
    tmp_df["yield_avg"] = (tmp_df.yield_avg / 1000).round(1)
    tmp_df = tmp_df.set_index(["yield_avg", "season_length"])
    cultivars = tmp_df.sort_index()

    cultivar_labels = dict(zip(
        cultivars.cultivar,
        cultivars.index.map(
            lambda x: f"{x[0]} kg/ha pot. - {x[1]} days mat."
        ),
    ))
    cultivar = cultivars.loc[cultivars.cultivar == cultivar].iloc[0]
    desc = f"Baseline was estimated assuming a {cultivar.name[1]} " + \
           f"days {cultivar.yield_category} " + \
           f"yield potential cultivar ({cultivar.name[0]} t/ha) " + \
           f"planted on {plantingdate.strftime('%B')} " + \
           f"and fertilized with {nitro:.0f} kg of Nitrogen"

    baseline_stats = baseline_quantile_stats(baseline_run)
    validation_run = baseline_data.dropna()
    tmp_df = validation_run
    columns = []
    for n, qrange in enumerate(Q_RANGE_PLOTS):
        data = columnRange_data(tmp_df, qrange)
        column = ColumnRangeSeries().from_array(data)
        column.name = f"Simulated yield ({SERIES_CI[n]}% CI)"
        column.color = COLORS[n]
        column.grouping = False
        column.border_width = 0.
        columns.append(json.loads(column.to_json()))
        my_chart.add_series(column)
    # Observed scatterplot
    data = tmp_df.groupby("year").obs.mean().round(3).reset_index().to_numpy()
    scatter = ScatterSeries().from_array(data)
    scatter.name = "Observed"
    scatter.color = "#ff3300"
    scatter.marker = {"symbol": "square", "radius": 6}

    # my_chart.add_series(scatter)
    return columns, scatter, desc, list(cultivar_labels.keys()), list(cultivar_labels.values())


def baseline_quantile_stats(obj):
    """
    Calculates the mean and std for each quantile in the baseline run.
    """
    baseline_df = obj
    baseline_stats = (
        baseline_df
        .groupby(["year"]).sim
        .quantile(QUANTILES_TO_COMPARE)
        .reset_index().rename(columns={"level_1": "quantile"})
        .groupby("quantile").sim
        .agg(["mean", "std"])
    )
    return baseline_stats


def init_columnRange_chart():
    my_chart = Chart()
    my_chart.options = HighchartsOptions()
    my_chart.container = 'column_chart'
    my_chart.options.title = {
        'text': 'DSSAT simulated maize yield',
        "style": {
            "font-size": "15px"
        }
    }
    my_chart.options.y_axis = {
        "title": {
            'text': 'Yield (kg/ha)',
            "style": {
                "font-size": "15px"
            }
        },
        "labels": {
            "style": {
                "font-size": "15px",
            }
        },
    }
    my_chart.options.x_axis = {
        "title": {
            'text': 'Experiment',
            "style": {
                "font-size": "15px",
            }
        },
        "labels": {
            "style": {
                "font-size": "15px",
            }
        }
    }
    my_chart.options.tooltip = {
        "header_format": '<span style="font-size: 12px; font-weight: bold">{point.key}</span><br/>',
        "point_format": '<span style="color:{point.color};font-size: 12px">\u25CF </span>' + \
                        '<span style="font-size: 12px">{series.name}</span><br/>'
    }
    my_chart.options.legend = Legend(
        label_format='<span style="font-size: 12px">{name}</span><br/>'
    )
    for n, _ in enumerate(Q_RANGE_PLOTS):
        my_chart.add_series(
            ColumnRangeSeries(
                name=f"Simulated yield ({SERIES_CI[n]}% CI)",
                color=COLORS[n], grouping=False, border_width=0.
            )
        )
    return my_chart


def init_anomalies_chart():
    """
    Creates and returns an anomaly chart
    """
    my_chart = Chart()
    my_chart.options = HighchartsOptions()
    my_chart.container = 'anomaly_chart'
    my_chart.options.title = {
        'text': 'DSSAT simulated maize yield anomaly probability',
        "style": {
            "font-size": "15px"
        }
    }
    my_chart.options.y_axis = {
        "title": {
            'text': 'Probability (%)',
            "style": {
                "font-size": "15px"
            }
        },
        "labels": {
            "style": {
                "font-size": "15px",
            }
        },
        "max": 100
    }
    my_chart.options.x_axis = {
        "title": {
            'text': 'Experiment',
            "style": {
                "font-size": "15px",
            }
        },
        "labels": {
            "style": {
                "font-size": "15px",
            }
        }
    }
    for name, color in zip(CAT_NAMES[::-1], CAT_COLORS[::-1]):
        box = ColumnSeries()
        box.name = name
        box.color = color
        box.data = []
        my_chart.add_series(box)
        box.stacking = 'normal'
        box.data_labels = {
            "enabled": True
        }
    my_chart.options.tooltip = {
        "header_format": '<span style="font-size: 12px; font-weight: bold">{point.key}</span><br/>',
        "point_format": '<span style="color:{point.color};font-size: 12px">\u25CF </span>' + \
                        '<span style="font-size: 12px">{series.name}</span><br/>'
    }
    my_chart.options.legend = Legend(
        label_format='<span style="font-size: 12px">{name}</span><br/>'
    )
    return my_chart


def init_stress_chart(stress_type, container):
    """
    Returns an stress chart. stress_type is water or nitrogen
    """
    assert stress_type in STRESS_COLUMNS
    my_chart = Chart()
    my_chart.options = HighchartsOptions()
    my_chart.container = container
    my_chart.options.title = {
        'text': f'{stress_type.title()} stress',
        "style": {
            "font-size": "15px"
        }
    }
    my_chart.options.y_axis = {
        "title": {
            'text': f'Stress (%)',
            "style": {
                "font-size": "15px"
            }
        },
        "labels": {
            "style": {
                "font-size": "15px",
            }
        },
        "max": 100
    }
    my_chart.options.x_axis = {
        "title": {
            'text': 'Crop Dev. Stage',
            "style": {
                "font-size": "15px",
            }
        },
        "labels": {
            "style": {
                "font-size": "15px",
            },
            "auto_rotation_limit": 0,
            "allow_overlap": True
        },
        "categories": DEV_STAGES_LABELS
    }
    return my_chart


@csrf_exempt
def run_experiment(request,admin1):
    # admin1 = request.POST.get('admin1')
    nitrogen_dap = request.POST.getlist('nitrogen_dap[]')
    nitrogen_rate = request.POST.getlist('nitrogen_rate[]')
    series = request.POST.get('chart')
    print(nitrogen_rate)
    print(nitrogen_dap)
    planting_date = datetime.strptime(request.POST.get('planting_date'), '%Y-%m-%d')
    print(planting_date)
    cultivar = request.POST.get('cultivar')
    admin1 = admin1
    nitro = list(zip(nitrogen_dap, nitrogen_rate))
    plantingdate = datetime(
        planting_date.year,
        planting_date.month,
        planting_date.day
    )
    planting_window_start = plantingdate - timedelta(days=5)
    planting_window_end = plantingdate + timedelta(days=5)
    sim_controls = {
        "PLANT": "F",  # Automatic, force in last day of window
        "PFRST": planting_window_start.strftime("%y%j"),
        "PLAST": planting_window_end.strftime("%y%j"),
    }
    # df = run_spatial_dssat( request,admin1
    #     # dbname="",
    #     # con= db.connect('dssatserv'),
    #     # schema= 'kenya',
    #     # admin1=admin1,
    #     # plantingdate=plantingdate,
    #     # cultivar=cultivar,
    #     # nitrogen=nitro,
    #     # overview=True,
    #     # all_random=True,
    #     # sim_controls=sim_controls
    # )
    latest_run = pd.DataFrame({
        "HARWT": (np.random.normal(0, 1, 50) * 100) + 500
    })

    yield_range = (
            latest_run.HARWT.astype(float) / 1000
    ).quantile((.05, .95)).values
    # harvest_range = (
    #     latest_run.MAT.astype(int)
    # ).quantile((.05, .95)).values
    # tmp_df = pd.DataFrame([{
    #     "planting":planting_date,
    #     "nitro_dap": nitrogen_dap,
    #     "nitro_rate":nitrogen_rate,
    #     "cultivar": cultivar,
    #     "yield_range": tuple(yield_range),
    #     "harvest_range": tuple(map(int, harvest_range))
    # }])
    # experiment_results = tmp_df
    # chart=Chart(id="column_chart"
    #             )

    # data = add_yield_column(cultivar, latest_run, admin1, planting_date,
    #                         nitrogen_rate, qrange=(.05, .95))
    water_series = add_stress_bar(series, 'watStress')
    nitrogen_series = add_stress_bar(series, 'nitroStress')
    # return JsonResponse({'water_series': (water_series.to_json()), 'nitrogen_series': nitrogen_series.to_json(),
    #                      'yield_series': data})
    return JsonResponse({'water_series': (water_series.to_json()), 'nitrogen_series': nitrogen_series.to_json(),
                         })


def add_yield_column(cultivar, latest_run, admin1, planting_date, nitrogen_rate, series_idx=0,
                     qrange=(.05, .95)):
    tmp_df = latest_run
    tmp_df['year'] = 1
    tmp_df["sim"] = tmp_df.HARWT.astype(float) / 1000
    data = dict(zip(("low", "high"), columnRange_data(tmp_df, qrange)[0][1:]))
    con = db.connect('dssatserv')
    schema = 'kenya'
    tmp_df = db.fetch_cultivars(con, schema, admin1)
    tmp_df["yield_avg"] = (tmp_df.yield_avg / 1000).round(1)
    tmp_df = tmp_df.set_index(["yield_avg", "season_length"])
    cultivars = tmp_df.sort_index()

    cultivar_labels = dict(zip(
        cultivars.cultivar,
        cultivars.index.map(
            lambda x: f"{x[0]} kg/ha pot. - {x[1]} days mat."
        ),
    ))
    print(cultivar)
    print(cultivar_labels)
    nrate = []
    for x in nitrogen_rate:
        nrate.append(float(x))

    label = f"{cultivar_labels[cultivar]}<br>" + \
            f"Planted on {planting_date.strftime('%b %d %Y')}<br>" + \
            f"{sum(nrate):.0f} kg N/ha applied in {len(nitrogen_rate)} events"

    data["name"] = label
    data["x"] = label

    return data


def add_stress_bar(series, column_type):
    "data is pandas.Series with the dev stage as index"
    with open(os.path.join(config['OVERVIEW_PATH'], "OVERVIEW.OUT"), 'r') as f:
        overview_copy = f.readlines()
        overview = process_overview(overview_copy.copy())
        var_column = column_type
        data = overview.groupby("devPhase")[var_column].mean()
        data = 100 * data
        box = ColumnSeries()
        box.data = [data.to_dict().get(dev_st) for dev_st in DEV_STAGES]
        if series is None:
            n = 0
        else:
            n = len(series)
        box.name = f"Exp {n}"
        print(box)
        # chart.add_series(box)
        return box


@csrf_exempt
def baseline(request,admin1):
    # admin1 = request.POST.get('admin1')
    columns, scatter, desc, cultivar_keys, cultivar_values = validation_chart(request, admin1)

    column_chart = init_columnRange_chart()
    anomaly_chart = init_anomalies_chart()
    stress_chart_water = init_stress_chart('water', 'stress_chart_water')
    stress_chart_nitrogen = init_stress_chart('nitrogen', 'stress_chart_nitrogen')

    # sFile = open(config['PATH_TO_ZIMBABWE'], "rb")
    gdf = gpd.read_file(config['PATH_TO_KENYA'])
    # gdf = gpd.read_file(sFile)
    data = json.loads(json.dumps(gdf.to_json()))
    temp = scatter.to_dict()
    scatter_json = {'data': []}
    x = list(temp['data']['ndarray']['x'])
    y = list(temp['data']['ndarray']['y'])
    for i in range(len(x)):
        scatter_json['data'].append({'x': x[i], 'y': y[i]})
    scatter_json['name'] = temp['name']
    scatter_json['marker'] = temp['marker']
    scatter_json['color'] = temp['color']
    scatter_json['type'] = temp['type']

    return JsonResponse({'desc': desc, 'cultivar_keys': cultivar_keys, 'cultivar_values': cultivar_values,
                         'scatter1': scatter_json, 'column1': columns, 'data': data,
                         'column_chart': column_chart.to_js_literal(),
                         'anomaly_chart': anomaly_chart.to_js_literal(),
                         'stress_chart_water': stress_chart_water.to_js_literal(),
                         'stress_chart_nitrogen': stress_chart_nitrogen.to_js_literal()})
