import logging
import requests
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.shortcuts import render, redirect
from django.conf import settings
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from open_humans.models import OpenHumansMember
from ohapi import api
from .helpers import get_notebook_files, get_notebook_oh, download_notebook_oh
from .helpers import create_notebook_link, find_notebook_by_keywords
from .helpers import suggest_data_sources
from .models import SharedNotebook, NotebookLike
from django.http import HttpResponse
from django.urls import reverse
import arrow
import nbconvert
import nbformat
import json
# Set up logging.
logger = logging.getLogger(__name__)


def shared(request):
    """
    Users get linked here after clicking export
    on notebooks.openhumans.org
    """
    if request.user.is_authenticated:
        messages.info(request,
                      ("Your notebook was uploaded into your Open Humans "
                       "account and can now be shared from here!"))
        return redirect('/dashboard')
    latest_notebooks = SharedNotebook.objects.all(
        ).order_by('-updated_at')[:10]
    context = {'latest_notebooks': latest_notebooks}
    return render(request, 'main/shared.html', context)


def index(request):
    """
    Starting page for app.
    """
    if request.user.is_authenticated:
        return redirect('/notebooks')
    else:
        latest_notebooks = SharedNotebook.objects.all(
            ).order_by('-updated_at')[:10]
        context = {'oh_proj_page': settings.OH_ACTIVITY_PAGE,
                   'latest_notebooks': latest_notebooks}

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


@login_required(login_url="/")
def logout_user(request):
    """
    Logout user
    """
    if request.method == 'POST':
        logout(request)
    return redirect('index')


@login_required(login_url='/')
def dashboard(request):
    oh_member = request.user.oh_member
    context = {
        'oh_member': oh_member,
    }
    try:
        oh_member_data = api.exchange_oauth2_member(
                            oh_member.get_access_token())
    except:
        messages.error(request, "You need to re-authenticate with Open Humans")
        logout(request)
        return redirect("/")
    all_available_notebooks = get_notebook_files(oh_member_data)
    existing_notebooks = SharedNotebook.objects.filter(oh_member=oh_member)
    context['notebook_files'] = all_available_notebooks
    context['existing_notebooks'] = existing_notebooks
    context['JH_URL'] = settings.JUPYTERHUB_BASE_URL
    context['base_url'] = request.build_absolute_uri("/").rstrip('/')
    context['section'] = 'dashboard'
    return render(request, 'main/dashboard.html',
                  context=context)


@login_required(login_url='/')
def add_notebook(request, notebook_id):
    oh_member = request.user.oh_member
    try:
        oh_member_data = api.exchange_oauth2_member(
                                oh_member.get_access_token())
    except:
        messages.error(request, "You need to re-authenticate with Open Humans")
        logout(request)
        return redirect("/")
    notebook_name, notebook_url = get_notebook_oh(oh_member_data, notebook_id)
    if request.method == 'POST':
        notebook_content = download_notebook_oh(notebook_url)
        notebook, created = SharedNotebook.objects.get_or_create(
                                                oh_member=oh_member,
                                                notebook_name=notebook_name)
        notebook.description = request.POST.get('description')
        tags = request.POST.get('tags')
        tags = [tag.strip() for tag in tags.split(',')]
        notebook.tags = json.dumps(tags)
        data_sources = request.POST.get('data_sources')
        data_sources = [ds.strip() for ds in data_sources.split(',')]
        notebook.data_sources = json.dumps(data_sources)
        notebook.notebook_name = notebook_name
        notebook.notebook_content = notebook_content.decode()
        notebook.updated_at = arrow.now().format()
        notebook.oh_member = oh_member
        if created:
            notebook.created_at = arrow.now().format()
            messages.info(request, 'Your notebook {} has been shared!'.format(
                notebook_name
            ))
        else:
            messages.info(request, 'Your notebook {} has been updated!'.format(
                notebook_name
            ))
        notebook.save()

        return redirect('/dashboard')
    else:
        if len(SharedNotebook.objects.filter(oh_member=oh_member,
                                             notebook_name=notebook_name)) > 0:
            existing_notebook = SharedNotebook.objects.get(
                                        oh_member=oh_member,
                                        notebook_name=notebook_name)
            context = {'description': existing_notebook.description,
                       'tags': existing_notebook.get_tags(),
                       'data_sources': existing_notebook.get_data_sources(),
                       'name': notebook_name,
                       'notebook_id': str(notebook_id),
                       'edit': True}
        else:
            notebook_content = download_notebook_oh(notebook_url)
            suggested_sources = suggest_data_sources(notebook_content)
            context = {'description': '',
                       'name': notebook_name,
                       'notebook_id': str(notebook_id),
                       'tags': '',
                       'data_sources': suggested_sources}
        return render(request, 'main/add_notebook.html', context=context)


