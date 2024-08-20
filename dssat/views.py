from datetime import datetime
from pathlib import Path

import pandas
import psycopg2
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from highcharts_core.chart import Chart
from pandas_highcharts.core import serialize
import os
import geopandas as gpd
import json

# Create your views here.
import geojson

from dssatservice.ui.base import AdminBase, Session
from dssatservice.ui.plot import init_anomalies_chart, init_stress_chart, get_stress_series_data, \
    get_anomaly_series_data, get_columnRange_series_data, init_columnRange_chart, clear_yield_chart, clear_stress_chart
from dssat.api import  init_columnRange, validation_ch

BASE_DIR = Path(__file__).resolve().parent.parent
f = open(str(BASE_DIR) + '/data.json', )
config = json.load(f)
def connect(dbname):
    con = psycopg2.connect(
        database=config['USERNAME'],
        user=config['DBUSER'],
        password=config['PASSWORD'],
        host=config['HOST'],
        port=5432,
    )

    return con


con = connect(config['USERNAME'])
session = Session(
    AdminBase(con, 'kenya', 'Nakuru')
)

anom_chart = init_anomalies_chart()
r_chart = init_columnRange_chart(session)
anom_chart.container = 'anomaly_chart'
r_chart.container = 'column_chart'
range_chart = r_chart.to_dict()
anomaly_chart = anom_chart.to_dict()
stress_chart_water = init_stress_chart('water')
stress_chart_water.container = 'stress_chart_water'
stress_chart_nitrogen = init_stress_chart('nitrogen')
sw = stress_chart_water.to_dict()
stress_chart_nitrogen.container = 'stress_chart_nitrogen'
sn = stress_chart_nitrogen.to_dict()


def get_geojson():
    import pandas as pd
    data = pd.read_json('C:\\Users\\gtondapu\\Downloads\\zimbabwe_fewsnet_admin2.geojson')
    import json
    data = json.load(open('C:\\Users\\gtondapu\\Downloads\\zimbabwe_fewsnet_admin2.geojson'))

    return data["result"]


def home(request,admin1='Nakuru'):
    # column,scatter,desc,cultivars,x = validation_chart(request,admin1)
    #
    # column_chart = init_columnRange_chart()
    # anomaly_chart = init_anomalies_chart()
    # stress_chart_water = init_stress_chart('water', 'stress_chart_water')
    # stress_chart_nitrogen = init_stress_chart('nitrogen', 'stress_chart_nitrogen')
    #
    sFile = open(config['PATH_TO_KENYA'], "rb")
    # gdf = gpd.read_file(config['PATH_TO_KENYA'])
    gdf = gpd.read_file(sFile)
    data = json.loads(json.dumps(gdf.to_json()))
    return render(request, 'index.html', {
                                           'data': data })


def charts(request,admin1='Nakuru_kenya'):
    clear_yield_chart(range_chart)
    clear_stress_chart(sw)
    clear_stress_chart(sn)
    clear_yield_chart(anomaly_chart)
    admin1_name=admin1.split('_')[0]
    admin1_country= admin1.split('_')[1]
    desc,column,cultivars,x= validation_ch(request, admin1)
    global session
    session = Session(
        AdminBase(con, admin1_country, admin1_name)
    )
    sFile = open(config['PATH_TO_KENYA'], "rb")
    # gdf = gpd.read_file(config['PATH_TO_KENYA'])
    gdf = gpd.read_file(sFile)
    data = json.loads(json.dumps(gdf.to_json()))
    return render(request, 'charts.html', {'admin1':admin1_name,'admin1_country':admin1_country,'desc': desc, 'cultivar_keys': cultivars, 'cultivar_values': x,
                                          'chart': column.to_js_literal(), 'data': data,
                                          'range_chart': r_chart.to_js_literal(), 'anomaly_chart': anom_chart.to_js_literal(),'stress_chart_water': stress_chart_water.to_js_literal(),'stress_chart_nitrogen': stress_chart_nitrogen.to_js_literal() })

def about(request):
    return render(request, 'about.html')

@csrf_exempt
def run_experiment(request,admin1):
    try:
        schema = request.POST.get('schema')
        admin1 = request.POST.get('admin1')
        global session
        session.simPars.planting_date=datetime.strptime(request.POST.get('planting_date'), '%Y-%m-%d')
        session.simPars.cultivar=request.POST.get('cultivar')
        session.run_experiment(fakerun=True)
        new_chart_data_range = get_columnRange_series_data(session)
        for serie in range_chart["userOptions"]["series"]:
            if serie.get("data"):
                data=[new_chart_data_range[serie["name"]]['low'],new_chart_data_range[serie["name"]]['high']]
                serie["data"] += [data]
            else:
                data = [new_chart_data_range[serie["name"]]['low'], new_chart_data_range[serie["name"]]['high']]
                serie["data"] = [data]

        # Add data for anomaly chart
        new_chart_data_an = get_anomaly_series_data(session)

        for serie in anomaly_chart["userOptions"]["series"]:
            if serie.get("data"):
                serie["data"] += [new_chart_data_an[serie["name"]]]
            else:
                serie["data"] = [new_chart_data_an[serie["name"]]]

        new_chart_data_water = get_stress_series_data(session, stresstype="water")
        if not sw["userOptions"].get("series"):
            new_chart_data_water["name"] = f"Exp 1"
            sw["userOptions"]["series"] = [new_chart_data_water]
        else:
            n_exps = len(sw["userOptions"]["series"])
            new_chart_data_water["name"] = f"Exp {n_exps + 1}"
            sw["userOptions"]["series"] += [new_chart_data_water]

        new_chart_data_nitro = get_stress_series_data(session, stresstype="nitrogen")
        if not sn["userOptions"].get("series"):
            new_chart_data_nitro["name"] = f"Exp 1"
            sn["userOptions"]["series"] = [new_chart_data_nitro]
        else:
            n_exps = len(sn["userOptions"]["series"])
            new_chart_data_nitro["name"] = f"Exp {n_exps + 1}"
            sn["userOptions"]["series"] += [new_chart_data_nitro]
        return JsonResponse({'error':'','anomaly_chart': anomaly_chart["userOptions"],'aseries':new_chart_data_an,'rdata':new_chart_data_range,'range_chart':range_chart["userOptions"],'stress_chart_water': new_chart_data_water,'stress_chart_nitrogen':new_chart_data_nitro})
    except Exception as e:
        return JsonResponse({'error': str(e)})
@csrf_exempt
def clear_charts(request,admin1):
    try:
        clear_yield_chart(range_chart)
        clear_stress_chart(sw)
        clear_stress_chart(sn)
        clear_yield_chart(anomaly_chart)
        global session
        session=None
        print(sn["userOptions"]["series"])
        return JsonResponse({'error': '', 'anomaly_chart': anomaly_chart["userOptions"],
                             'range_chart': range_chart["userOptions"],
                             'stress_chart_water': sw['userOptions'], 'stress_chart_nitrogen':sn["userOptions"]["series"]})

    except Exception as e:
        print(str(e))
        return JsonResponse({'error': str(e)})