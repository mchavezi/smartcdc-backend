set -e
echo 'Storing docker image in ECR'
source env.sh
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_URI

docker push $IMAGE_ID
