set -e
echo '🏗️ Building docker image...'
source env.sh
echo $IMAGE_ID
echo $BRANCH_NAME
echo $COMMIT_HASH
# docker build -f Dockerfile-aws-2 -t $IMAGE_ID --no-cache .
# docker build -f Dockerfile -t $IMAGE_ID --no-cache .
docker build -f Dockerfile -t $IMAGE_ID --no-cache .
