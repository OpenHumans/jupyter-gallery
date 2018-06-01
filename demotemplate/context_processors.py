from django.conf import settings


def login_fills(request):
        return {
            'client_id': settings.OPENHUMANS_CLIENT_ID,
            'redirect_uri':
                settings.OPENHUMANS_APP_BASE_URL + '/complete',
            'JH_URL': settings.JUPYTERHUB_BASE_URL,
            'base_url': request.build_absolute_uri("/").rstrip('/')
        }
