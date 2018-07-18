from django.test import TestCase, Client
from django.conf import settings
from open_humans.models import OpenHumansMember
from main.models import SharedNotebook
import vcr


class ViewTest(TestCase):
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
