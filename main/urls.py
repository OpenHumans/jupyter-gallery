from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('complete/', views.complete, name='complete'),
    path('rescuetime/complete/', views.rescuetime_complete, name='rescuetime_complete'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('update_data/', views.update_data, name='update_data'),
    path('remove_rescuetime/', views.remove_rescuetime, name='remove_rescuetime')
]
