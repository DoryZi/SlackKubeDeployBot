import os
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import logging

from docker_repository import DockerRepositoryManager
from utils import get_app_info

KUBE_CLUSTER_TOKEN = os.getenv('KUBE_CLUSTER_TOKEN', None)
KUBE_CLUSTER_ENDPOINT = os.getenv('KUBE_CLUSTER_ENDPOINT', None)

from datetime import datetime

class KubeClientApiInstance:
    _API_INSTANCE = None

    @staticmethod
    def _create_token_api_client(token, endpoint):
        # Create a configuration object
        token_configuration = client.Configuration()
        # Specify the endpoint of your Kube cluster
        token_configuration.host = endpoint
        # Security part.
        # In this simple example we are not going to verify the SSL certificate of
        # the remote cluster (for simplicity reason)
        token_configuration.verify_ssl = False
        # Nevertheless if you want to do it you can with these 2 parameters
        # configuration.verify_ssl=True
        # ssl_ca_cert is the filepath to the file that contains the certificate.
        # configuration.ssl_ca_cert="certificate"

        token_configuration.api_key = {"authorization": "Bearer " + token}

        # Create a ApiClient with our config
        token_api_client = client.ApiClient(token_configuration)
        return client.AppsV1Api(token_api_client)

    @staticmethod
    def _initialize_using_token():
        KubeClientApiInstance._API_INSTANCE = KubeClientApiInstance._create_token_api_client(
            KUBE_CLUSTER_TOKEN,
            KUBE_CLUSTER_ENDPOINT
        )
        return

    @staticmethod
    def _initialize_client():
        if KUBE_CLUSTER_TOKEN is not None:
            return KubeClientApiInstance._initialize_using_token()
        try:
            config.load_incluster_config()  # How to set up the client from within a k8s pod
            client.configuration.debug = True
            KubeClientApiInstance._API_INSTANCE = client.AppsV1Api()
        except config.config_exception.ConfigException:
            config.load_kube_config()
            KubeClientApiInstance._API_INSTANCE = client.AppsV1Api()

    @staticmethod
    def get_client_api(app_info=None):
        client.configuration.debug = True
        if app_info is not None and 'cluster-token' in app_info:
            return KubeClientApiInstance._create_token_api_client(
                app_info.get('cluster-token'),
                app_info.get('cluster-endpoint')
            )
        if KubeClientApiInstance._API_INSTANCE is None:
            KubeClientApiInstance._initialize_client()
        return KubeClientApiInstance._API_INSTANCE


class KubeApi:

    @staticmethod
    def _create_patch_for_deployment(new_image, app_info, app):
        new_image_with_tag = DockerRepositoryManager.generate_full_image_url(new_image,
                             app_info['image-base-name'] if 'image-base-name' in app_info else app)
        return None if new_image_with_tag is None else {
            "metadata": {"annotations": {'kubernetes.io/change-cause': f'KubeBot update deployment {app_info["deployment"]} to {new_image_with_tag} using: _create_patch_for_deployment API on {datetime.now().isoformat()}'}},
            "spec": {"template": {"spec": {"containers": [{"name": f"{app_info['container-name']}", "image": f"{new_image_with_tag}"}]}}},
        }


    @staticmethod
    def get_app_image(app, progress_cb=None):
        app_info = get_app_info(app)
        kube_client_api = KubeClientApiInstance.get_client_api(app_info)
        try:
            api_response = kube_client_api.read_namespaced_deployment(
                name=app_info.get('deployment'),
                namespace=app_info.get('namespace'),
                pretty=True
            )
            print(api_response)
            running_image = api_response.spec.template.spec.containers[0].image.split(':')[1]
            if progress_cb:
                progress_cb(f'app *{app}* is currently running image\n`{running_image}`')
            return running_image
        except ApiException as e:
            if progress_cb:
                progress_cb(f'failed to read deployment: {e}')
        return None

    @staticmethod
    def update_image(app, progress_cb, dry_run=False):
        app_info = get_app_info(app)
        kube_client_api = KubeClientApiInstance.get_client_api(app_info)
        image_to_update = DockerRepositoryManager.get_latest_image_for_app(app)
        image_tag = image_to_update['imageTags'][0]
        running_image = KubeApi.get_app_image(app)
        if running_image is None:
            progress_cb(f"failed to *{app}* status from deployment: {app_info['deployment']}")
            return

        if running_image == image_tag:
            if progress_cb:
                progress_cb(f'*{app}* running latest image:\n`{running_image}`\nnothing to deploy.')
            return

        if dry_run:
            if progress_cb:
                progress_cb(f"*{app}* Needs to be updated. Currently running:\n `{running_image}`\n"
                            f"and should update to latest image:\n`{image_tag}`\n"
                            f"pushed to registry on: `{image_to_update['imagePushedAt'].strftime('%d-%b-%Y (%H:%M:%S.%f)')}`")
            return


        if progress_cb:
            progress_cb(f"Updating *{app}* deployment with image:\n"
                        f"`{image_tag}`\n"
                        f"pushed to registry on: `{image_to_update['imagePushedAt'].strftime('%d-%b-%Y (%H:%M:%S.%f)')}`"
                        f"\nplease wait...")

        update_patch_body = KubeApi._create_patch_for_deployment(image_to_update, app_info, app)
        if update_patch_body is None:
            if progress_cb:
                progress_cb(f"Failed to generate an update patch for {image_to_update}, could not find a valid tag name for image")
            return
        try:
            api_response = kube_client_api.patch_namespaced_deployment(
                name=app_info['deployment'],
                namespace=app_info['namespace'],
                body=update_patch_body,
                pretty=True
            )
        except ApiException as e:
            if progress_cb:
                progress_cb(f'failed to read deployment: {e}')

        if progress_cb:
            progress_cb(f'{app} updated successfully.')
