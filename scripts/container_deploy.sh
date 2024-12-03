# Usage: ./container_deploy.sh <env>

# get region and env from default profile
REGION=$(aws configure get region)
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)

# Check if REGION and AWS_ACCOUNT_ID are set
if [ -z "$REGION" ] || [ -z "$AWS_ACCOUNT_ID" ]; then
  echo "Error: REGION and AWS_ACCOUNT_ID must be set."
  exit 1
fi


# Build the Docker image
docker build --platform linux/amd64 -t tasknode-processor-${env} .

# Create ECR repository if it doesn't exist
aws ecr describe-repositories --repository-names tasknode-processor-${env} --region $REGION > /dev/null 2>&1 || \
aws ecr create-repository --repository-name tasknode-processor-${env} --region $REGION

# Tag and push to ECR
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com
docker tag tasknode-processor-${env}:latest $AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/tasknode-processor-${env}:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/tasknode-processor-${env}:latest