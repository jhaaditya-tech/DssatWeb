from pathlib import Path

import pandas
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from highcharts_core.chart import Chart
from pandas_highcharts.core import serialize
import os
import geopandas as gpd
import json

# Create your views here.
import geojson
from dssatservice.ui.plot import init_anomalies_chart,init_stress_chart
from dssat.api import  init_columnRange, validation_ch

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


def charts(request,admin1='Nakuru_kenya'):
    admin1_name=admin1.split('_')[0]
    admin1_country= admin1.split('_')[1]
    print(admin1)
    desc,column,cultivars,x= validation_ch(request, admin1)
    column_chart = init_columnRange(admin1)
    anomaly_chart = init_anomalies_chart()
    anomaly_chart.container='anomaly_chart'
    column_chart.container = 'column_chart'
    stress_chart_water = init_stress_chart('water')
    stress_chart_water.container='stress_chart_water'
    stress_chart_nitrogen = init_stress_chart('nitrogen')
    stress_chart_nitrogen.container='stress_chart_nitrogen'

    sFile = open(config['PATH_TO_KENYA'], "rb")
    # gdf = gpd.read_file(config['PATH_TO_KENYA'])
    gdf = gpd.read_file(sFile)
    data = json.loads(json.dumps(gdf.to_json()))
    return render(request, 'charts.html', {'admin1':admin1_name,'admin1_country':admin1_country,'desc': desc, 'cultivar_keys': cultivars, 'cultivar_values': x,
                                          'chart': column.to_js_literal(), 'data': data,
                                          'range_chart': column_chart.to_js_literal(), 'anomaly_chart': anomaly_chart.to_js_literal(),'stress_chart_water': stress_chart_water.to_js_literal(),'stress_chart_nitrogen': stress_chart_nitrogen.to_js_literal() })

def about(request):
    return render(request, 'about.html')