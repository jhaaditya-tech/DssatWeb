from pathlib import Path

import pandas
from django.shortcuts import render
from pandas_highcharts.core import serialize
import os
import geopandas as gpd
import json

# Create your views here.
import geojson
BASE_DIR = Path(__file__).resolve().parent.parent
f = open(str(BASE_DIR) + '/data.json', )
config = json.load(f)

def get_geojson():
    import pandas as pd
    data = pd.read_json('C:\\Users\\gtondapu\\Downloads\\zimbabwe_fewsnet_admin2.geojson')
    import json
    data = json.load(open('C:\\Users\\gtondapu\\Downloads\\zimbabwe_fewsnet_admin2.geojson'))

    return data["result"]


def home(request):
    import pandas as pd

    chart = serialize(pandas.DataFrame(), render_to="chart", output_type='json', type='spline',
                      xticks='',
                      title='test1')

    # sFile = open(config['PATH_TO_ZIMBABWE'], "rb")
    gdf = gpd.read_file(config['PATH_TO_KENYA'])
    # gdf = gpd.read_file(sFile)
    data = json.loads(json.dumps(gdf.to_json()))

    return render(request, 'index.html', {'name': 'DSSAT Web', 'chart': chart, 'data':data })
