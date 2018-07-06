from django.db.models.signals import post_delete
from django.dispatch import receiver
from .models import SharedNotebook


@receiver(post_delete, sender=SharedNotebook)
def my_handler(sender, instance, **kwargs):
    notebooks = SharedNotebook.objects.filter(
                notebook_name=instance.notebook_name).order_by('created_at')
    if notebooks:
        master_nb = notebooks[0]
        for notebook in notebooks[1:]:
            notebook.master_notebook = master_nb
            notebook.save()
