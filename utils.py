import re
import os

NEW_CLUSTER_ENDPOINT = os.getenv("KUBE_CLUSTER_ENDPOINT2")
NEW_CLUSTER_TOKEN = os.getenv("KUBE_CLUSTER_TOKEN2")


APPS = {
    "app-name": {
        "deployment": '<deployment-name>',
        "namespace": "<namespace>",
        "container-name": "<container-name>",
        "cluster-token": NEW_CLUSTER_TOKEN, # this is optional if you're running in another cluster
        "cluster-endpoint": NEW_CLUSTER_ENDPOINT # this is optional if you're running in another cluster
    },
}


def get_all_apps():
    return APPS.keys()


def get_app_info(app):
    app_info = APPS.get(app, None)
    if app_info is None:
        raise Exception(f'{app} does not exist, supported apps are: `{", ".join([key for key in APPS])}`')
    return app_info


def get_regexp_for_image_name(app_name):
    return re.compile(r'%s-\b[0-9a-f]{6,64}\b'%app_name)


