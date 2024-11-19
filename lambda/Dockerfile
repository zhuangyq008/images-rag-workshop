FROM public.ecr.aws/docker/library/python:3.8.12-slim-buster
RUN aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.8.4 /lambda-adapter /opt/extensions/lambda-adapter
ENV PORT=8000
WORKDIR /var/task
COPY requirements.txt ./
RUN python -m pip install -r requirements.txt
COPY . ./
CMD exec uvicorn --port=$PORT index:app