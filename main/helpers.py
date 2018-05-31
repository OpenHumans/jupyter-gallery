from ohapi import api
from django.conf import settings
import arrow
from datetime import timedelta


def get_rescuetime_file(oh_member):
    try:
        oh_access_token = oh_member.get_access_token(
                            client_id=settings.OPENHUMANS_CLIENT_ID,
                            client_secret=settings.OPENHUMANS_CLIENT_SECRET)
        user_object = api.exchange_oauth2_member(oh_access_token)
        for dfile in user_object['data']:
            if 'Rescuetime' in dfile['metadata']['tags']:
                return dfile['download_url']
        return ''

    except:
        return 'error'


def check_update(rescuetime_member):
    if rescuetime_member.last_submitted < (arrow.now() - timedelta(hours=1)):
        return True
    return False
