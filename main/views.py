import logging
import requests
from django.contrib import messages
from django.contrib.auth import login, logout
from django.shortcuts import render, redirect
from django.conf import settings
from open_humans.models import OpenHumansMember
from .helpers import get_rescuetime_file, check_update
from ohapi import api
import arrow

# Set up logging.
logger = logging.getLogger(__name__)


def index(request):
    """
    Starting page for app.
    """
    if request.user.is_authenticated:
        return redirect('/dashboard')
    else:
        context = {'client_id': settings.OPENHUMANS_CLIENT_ID,
                   'redirect_uri': settings.OPENHUMANS_APP_BASE_URL +'/complete',
                   'oh_proj_page': settings.OH_ACTIVITY_PAGE}

        return render(request, 'main/index.html', context=context)


def complete(request):
    """
    Receive user from Open Humans. Store data, start upload.
    """
    print("Received user returning from Open Humans.")
    # Exchange code for token.
    # This creates an OpenHumansMember and associated user account.
    code = request.GET.get('code', '')
    oh_member = oh_code_to_member(code=code)

    if oh_member:
        # Log in the user.
        user = oh_member.user
        login(request, user,
              backend='django.contrib.auth.backends.ModelBackend')

        # Initiate a data transfer task, then render `complete.html`.
        # xfer_to_open_humans.delay(oh_id=oh_member.oh_id)
        context = {'oh_id': oh_member.oh_id,
                   'oh_proj_page': settings.OH_ACTIVITY_PAGE}
        if not hasattr(oh_member, 'datasourcemember'):

            rescuetime_url = ('https://www.rescuetime.com/oauth/authorize?'
                              'response_type=code&scope=time_data&'
                              'redirect_uri={}&client_id={}').format(
                            settings.RESCUETIME_REDIRECT_URI,
                            settings.RESCUETIME_CLIENT_ID)
            logger.debug(rescuetime_url)
            context['rescuetime_url'] = rescuetime_url
            return render(request, 'main/complete.html',
                          context=context)
        return redirect("/dashboard")

    logger.debug('Invalid code exchange. User returned to starting page.')
    return redirect('/')


def dashboard(request):
    if request.user.is_authenticated:
        if hasattr(request.user.oh_member, 'datasourcemember'):
            rescuetime_member = request.user.oh_member.datasourcemember
            download_file = get_rescuetime_file(request.user.oh_member)
            if download_file == 'error':
                logout(request)
                return redirect("/")
            connect_url = ''
            allow_update = check_update(rescuetime_member)
        else:
            allow_update = False
            rescuetime_member = ''
            download_file = ''
            connect_url = ('https://www.rescuetime.com/oauth/authorize?'
                           'response_type=code&scope=time_data&'
                           'redirect_uri={}&client_id={}').format(
                            settings.RESCUETIME_REDIRECT_URI,
                            settings.RESCUETIME_CLIENT_ID)
        context = {
            'oh_member': request.user.oh_member,
            'rescuetime_member': rescuetime_member,
            'download_file': download_file,
            'connect_url': connect_url,
            'allow_update': allow_update
        }
        return render(request, 'main/dashboard.html',
                      context=context)
    return redirect("/")


def remove_rescuetime(request):
    if request.method == "POST" and request.user.is_authenticated:
        try:
            oh_member = request.user.oh_member
            api.delete_file(oh_member.access_token,
                            oh_member.oh_id,
                            file_basename="rescuetime.json")
            messages.info(request, "Your Rescuetime account has been removed")
            rescuetime_account = request.user.oh_member.datasourcemember
            rescuetime_account.delete()
        except:
            rescuetime_account = request.user.oh_member.datasourcemember
            rescuetime_account.delete()
            messages.info(request, ("Something went wrong, please"
                          "re-authorize us on Open Humans"))
            logout(request)
            return redirect('/')
    return redirect('/dashboard')


def update_data(request):
    if request.method == "POST" and request.user.is_authenticated:
        oh_member = request.user.oh_member
        process_rescuetime.delay(oh_member.oh_id)
        rescuetime_member = oh_member.datasourcemember
        rescuetime_member.last_submitted = arrow.now().format()
        rescuetime_member.save()
        messages.info(request,
                      ("An update of your Rescuetime data has been started! "
                       "It can take some minutes before the first data is "
                       "available. Reload this page in a while to find your "
                       "data"))
        return redirect('/dashboard')


