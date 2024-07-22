from pathlib import Path

import pandas
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from pandas_highcharts.core import serialize
import os
import geopandas as gpd
import json

# Create your views here.
import geojson

from dssat.api import validation_chart,init_columnRange_chart,init_anomalies_chart,init_stress_chart

BASE_DIR = Path(__file__).resolve().parent.parent
f = open(str(BASE_DIR) + '/data.json', )
config = json.load(f)

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


def charts(request,admin1='Nakuru'):
    column, scatter, desc, cultivars, x = validation_chart(request, admin1)

    column_chart = init_columnRange_chart()
    anomaly_chart = init_anomalies_chart()
    stress_chart_water = init_stress_chart('water', 'stress_chart_water')
    stress_chart_nitrogen = init_stress_chart('nitrogen', 'stress_chart_nitrogen')

    sFile = open(config['PATH_TO_KENYA'], "rb")
    # gdf = gpd.read_file(config['PATH_TO_KENYA'])
    gdf = gpd.read_file(sFile)
    data = json.loads(json.dumps(gdf.to_json()))
    return render(request, 'charts.html', {'admin1':admin1,'desc': desc, 'cultivars': cultivars,
                                          'chart': column, 'data': data, 'column_chart': column_chart.to_js_literal(),
                                          'anomaly_chart': anomaly_chart.to_js_literal(),
                                          'stress_chart_water': stress_chart_water.to_js_literal(),
                                          'stress_chart_nitrogen': stress_chart_nitrogen.to_js_literal()})

def about(request):
    return render(request, 'about.html')