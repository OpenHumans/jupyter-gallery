import requests
from django.conf import settings
from django.urls import reverse
from main.models import SharedNotebook


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


def find_notebook_by_keywords(search_term, search_field=None):
    notebooks_tag = SharedNotebook.objects.filter(tags__contains=search_term)
    if search_field == 'tags':
        return notebooks_tag
    notebooks_source = SharedNotebook.objects.filter(
                        data_sources__contains=search_term)
    if search_field == 'data_sources':
        return notebooks_source
    notebooks_user = SharedNotebook.objects.filter(
                        oh_member__oh_username__contains=search_term)
    if search_field == 'username':
        return notebooks_user
    notebooks_description = SharedNotebook.objects.filter(
                        description__contains=search_term)
    notebooks_name = SharedNotebook.objects.filter(
                        notebook_name__contains=search_term)

    nbs = notebooks_tag | notebooks_source | notebooks_description | notebooks_name | notebooks_user
    return nbs
