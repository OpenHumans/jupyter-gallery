from django.db import models
from open_humans.models import OpenHumansMember
from datetime import timedelta
import arrow


class DataSourceMember(models.Model):
    """
    Store OAuth data for a data source.
    This is a one to one relationship with a OpenHumansMember model
    You can find the OpenHumansMember model in open_humans/models.py

    There is a bi-directional link, called oh_member from this object.
    This could be used
    to fetch the OpenHumansMember object given a DataSourceMember object.
    """
    user = models.OneToOneField(OpenHumansMember, on_delete=models.CASCADE)
    # Your other fields should go below here
    access_token = models.CharField(max_length=256, default="")
    scope = models.CharField(max_length=256, default="")
    last_updated = models.DateTimeField(
                            default=(arrow.now() - timedelta(days=7)).format())
    last_submitted = models.DateTimeField(
                            default=(arrow.now() - timedelta(days=7)).format())
