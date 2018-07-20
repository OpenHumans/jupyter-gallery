from django.test import TestCase, RequestFactory
from main import helpers
from django.conf import settings
import arrow
from main.models import SharedNotebook
from open_humans.models import OpenHumansMember
from main.signals import my_handler


class HelpersTest(TestCase):
    def setUp(self):
        settings.DEBUG = True
        settings.JUPYTERHUB_BASE_URL = 'http://example.com/'
        self.factory = RequestFactory()
        self.oh_member = OpenHumansMember.create(
                            oh_id=1234,
                            oh_username='testuser1',
                            access_token='foo',
                            refresh_token='bar',
                            expires_in=36000)
        self.oh_member.save()
        self.notebook = SharedNotebook(
            oh_member=self.oh_member,
            notebook_name='test_notebook.ipynb',
            notebook_content=open(
                'main/tests/fixtures/test_notebook.ipynb').read(),
            description='test_description',
            tags='foo, bar',
            data_sources='source1, source2',
            views=123,
            updated_at=arrow.now().format(),
            created_at=arrow.now().format()
        )
        self.notebook.save()
        self.oh_member_two = OpenHumansMember.create(
                            oh_id=2345,
                            oh_username='testuser2',
                            access_token='foo',
                            refresh_token='bar',
                            expires_in=36000)
        self.oh_member_two.save()

    def test_notebook_link(self):
        request = self.factory.get('/')
        self.assertEqual(
            ('http://example.com//notebook-import?notebook_location'
                '=http://testserver/export-notebook/1/&notebook_name'
                '=test_notebook.ipynb'),
            helpers.create_notebook_link(self.notebook, request))

    def test_notebook_search(self):
        sources = helpers.find_notebook_by_keywords('foo', 'data_sources')
        tags = helpers.find_notebook_by_keywords('foo', 'tags')
        user = helpers.find_notebook_by_keywords('test', 'username')
        self.assertEqual(len(sources), 0)
        self.assertEqual(len(tags), 1)
        self.assertEqual(len(user), 1)

    def test_paginator(self):
        queryset = SharedNotebook.objects.all().order_by('pk')
        pages = [1, 2, 'NaN']
        for page in pages:
            paginator = helpers.paginate_items(queryset, page)
            self.assertEqual(paginator.number, 1)

    def test_signal_nb_delete(self):
        self.notebook_two = SharedNotebook(
            pk=2,
            oh_member=self.oh_member_two,
            notebook_name='test_notebook.ipynb',
            notebook_content=open(
                'main/tests/fixtures/test_notebook.ipynb').read(),
            description='test_description',
            tags='foo, bar',
            data_sources='source1, source2',
            views=123,
            updated_at=arrow.now().format(),
            created_at=arrow.now().format(),
            master_notebook=self.notebook
        )
        self.notebook_two.save()
        self.assertEqual(self.notebook_two.master_notebook, self.notebook)
        self.notebook_three = SharedNotebook(
            pk=3,
            oh_member=self.oh_member_two,
            notebook_name='test_notebook.ipynb',
            notebook_content=open(
                'main/tests/fixtures/test_notebook.ipynb').read(),
            description='test_description',
            tags='foo, bar',
            data_sources='source1, source2',
            views=123,
            updated_at=arrow.now().format(),
            created_at=arrow.now().format(),
            master_notebook=self.notebook
        )
        self.notebook_three.save()
        self.assertEqual(self.notebook_three.master_notebook, self.notebook)
        self.notebook.delete()
        my_handler('SharedNotebook', self.notebook)
        nb_two = SharedNotebook.objects.get(pk=2)
        nb_three = SharedNotebook.objects.get(pk=3)
        self.assertEqual(
            nb_three.master_notebook,
            nb_two)
