from django.db import models
from open_humans.models import OpenHumansMember
from datetime import timedelta
import arrow
import json


class SharedNotebook(models.Model):
    """
    Store OAuth data for a data source.
    This is a one to one relationship with a OpenHumansMember model
    You can find the OpenHumansMember model in open_humans/models.py

    There is a bi-directional link, called oh_member from this object.
    This could be used
    to fetch the OpenHumansMember object given a DataSourceMember object.
    """
    oh_member = models.ForeignKey(OpenHumansMember, on_delete=models.CASCADE)
    notebook_name = models.TextField(default='')
    notebook_content = models.TextField(default='')
    description = models.TextField(default='')
    tags = models.TextField(default='')
    data_sources = models.TextField(default='')
    views = models.IntegerField(default=0)
    # Your other fields should go below here
    updated_at = models.DateTimeField(
                            default=(arrow.now() - timedelta(days=7)).format())
    created_at = models.DateTimeField(
                            default=(arrow.now() - timedelta(days=7)).format())
    master_notebook = models.ForeignKey('self',
                                        on_delete=models.SET_NULL,
                                        blank=True,
                                        null=True)

    def get_tags(self):
        return ",".join(json.loads(self.tags)) if self.tags else ''

    def get_data_sources(self):
        if self.data_sources:
            return ",".join(json.loads(self.data_sources))
        else:
            return ''

    def get_tags_json(self):
        return json.loads(self.tags)

    def get_data_sources_json(self):
        return json.loads(self.data_sources)

    def delete(self, *args, **kwargs):
        nb_name = self.notebook_name
        super().delete(*args, **kwargs)  # Call the "real" save() method.
        # update_master_associations(nb_name)


class NotebookComment(models.Model):
    """
    comments about a given notebook
    """
    oh_member = models.ForeignKey(OpenHumansMember, on_delete=models.CASCADE)
    notebook = models.ForeignKey(SharedNotebook, on_delete=models.CASCADE)
    comment_text = models.TextField(default='')
    created_at = models.DateTimeField(default=arrow.now().format())

    class Meta:
            ordering = ["created_at"]


class NotebookLike(models.Model):
    """
    like a given notebook
    """
    oh_member = models.ForeignKey(OpenHumansMember, on_delete=models.CASCADE)
    notebook = models.ForeignKey(SharedNotebook, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=arrow.now().format())
