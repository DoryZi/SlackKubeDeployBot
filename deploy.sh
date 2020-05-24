#/bin/bash
docker build -t slackbot:latest .
docker tag slackbot:latest "${ECR_REGISTER}/slackbot:latest"
docker push "${ECR_REGISTER}/slackbot:latest"
kubectl delete pod $(kubectl get pods -n slackbot | grep 'kube-slackbot' | awk '{ print $1 }') -n slackbot
SLACKBOT_POD=$(kubectl get pods -n slackbot | grep kube | awk '{ print $1 }')
echo $SLACKBOT_POD
kubectl logs $SLACKBOT_POD -n slackbot



