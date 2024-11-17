# 使用 Amazon Linux 2 作为基础镜像
FROM amazonlinux:2

# 更新并安装 Python 3.8 和其他必要的工具
RUN yum update -y && \
    amazon-linux-extras enable python3.8 && \
    yum install -y python3.8 python3-pip zip && \
    yum clean all

# 删除现有的 python3 和 pip3 链接，确保创建新的符号链接
RUN rm -f /usr/bin/python3 && \
    rm -f /usr/bin/pip && \
    ln -s /usr/bin/python3.8 /usr/bin/python3 && \
    ln -s /usr/bin/pip3 /usr/bin/pip

# 设置工作目录
WORKDIR /app

# 复制项目文件到容器中
COPY . /app

# 创建 lambda_layer 目录
RUN mkdir -p lambda_layer/python

# 安装依赖到 lambda_layer 中
RUN python3 -m pip install --no-cache-dir -r requirements.txt -t lambda_layer/python

# 清理无用文件
RUN find lambda_layer/python -type d -name "__pycache__" -exec rm -rf {} + && \
    find lambda_layer/python -type d -name "*.dist-info" -exec rm -rf {} + && \
    find lambda_layer/python -type f -name "*.pyc" -delete && \
    find lambda_layer/python -type f -name "*.pyo" -delete

# 结束构建镜像，此时不进行压缩操作
