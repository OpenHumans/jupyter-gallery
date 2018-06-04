import requests
from django.conf import settings
from django.urls import reverse


def get_notebook_files(oh_member_data):
    files = [i for i in oh_member_data['data']
             if i['source'] == 'direct-sharing-71']
    return files


def get_notebook_oh(oh_member_data, notebook_id):
    for data_object in oh_member_data['data']:
        if str(data_object['id']) == notebook_id:
            return (data_object['basename'], data_object['download_url'])


def download_notebook_oh(notebook_url):
    notebook_content = requests.get(notebook_url).content
    return notebook_content


def create_notebook_link(notebook, request):
    base_url = request.build_absolute_uri("/").rstrip('/')
    jupyterhub_url = settings.JUPYTERHUB_BASE_URL
    export_url = reverse('export-notebook', args=(notebook.id,))
    notebook_link = '{}/gallery-import?notebook_location={}{}&notebook_name={}'.format(
        jupyterhub_url,
        base_url,
        export_url,
        notebook.notebook_name
    )
    return notebook_link
