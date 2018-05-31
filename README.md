# WIP: Jupyter Notebook Gallery

[![Build Status](https://travis-ci.org/gedankenstuecke/jupyter-gallery.svg?branch=master)](https://travis-ci.org/gedankenstuecke/jupyter-gallery)

This repository provides a `Django` application that interfaces with the `Open Humans` API.


## settings
what should be in the `.env`:

```
# the usual stuff:
SECRET_KEY='secret_key_here'
OH_ACTIVITY_PAGE='https://www.openhumans.org/activity/your-project-name-should-be-here/'
OH_CLIENT_ID='id'
OH_CLIENT_SECRET='secret'
APP_BASE_URL='http://127.0.0.1:5000'

# the UNusual stuff:
# the JUPYTERHUB_BASE_URL should be the local
# jupyter notebook url if running in dev
# or https://notebooks.openhumans.org/hub/user-redirect
# for production
JUPYTERHUB_BASE_URL = http://localhost:8888
