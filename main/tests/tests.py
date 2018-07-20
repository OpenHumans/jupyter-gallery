from django.test import TestCase, Client
from django.conf import settings
from open_humans.models import OpenHumansMember
from main.models import SharedNotebook, NotebookComment
import vcr
import arrow


class GeneralTest(TestCase):
    def setUp(self):
        settings.DEBUG = True
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

    @vcr.use_cassette('main/tests/fixtures/add_notebook.yaml',
                      record_mode='none')
    def test_add_notebook_not_logged_in(self):

        c = Client()
        response = c.post(
            '/add-notebook-gallery/12/',
            {
                'description': 'foobar',
                'tags': 'test, tags',
                'data_sources': 'data,source'
            },
            follow=True)
        self.assertEqual(response.status_code, 200)
        notebooks = SharedNotebook.objects.all()
        self.assertEqual(len(notebooks), 0)

    @vcr.use_cassette('main/tests/fixtures/add_notebook.yaml',
                      record_mode='none')
    def test_add_notebook_logged_in(self):

        c = Client()
        c.login(username=self.user.username, password='foobar')
        response = c.post(
            '/add-notebook-gallery/12/',
            {
                'description': 'foobar',
                'tags': 'test, tags',
                'data_sources': 'data,source'
            },
            follow=True)
        self.assertEqual(response.status_code, 200)
        notebooks = SharedNotebook.objects.all()
        self.assertEqual(len(notebooks), 1)
        self.assertEqual(
            notebooks[0].notebook_name,
            'twitter-and-fitbit-activity.ipynb')

    def test_add_comment(self):
        c = Client()
        c.login(username=self.user.username, password='foobar')
        self.assertEqual(len(NotebookComment.objects.all()), 0)
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
        response = c.post(
                    '/add-comment/{}/'.format(self.notebook.id),
                    {'comment_text': 'stupid comment'},
                    follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(NotebookComment.objects.all()), 1)

    def test_edit_notebook(self):
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
        c = Client()
        c.login(username=self.user.username, password='foobar')

        response = c.post(
            '/edit-notebook/{}/'.format(self.notebook.id),
            {
                'description': 'edited',
                'tags': 'notfoo, notbar',
                'data_sources': 'new_data_source',
            },
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        updated_nb = SharedNotebook.objects.get(pk=self.notebook.pk)
        self.assertEqual(updated_nb.description, 'edited')
