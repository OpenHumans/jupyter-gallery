import logging
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.shortcuts import render, redirect
from django.conf import settings
from ohapi import api
from .helpers import get_notebook_files, get_notebook_oh, download_notebook_oh
from .helpers import find_notebook_by_keywords, get_all_data_sources
from .helpers import suggest_data_sources, add_notebook_helper
from .helpers import paginate_items, oh_code_to_member
from .helpers import get_all_data_sources_numeric
from .models import SharedNotebook
import arrow
import json
from django.db.models import Count
from django.urls import reverse
from django.http import JsonResponse

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
        latest_notebooks = SharedNotebook.objects.filter(
            master_notebook=None).order_by('-views')[:5]
        data_sources = get_all_data_sources()[:6]
        context = {'oh_proj_page': settings.OH_ACTIVITY_PAGE,
                   'latest_notebooks': latest_notebooks,
                   'data_sources': data_sources}

        return render(request, 'main/index.html', context=context)


def data_source_index(request):
    data_sources = get_all_data_sources_numeric()
    return render(request, 'main/sources_index.html', {
                'section': 'sources',
                'data_sources': data_sources})


def about(request):
    return render(request, 'main/about.html', {'section': 'about'})


@login_required(login_url="/")
def delete_user(request):
    if request.method == "POST":
        request.user.delete()
        messages.info(request, "Your account was deleted!")
        logout(request)
    return redirect('index')


def complete(request):
    """
    Receive user from Open Humans. Store data, start upload.
    """
    # print("Received user returning from Open Humans.")
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
    context = {
        'notebook_files': all_available_notebooks,
        'existing_notebooks': existing_notebooks,
        'JH_URL': settings.JUPYTERHUB_BASE_URL,
        'base_url': request.build_absolute_uri("/").rstrip('/'),
        'section': 'dashboard'}
    return render(request, 'main/dashboard.html',
                  context=context)


@login_required(login_url='/')
def likes(request):
    oh_member = request.user.oh_member
    liked_notebook_list = oh_member.notebooklike_set.all().order_by('-created_at')
    liked_notebooks = paginate_items(
                        liked_notebook_list,
                        request.GET.get('page'))
    return render(request, 'main/likes.html',
                  context={'liked_notebooks': liked_notebooks,
                           'section': 'likes'})


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
        add_notebook_helper(request, notebook_url, notebook_name, oh_member)
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
    if request.method == "POST":
        oh_member = request.user.oh_member
        notebook = SharedNotebook.objects.get(pk=notebook_id)
        if notebook.oh_member != oh_member:
            messages.warning(request, 'Permission denied!')
            return redirect("/")
        notebook.delete()
        messages.info(request, 'Deleted {}!'.format(notebook.notebook_name))
        return redirect("/dashboard")


def notebook_index(request):
    order_variable = request.GET.get('order_by', 'updated_at')
    data_sources = get_all_data_sources()
    data_sources = sorted(data_sources)
    if order_variable not in ['updated_at', 'likes', 'views']:
        order_variable = 'updated_at'
    source_filter = request.GET.get('source', None)
    if source_filter:
        notebook_list = find_notebook_by_keywords(
                            source_filter,
                            search_field='data_sources')
    else:
        notebook_list = SharedNotebook.objects.filter(
            master_notebook=None)
    if order_variable == 'likes':
        notebook_list = notebook_list.annotate(
            likes=Count('notebooklike'))
    notebook_list = notebook_list.order_by('-{}'.format(order_variable))
    notebooks = paginate_items(notebook_list, request.GET.get('page'))
    return render(request,
                  'main/notebook_index.html',
                  {'notebooks': notebooks,
                   'section': 'explore',
                   'order_by': order_variable,
                   'data_sources': data_sources,
                   'source': source_filter})


def search_notebooks(request):
    if request.method == "POST":
        search_term = request.POST.get('search_term')
        notebook_list = find_notebook_by_keywords(search_term)
    else:
        search_term = request.GET.get('search_term', '')
        search_field = request.GET.get('search_field', None)
        notebook_list = find_notebook_by_keywords(search_term, search_field)
    order_variable = request.GET.get('order_by', 'updated_at')
    if order_variable not in ['updated_at', 'likes', 'views']:
        order_variable = 'updated_at'
    if order_variable == 'likes':
        notebook_list = notebook_list.annotate(
            likes=Count('notebooklike'))
    notebook_list = notebook_list.order_by('-{}'.format(order_variable))
    notebooks = paginate_items(notebook_list, request.GET.get('page'))
    return render(request,
                  'main/search.html',
                  {'notebooks': notebooks,
                   'order_by': order_variable,
                   'search_term': search_term})


def notebook_by_source(request):
    source_name = request.GET.get('source')
    notebook_list = []
    notebooks = SharedNotebook.objects.filter(
                        data_sources__contains=source_name,
                        master_notebook=None)
    notebooks = notebooks.annotate(
        likes=Count('notebooklike'))
    for notebook in notebooks:
        notebook_list.append(
            {
                'name': notebook.notebook_name,
                'user': notebook.oh_member.oh_username,
                'description': notebook.description,
                'views': notebook.views,
                'likes': notebook.likes,
                'details_url': request.build_absolute_uri(
                    reverse('notebook-details', args=[notebook.id])),
                'preview_url': request.build_absolute_uri(
                    reverse('render-notebook', args=[notebook.id])),
                'open_url': request.build_absolute_uri(
                    reverse('open-notebook', args=[notebook.id])
                )
            }
        )
    notebook_list = sorted(
        notebook_list,
        key=lambda k: k['views'], reverse=True)
    output = {
        'source_name': source_name, 'hits': len(notebook_list),
        'notebooks': notebook_list}
    return JsonResponse(output)
