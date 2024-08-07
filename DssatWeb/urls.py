"""DssatWeb URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin

from dssat.api import regions_geojson
from dssat.api import run_experiment
from dssat.views import home, charts, about
from django.urls import path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('',home,name='home'),
    # path('run-spatial-dssat/',run_spatial_dssat,name='run-spatial-dssat'),
    path('charts/<str:admin1>/',charts,name='charts'),
    path('charts/validation-chart/<str:admin1>/',home,name='validation-chart'),
    # path('charts/<str:admin1>/baseline-chart/',baseline,name='baseline-chart'),
    path('charts/<str:admin1>/run-experiment/',run_experiment,name='run-experiment'),
    path('get-regions/',regions_geojson,name='regions-geojson'),
    path('about/',about,name='about'),
]
