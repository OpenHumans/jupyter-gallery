from django.test import TestCase
from django.conf import settings
from open_humans.models import OpenHumansMember, make_unique_username
from django.contrib.auth.models import User


class OpenHumansMemberTest(TestCase):
    def setUp(self):
        settings.DEBUG = True

        self.oh_member = OpenHumansMember.create(
                            oh_id=1234,
                            oh_username='testuser1',
                            access_token='foo',
                            refresh_token='bar',
                            expires_in=36000)
        self.user = User(username='user1')
        self.user.save()

    def tests_str_(self):
        self.assertEqual(str(self.oh_member),
                         "<OpenHumansMember(oh_id='1234')>")

    def tests_unique(self):
        self.assertEqual(make_unique_username("user1"),
                         "user12")
