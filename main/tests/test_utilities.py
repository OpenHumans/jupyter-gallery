from django.test import TestCase
from main.templatetags import utilities


class UtilitiesTest(TestCase):
    def test_markdown(self):
        conversion = utilities.markdown('#foo')
        self.assertEqual(conversion, '<h1>foo</h1>')

    def test_concatenate(self):
        concat = utilities.concatenate('foo', 'bar')
        self.assertEqual(concat, 'foo_bar')
