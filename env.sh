REGION="us-east-1"
ECR_URI="123456789101.dkr.ecr.us-east-1.amazonaws.com/space-rocket"
ECR_REPOSITORY="smart-cdc"
ECR_REPOSITORY_URI="$ECR_URI/$ECR_REPOSITORY"
# TAG=$(date +%Y%m%d%H%M%S)
TAG="latest"
export IMAGE_ID="$ECR_REPOSITORY_URI:$TAG"
BRANCH_NAME=$(git rev-parse HEAD | xargs git name-rev | cut -d' ' -f2 | sed 's/remotes\/origin\///g' | tr '[:upper:]' '[:lower:]' | tr '_' '-')
COMMIT_HASH=$(git rev-parse HEAD)
export COMMIT_HASH