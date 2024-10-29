cd upload-image
aws ecr-public get-login-password --region us-east-1 --profile default | docker login --username AWS --password-stdin public.ecr.aws/o7j8s3d5
docker build -t uploadimage:latest .

export ACCOUNT_ID=<YOUR-ACCOUNT-ID>
export TAG="latest"

aws ecr get-login-password --region us-east-1 --profile default | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com
docker tag uploadimage:latest $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/image_search_rag/uploadimage:$TAG
docker push $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/image_search_rag/uploadimage:$TAG