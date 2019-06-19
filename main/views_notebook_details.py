from django.contrib.auth.decorators import login_required
from .models import SharedNotebook, NotebookLike
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
import nbconvert
import nbformat
from django.urls import reverse
from django.http import HttpResponse
import arrow
from .helpers import create_notebook_link


def notebook_details(request, notebook_id):
    notebook = SharedNotebook.objects.get(pk=notebook_id)
    if notebook.master_notebook:
        other_notebooks = notebook.master_notebook.sharednotebook_set.exclude(
            pk=notebook.id)
    else:
        other_notebooks = notebook.sharednotebook_set.exclude(
            pk=notebook.id)
    liked = False
    if request.user.is_authenticated:
        if notebook.notebooklike_set.filter(oh_member=request.user.oh_member):
            liked = True
    format_notebook = nbformat.reads(notebook.notebook_content,
                                     as_version=nbformat.NO_CONVERT)
    html_exporter = nbconvert.HTMLExporter()
    html_exporter.template_file = 'basic'
    # below also removes output of code
    # html_exporter.exclude_code_cell = True

    (body, resources) = html_exporter.from_notebook_node(format_notebook)
    return render(request,
                  'main/notebook_details.html',
                  {'notebook': notebook,
                   'other_notebooks': other_notebooks,
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
                            oh_member=request.user.oh_member,
                            created_at=arrow.now().format())
        like.save()
    return redirect(reverse('notebook-details', args=(notebook_id,)))


def render_notebook(request, notebook_id):
    notebook = SharedNotebook.objects.get(pk=notebook_id)
    format_notebook = nbformat.reads(notebook.notebook_content,
                                     as_version=nbformat.NO_CONVERT)
    html_exporter = nbconvert.HTMLExporter()
    html_exporter.template_file = 'basic'
    # below also removes output of code
    html_exporter.exclude_code_cell = True
    (body, resources) = html_exporter.from_notebook_node(format_notebook)
    return HttpResponse(body)


def export_notebook(request, notebook_id):
    notebook = SharedNotebook.objects.get(pk=notebook_id)
    return HttpResponse(notebook.notebook_content,
                        content_type='application/json')


def open_notebook_hub(request, notebook_id):
    notebook = SharedNotebook.objects.get(pk=notebook_id)
    nbview_session_key = 'nb-view-{}'.format(notebook_id)
    if not request.session.get(nbview_session_key):
        request.session[nbview_session_key] = True
        notebook.views += 1
        notebook.save()
    notebook_link = create_notebook_link(notebook, request)
    return redirect(notebook_link)