@login_required(login_url="/")
def edit_notebook(request, notebook_id):
    oh_member = request.user.oh_member
    notebook = SharedNotebook.objects.get(pk=notebook_id)
    if notebook.oh_member != oh_member:
        messages.warning(request, 'Permission denied!')
        return redirect("/")
    if request.method == "POST":
        notebook.description = request.POST.get('description')
        tags = request.POST.get('tags')
        tags = [tag.strip() for tag in tags.split(',')]
        notebook.tags = json.dumps(tags)
        data_sources = request.POST.get('data_sources')
        data_sources = [ds.strip() for ds in data_sources.split(',')]
        notebook.data_sources = json.dumps(data_sources)
        notebook.updated_at = arrow.now().format()
        notebook.save()
        messages.info(request, 'Updated {}!'.format(notebook.notebook_name))
        return redirect("/dashboard")
    else:
        context = {'description': notebook.description,
                   'tags': notebook.get_tags(),
                   'data_sources': notebook.get_data_sources(),
                   'name': notebook.notebook_name,
                   'notebook_id': str(notebook_id)}
        return render(request, 'main/edit_notebook.html', context=context)


@login_required(login_url="/")
def delete_notebook(request, notebook_id):
    oh_member = request.user.oh_member
    notebook = SharedNotebook.objects.get(pk=notebook_id)
    if notebook.oh_member != oh_member:
        messages.warning(request, 'Permission denied!')
        return redirect("/")
    notebook.delete()
    messages.info(request, 'Deleted {}!'.format(notebook.notebook_name))
    return redirect("/dashboard")


def render_notebook(request, notebook_id):
    notebook = SharedNotebook.objects.get(pk=notebook_id)
    format_notebook = nbformat.reads(notebook.notebook_content,
                                     as_version=nbformat.NO_CONVERT)
    html_exporter = nbconvert.HTMLExporter()
    html_exporter.template_file = 'basic'
    (body, resources) = html_exporter.from_notebook_node(format_notebook)
    return HttpResponse(body)


def export_notebook(request, notebook_id):
    notebook = SharedNotebook.objects.get(pk=notebook_id)
    return HttpResponse(notebook.notebook_content,
                        content_type='application/json')


def open_notebook_hub(request, notebook_id):
    notebook = SharedNotebook.objects.get(pk=notebook_id)
    notebook.views += 1
    notebook.save()
    notebook_link = create_notebook_link(notebook, request)
    return redirect(notebook_link)


def notebook_index(request):
    notebook_list = SharedNotebook.objects.all().order_by('-updated_at')
    paginator = Paginator(notebook_list, 20)
    page = request.GET.get('page')
    try:
        notebooks = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        notebooks = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        notebooks = paginator.page(paginator.num_pages)
    return render(request,
                  'main/notebook_index.html',
                  {'notebooks': notebooks,
                   'section': 'explore'})


def notebook_details(request, notebook_id):
    notebook = SharedNotebook.objects.get(pk=notebook_id)
    liked = False
    if request.user.is_authenticated:
        if notebook.notebooklike_set.filter(oh_member=request.user.oh_member):
            liked = True
    format_notebook = nbformat.reads(notebook.notebook_content,
                                     as_version=nbformat.NO_CONVERT)
    html_exporter = nbconvert.HTMLExporter()
    html_exporter.template_file = 'basic'
    (body, resources) = html_exporter.from_notebook_node(format_notebook)
    return render(request,
                  'main/notebook_details.html',
                  {'notebook': notebook,
                   'notebook_preview': body,
                   'liked': liked})


@login_required(login_url='/')
def like_notebook(request, notebook_id):
    notebook = SharedNotebook.objects.get(pk=notebook_id)
    if notebook.notebooklike_set.filter(oh_member=request.user.oh_member):
        like = NotebookLike.objects.get(oh_member=request.user.oh_member,
                                        notebook=notebook)
        like.delete()
    else:
        like = NotebookLike(notebook=notebook,
                            oh_member=request.user.oh_member)
        like.save()
    return redirect(reverse('notebook-details', args=(notebook_id,)))


def search_notebooks(request):
    if request.method == "POST":
        search_term = request.POST.get('search_term')
        print(search_term)
        print(len(search_term))
        notebook_list = find_notebook_by_keywords(search_term)
    else:
        search_term = request.GET.get('search_term', '')
        search_field = request.GET.get('search_field', None)
        notebook_list = find_notebook_by_keywords(search_term, search_field)
    paginator = Paginator(notebook_list, 20)
    page = request.GET.get('page')
    try:
        notebooks = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        notebooks = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        notebooks = paginator.page(paginator.num_pages)
    return render(request,
                  'main/search.html',
                  {'notebooks': notebooks,
                   'search_term': search_term})


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
                    oh_username=data['username'],
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
