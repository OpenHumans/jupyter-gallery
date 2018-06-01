from django.conf import settings


def login_fills(request):
        return {
            'client_id': settings.OPENHUMANS_CLIENT_ID,
            'redirect_uri':
                settings.OPENHUMANS_APP_BASE_URL + '/complete',
        }
