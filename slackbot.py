import os
from slack import RTMClient
from slack.errors import SlackApiError
import time

from docker_repository import DockerRepositoryManager
from kube_api import KubeApi
from utils import get_all_apps


DEPLOYBOT_SYNTEX = 'valid commands:\n' \
                   '`@DeployBot deploy <app-name>`\n' \
                   '`@DeployBot latest-image <app-name>`\n' \
                   '`@DeployBot running-app-image <app-name>`\n' \
                   '`@DeployBot check-for-update <app-name or all>`'
DEPLOYBOT_MENTION = f'<@{os.getenv("DEPLOYBOT_USER_ID")}>'


def __answer_message(channel, text, web_client):
    try:
        print(f'sending {text} to channel {channel}')
        response = web_client.chat_postMessage(
            channel=channel,
            text=text
        )
    except SlackApiError as e:
        # You will get a SlackApiError if "ok" is False
        assert e.response["ok"] is False
        assert e.response["error"]  # str like 'invalid_auth', 'channel_not_found'
        print(f"Got an error: {e.response['error']}")


def __check_for_update(app, progress_cb):
    if app != 'all':
        return KubeApi.update_image(app, progress_cb, dry_run=True)

    for app in get_all_apps():
        KubeApi.update_image(app, progress_cb, dry_run=True)

@RTMClient.run_on(event="message")
def process_command(**payload):
    data = payload['data']
    if 'client_msg_id' not in data or 'text' not in data or DEPLOYBOT_MENTION not in data['text']:
        return
    web_client = payload['web_client']
    rtm_client = payload['rtm_client']
    user = data['user']
    channel = data['channel']

    def send_message(msg):
        __answer_message(channel, msg, web_client)

    try:
        (bot_user_id, command, app) = data['text'].split()
    except ValueError as err:
        send_message(f'Sorry <@{user}>, invalid command syntex, {DEPLOYBOT_SYNTEX}')
        return

    try:
        if command == 'deploy':
            return KubeApi.update_image(app, send_message)
        if command == 'latest-image':
            return DockerRepositoryManager.get_latest_image_for_app(app, send_message)
        if command == 'running-app-image':
            return KubeApi.get_app_image(app, send_message)
        if command == 'check-for-update':
            return __check_for_update(app, send_message)
    except Exception as e:
        send_message(f'{e}')
        return
    send_message(f'Sorry <@{user}>, {command} is not a valid command, {DEPLOYBOT_SYNTEX}')


def start_work(retries=0):
    try:
        rtm_client = RTMClient(token=os.environ["SLACKBOT_API_TOKEN"], auto_reconnect=True)
        rtm_client.start()
    except Exception as e:
        print (f'main loop crash {e}, try to restart, attempt {retries}')
        if retries == 3:
            raise e
        time.sleep(retries*15)
        start_work(retries+1)

start_work()
