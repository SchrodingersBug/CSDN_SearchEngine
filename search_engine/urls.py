from django.urls import path
from django.urls import include
from .views import *


urlpatterns = [
    path('', index, name='index'),
    path('index/', index, name='index'),
    path('results/', results, name='results'),
]
