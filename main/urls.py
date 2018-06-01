from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('complete/', views.complete, name='complete'),
    path('logout/', views.logout_user, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('notebooks/', views.notebook_index, name='notebook-index'),
    path('notebook/<notebook_id>/',
         views.notebook_details,
         name='notebook-details'),
    path('add-notebook-gallery/<notebook_id>/',
         views.add_notebook,
         name='add-notebook-gallery'),
    path('edit-notebook/<notebook_id>/',
         views.edit_notebook,
         name='edit-notebook'),
    path('render-notebook/<notebook_id>/',
         views.render_notebook,
         name='render-notebook'),
    path('delete-notebook/<notebook_id>/',
         views.delete_notebook,
         name='delete-notebook'),
    path('export-notebook/<notebook_id>/',
         views.export_notebook,
         name='export-notebook')

]