def rescuetime_complete(request):
    """
    Receive user from Rescuetime. Store data, start processing.
    """
    logger.debug("Received user returning from Rescuetime.")
    # Exchange code for token.
    # This creates an OpenHumansMember and associated user account.
    code = request.GET.get('code', '')
    ohmember = request.user.oh_member
    rescuetime_member = rescuetime_code_to_member(code=code, ohmember=ohmember)

    if rescuetime_member:
        messages.info(request, "Your Rescuetime account has been connected")
        process_rescuetime.delay(ohmember.oh_id)
        return redirect('/dashboard')

    logger.debug('Invalid code exchange. User returned to starting page.')
    messages.info(request, ("Something went wrong, please try connecting your "
                            "Rescuetime account again"))
    return redirect('/dashboard')


def rescuetime_code_to_member(code, ohmember):
    """
    Exchange code for token, use this to create and return Rescuetime members.
    If a matching Rescuetime exists, update and return it.
    """
    if settings.RESCUETIME_CLIENT_SECRET and \
       settings.RESCUETIME_CLIENT_ID and code:
        data = {
            'grant_type': 'authorization_code',
            'redirect_uri': settings.RESCUETIME_REDIRECT_URI,
            'code': code,
            'client_id': settings.RESCUETIME_CLIENT_ID,
            'client_secret': settings.RESCUETIME_CLIENT_SECRET
        }
        req = requests.post(
            'https://www.rescuetime.com/oauth/token/',
            data=data
        )
        data = req.json()
        print(data)
        if 'access_token' in data:
            try:
                rescuetime_member = DataSourceMember.objects.get(
                    user=ohmember)
                logger.debug('Member {} re-authorized.'.format(
                    rescuetime_member.user.project_member_id))
                rescuetime_member.access_token = data['access_token']
                rescuetime_member.scope = data['scope']
                print('got old rescuetime member')
            except DataSourceMember.DoesNotExist:
                rescuetime_member = DataSourceMember(
                    scope=data['scope'],
                    access_token=data['access_token'],
                        )
                rescuetime_member.user = ohmember
                logger.debug('Member {} created.'.format(ohmember.oh_id))
                print('make new rescuetime_member')
            rescuetime_member.save()

            return rescuetime_member

        elif 'error' in req.json():
            logger.debug('Error in token exchange: {}'.format(req.json()))
        else:
            logger.warning('Neither token nor error info in Rescuetime response!')
    else:
        logger.error('RESCUETIME_CLIENT_SECRET or code are unavailable')
    return None


def oh_code_to_member(code):
    """
    Exchange code for token, use this to create and return OpenHumansMember.
    If a matching OpenHumansMember exists, update and return it.
    """
    if settings.OPENHUMANS_CLIENT_SECRET and \
       settings.OPENHUMANS_CLIENT_ID and code:
        data = {
            'grant_type': 'authorization_code',
            'redirect_uri':
            '{}/complete'.format(settings.OPENHUMANS_APP_BASE_URL),
            'code': code,
        }
        req = requests.post(
            '{}/oauth2/token/'.format(settings.OPENHUMANS_OH_BASE_URL),
            data=data,
            auth=requests.auth.HTTPBasicAuth(
                settings.OPENHUMANS_CLIENT_ID,
                settings.OPENHUMANS_CLIENT_SECRET
            )
        )
        data = req.json()

        if 'access_token' in data:
            oh_id = oh_get_member_data(
                data['access_token'])['project_member_id']
            try:
                oh_member = OpenHumansMember.objects.get(oh_id=oh_id)
                logger.debug('Member {} re-authorized.'.format(oh_id))
                oh_member.access_token = data['access_token']
                oh_member.refresh_token = data['refresh_token']
                oh_member.token_expires = OpenHumansMember.get_expiration(
                    data['expires_in'])
            except OpenHumansMember.DoesNotExist:
                oh_member = OpenHumansMember.create(
                    oh_id=oh_id,
                    access_token=data['access_token'],
                    refresh_token=data['refresh_token'],
                    expires_in=data['expires_in'])
                logger.debug('Member {} created.'.format(oh_id))
            oh_member.save()

            return oh_member

        elif 'error' in req.json():
            logger.debug('Error in token exchange: {}'.format(req.json()))
        else:
            logger.warning('Neither token nor error info in OH response!')
    else:
        logger.error('OH_CLIENT_SECRET or code are unavailable')
    return None


def oh_get_member_data(token):
    """
    Exchange OAuth2 token for member data.
    """
    req = requests.get(
        '{}/api/direct-sharing/project/exchange-member/'
        .format(settings.OPENHUMANS_OH_BASE_URL),
        params={'access_token': token}
        )
    if req.status_code == 200:
        return req.json()
    raise Exception('Status code {}'.format(req.status_code))
    return None
