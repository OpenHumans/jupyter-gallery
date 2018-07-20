from django.test import TestCase, RequestFactory
from django.conf import settings
from open_humans.models import OpenHumansMember
from main.models import SharedNotebook
from main.views import render_notebook, open_notebook_hub
import arrow


class ViewTest(TestCase):
    def setUp(self):
        settings.DEBUG = True
        self.factory = RequestFactory()
        self.oh_member = OpenHumansMember.create(
                            oh_id=1234,
                            oh_username='testuser1',
                            access_token='foobar',
                            refresh_token='bar',
                            expires_in=36000)
        self.oh_member.save()
        self.user = self.oh_member.user
        self.user.set_password('foobar')
        self.user.save()
        self.notebook = SharedNotebook(
            oh_member=self.oh_member,
            notebook_name='test_notebook.ipynb',
            notebook_content=open(
                'main/tests/fixtures/test_notebook.ipynb').read(),
            description='test_description',
            tags='["foo", "bar"]',
            data_sources='["source1", "source2"]',
            views=123,
            updated_at=arrow.now().format(),
            created_at=arrow.now().format()
        )
        self.notebook.save()

    def test_notebook_render(self):
        r = self.factory.get('/')
        rendered_notebook = render_notebook(r, self.notebook.id)
        self.assertEqual(rendered_notebook.status_code, 200)
        self.assertIsNotNone(rendered_notebook.content)

    def test_open_notebook(self):
        r = self.factory.get('/')
        self.assertEqual(self.notebook.views, 123)
        open_notebook_hub(r, self.notebook.id)
        updated_nb = SharedNotebook.objects.get(pk=self.notebook.id)
        self.assertEqual(updated_nb.views, 124)
