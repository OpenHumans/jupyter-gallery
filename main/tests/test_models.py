from django.test import TestCase
from django.conf import settings
from open_humans.models import OpenHumansMember
from main.models import SharedNotebook
from main.helpers import suggest_data_sources, identify_master_notebook
from main.helpers import get_notebook_files, get_notebook_oh
import arrow
import vcr


class SharedNotebookTest(TestCase):
    def setUp(self):
        settings.DEBUG = True

        self.oh_member = OpenHumansMember.create(
                            oh_id=1234,
                            oh_username='testuser1',
                            access_token='foo',
                            refresh_token='bar',
                            expires_in=36000)
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
        self.oh_member_data = {
            'created': '2018-01-19T21:55:40.049169Z',
            'project_member_id': '1234',
            'message_permission': True,
            'sources_shared': ['direct-sharing-71'],
            'username': 'gedankenstuecke',
            'data': [{
                'id': 12,
                'source': 'direct-sharing-71',
                'basename': 'test_notebook.ipynb',
                'created': '2018-06-06T17:09:26.688794Z',
                'download_url': 'http://example.com/test_notebook.ipynb',
                'metadata': {
                    'tags': ['personal data notebook', 'notebook', 'jupyter'],
                    'description': 'A Personal Data Notebook'}
                    }]}

    @vcr.use_cassette('main/tests/fixtures/suggested_sources.yaml')
    def test_notebook_present(self):
        suggested_sources = suggest_data_sources(
                                self.notebook.notebook_content)
        self.assertEqual(
            len(suggested_sources.split(',')),
            2)

    def test_identify_master_notebook(self):
        mnb = identify_master_notebook(
                'test_notebook.ipynb',
                self.oh_member_two)
        self.assertEqual(mnb, self.notebook)
        no_mnb = identify_master_notebook(
                'edited_test_notebook.ipynb',
                self.oh_member_two)
        self.assertEqual(no_mnb, None)

    def test_get_notebook_files(self):
        nb_files = get_notebook_files(self.oh_member_data)
        self.assertEqual(len(nb_files), 1)

    def test_get_notebook_oh(self):
        nbd = get_notebook_oh(
            oh_member_data=self.oh_member_data,
            notebook_id='12')
        self.assertEqual(
            nbd,
            ('test_notebook.ipynb', 'http://example.com/test_notebook.ipynb'))
