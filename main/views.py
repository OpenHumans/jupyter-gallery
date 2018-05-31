import logging
import requests
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.shortcuts import render, redirect
from django.conf import settings
from open_humans.models import OpenHumansMember
from ohapi import api
from .helpers import get_notebook_files, get_notebook_oh, download_notebook_oh
from .models import SharedNotebook
from django.http import HttpResponse
import arrow
import nbconvert, nbformat
# Set up logging.
logger = logging.getLogger(__name__)


def index(request):
    """
    Starting page for app.
    """
    if request.user.is_authenticated:
        return redirect('/dashboard')
    else:
        context = {'client_id': settings.OPENHUMANS_CLIENT_ID,
                   'redirect_uri':
                   settings.OPENHUMANS_APP_BASE_URL + '/complete',
                   'oh_proj_page': settings.OH_ACTIVITY_PAGE}

        return render(request, 'main/index.html', context=context)


def complete(request):
    """
    Receive user from Open Humans. Store data, start upload.
    """
    print("Received user returning from Open Humans.")
    # Exchange code for token.
    # This creates an OpenHumansMember and associated user account.
    code = request.GET.get('code', '')
    oh_member = oh_code_to_member(code=code)

    if oh_member:
        # Log in the user.
        user = oh_member.user
        login(request, user,
              backend='django.contrib.auth.backends.ModelBackend')
        return redirect("/dashboard")

    logger.debug('Invalid code exchange. User returned to starting page.')
    return redirect('/')


@login_required(login_url='/')
def dashboard(request):
    oh_member = request.user.oh_member
    context = {
        'oh_member': oh_member,
    }
    oh_member_data = api.exchange_oauth2_member(oh_member.get_access_token())
    if 'data' not in oh_member_data.keys():
        messages.error(request, "You need to re-authenticate with Open Humans")
        logout(request)
        return redirect("/")
    all_available_notebooks = get_notebook_files(oh_member_data)
    existing_notebooks = SharedNotebook.objects.filter(oh_member=oh_member)
    context['notebook_files'] = all_available_notebooks
    context['existing_notebooks'] = existing_notebooks
    return render(request, 'main/dashboard.html',
                  context=context)


@login_required(login_url='/')
def add_notebook(request, notebook_id):
    oh_member = request.user.oh_member
    oh_member_data = api.exchange_oauth2_member(oh_member.get_access_token())
    notebook_name, notebook_url = get_notebook_oh(oh_member_data, notebook_id)
    if request.method == 'POST':
        notebook_content = download_notebook_oh(notebook_url)
        notebook, created = SharedNotebook.objects.get_or_create(
                                                oh_member=oh_member,
                                                notebook_name=notebook_name)
        notebook.description = request.POST.get('description')
        notebook.tags = request.POST.get('tags')
        notebook.notebook_name = notebook_name
        notebook.notebook_content = notebook_content.decode()
        notebook.updated_at = arrow.now().format()
        notebook.oh_member = oh_member
        if created:
            notebook.created_at = arrow.now().format()
        notebook.save()
        messages.info(request, 'Your Notebook {} has been shared!'.format(
            notebook_name
        ))
        return redirect('/dashboard')
    else:
        if len(SharedNotebook.objects.filter(oh_member=oh_member,
                                             notebook_name=notebook_name)) > 0:
            existing_notebook = SharedNotebook.objects.get(
                                        oh_member=oh_member,
                                        notebook_name=notebook_name)
            context = {'description': existing_notebook.description,
                       'tags': existing_notebook.tags,
                       'name': notebook_name,
                       'notebook_id': str(notebook_id),
                       'edit': True}
        else:
            context = {'description': '',
                       'name': notebook_name,
                       'notebook_id': str(notebook_id),
                       'tags': ''}
        return render(request, 'main/add_notebook.html', context=context)


def render_notebook(request, notebook_id):
    notebook = SharedNotebook.objects.get(pk=notebook_id)
    format_notebook = nbformat.reads(notebook.notebook_content,
                                     as_version=nbformat.NO_CONVERT)
    html_exporter = nbconvert.HTMLExporter()
    html_exporter.template_file = 'full'
    (body, resources) = html_exporter.from_notebook_node(format_notebook)
    print(body)
    return HttpResponse(body)


def export_notebook(request, notebook_id):
    notebook = SharedNotebook.objects.get(pk=notebook_id)
    return HttpResponse(notebook.notebook_content,
                        content_type='application/json')


def oh_code_to_member(code):
    """
    Exchange code for token, use this to create and return OpenHumansMember.
    If a matching OpenHumansMember exists, update and return it.
    """
    if settings.OPENHUMANS_CLIENT_SECRET and \
       settings.OPENHUMANS_CLIENT_ID and code:
        data = {
            'grant_type': 'authorization_code',
            'redirect_uri':
            '{}/complete'.format(settings.OPENHUMANS_APP_BASE_URL),
            'code': code,
        }
        req = requests.post(
            '{}/oauth2/token/'.format(settings.OPENHUMANS_OH_BASE_URL),
            data=data,
            auth=requests.auth.HTTPBasicAuth(
                settings.OPENHUMANS_CLIENT_ID,
                settings.OPENHUMANS_CLIENT_SECRET
            )
        )
        data = req.json()

        if 'access_token' in data:
            oh_id = api.exchange_oauth2_member(
                data['access_token'])['project_member_id']
            try:
                oh_member = OpenHumansMember.objects.get(oh_id=oh_id)
                logger.debug('Member {} re-authorized.'.format(oh_id))
                oh_member.access_token = data['access_token']
                oh_member.refresh_token = data['refresh_token']
                oh_member.token_expires = OpenHumansMember.get_expiration(
                    data['expires_in'])
            except OpenHumansMember.DoesNotExist:
                oh_member = OpenHumansMember.create(
                    oh_id=oh_id,
                    access_token=data['access_token'],
                    refresh_token=data['refresh_token'],
                    expires_in=data['expires_in'])
                logger.debug('Member {} created.'.format(oh_id))
            oh_member.save()

            return oh_member

        elif 'error' in req.json():
            logger.debug('Error in token exchange: {}'.format(req.json()))
        else:
            logger.warning('Neither token nor error info in OH response!')
    else:
        logger.error('OH_CLIENT_SECRET or code are unavailable')
    return None
