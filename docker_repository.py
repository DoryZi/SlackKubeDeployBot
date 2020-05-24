from datetime import datetime
import boto3
import os

from utils import get_regexp_for_image_name, get_app_info

REGISTRY_ID = os.getenv('AWS_ACCOUNT_ID')
AWS_REGION = os.getenv('AWS_DEFAULT_REGION')
REGISTRY_ADDRESS = f'{REGISTRY_ID}.dkr.ecr.{AWS_REGION}.amazonaws.com'

class DockerRepositoryManager:
    _ECR_CLIENT = None

    @staticmethod
    def get_ecr_client():
        if DockerRepositoryManager._ECR_CLIENT is None:
            DockerRepositoryManager._ECR_CLIENT = boto3.client('ecr')
        return DockerRepositoryManager._ECR_CLIENT

    @staticmethod
    def get_latest_image_for_app(app_name, progress_cb=None):
        app_info = get_app_info(app_name)
        image_name = app_name
        if ('image-base-name' in app_info):
            image_name = app_info['image-base-name']
        image_regexp = get_regexp_for_image_name(image_name)
        latest_image = { 'imagePushedAt': datetime(1970, 1, 1).astimezone() }
        ecr_client = DockerRepositoryManager.get_ecr_client()
        list_resp = ecr_client.describe_images(
            registryId=REGISTRY_ID,
            repositoryName=image_name,
            maxResults=1000
        )
        while True:
            for cur_image in list_resp['imageDetails']:
                if 'imageTags' not in cur_image or not any(image_regexp.match(tag) for tag in cur_image['imageTags']):
                    continue
                if (latest_image['imagePushedAt'] - cur_image['imagePushedAt']).total_seconds() < 0:
                    latest_image = cur_image
            next_token = list_resp.get('nextToken', None)
            if next_token is None:
                break
            list_resp = ecr_client.describe_images(
                registryId=REGISTRY_ID,
                repositoryName=image_name,
                maxResults=1000,
                nextToken=next_token
            )
        if progress_cb:
            progress_cb(f"*{app_name}* latest image in AWS ECR Repository (might not be deployed!):\n`{latest_image['imageTags'][0]}`\npushed to registry on: `{latest_image['imagePushedAt'].strftime('%d-%b-%Y (%H:%M:%S.%f)')}`")
        return latest_image

    @staticmethod
    def generate_full_image_url(new_image, app_name):
        valid_image_name_regexp = get_regexp_for_image_name(app_name)
        valid_image_tag = next(image_tag for image_tag in new_image['imageTags'] if valid_image_name_regexp.match(image_tag))
        if valid_image_tag is None:
            return valid_image_tag
        return f'{REGISTRY_ADDRESS}/{app_name}:{valid_image_tag}'
