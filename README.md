<<<<<<< HEAD
# images-rag-workshop
电商多模态 RAG 应用 Workshop
=======
# Images 多模态RAG 应用Workshop

#### 业务背景

电商场景中，用户希望通过输入图片，用以图搜图/文搜图/图+文搜图的方式可快速在图片库中检索到与输入图片相似的图片集合。可广泛应用于拍照购物、商品推荐、电商选品、产品设计管理等场景。

图片搜素的三个需求：

1. 根据整张图片搜索近似图片列表，并根据相似度排序；
2. 根据局部图片从图片库中搜索包含局部图片的列表，并根据匹配度排序；
3. 根据整张图的局部特征描述搜索近似图片列表，并根据匹配度排序。

传统方案的挑战：

1. 通过图片的关键词做纯文本检索，无法完全捕捉图片细节，通常取决于文本内容。然后大部分图片的描述信息又会有很多重复；
2. 通过小模型的图片特征匹配，维度较少，匹配精度不高；
3. 通过纯图片的向量化召回，无法根据特定的细节进行匹配，如描述一个图片里局部的匹配；

## 架构说明

![1729170034791](image/README/1729170034791.png)

![1729170049892](image/README/1729170049892.png)

**组件说明**

Amazon Bedrock: 是Amazon 完全托管的AI服务，通过API的方式提供访问多种FMs 比如Anthropic/AI21 Labs/Cohere/Meta等模型

Amazon Opensearch: 是AWS完全托管的Text Search/Vector 数据库

Amazon S3:  Amazon S3是高可用的，几乎无限扩张的对象存储服务, 这边我们使用它来存储图片

Amazon Lambda: 是Amazon Serverless的计算服务，在这边封装了image search的API如upload image/search image等

Rerank:  这个组件是借助基于prompt Engineering的rerank，通过配置的prompt设计，将候选结果和查询一起输入到LLM，让LLM生成一个新的排序来表示候选结果的相关性。


## 本地开发说明

cd lambda

uvicorn index:app --reload

## 部署说明

### 前提

1. 安装python 版本>3.9 npm 及cdk
2. [安装与配置AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
3. 安装[AWS CDK](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html)
4. 安装docker

Amazon linux 2023 参考

```
yum install npm
npm install -g aws-cdk
npm install docker 
service docker start

```

### 工程结构说明

```
├── API_Docs.md  //API文档
├── README.md
├── asserts
├── bin
├── cdk.context.json
├── cdk.json
├── image
├── jest.config.js
├── lambda     //业务逻辑
├── lib
├── package.json
├── tsconfig.json
└── web     // 前端UI，通过node运行
```

### Quick Start


```
# 登陆aws public ECR 获取基础镜像（多阶段构建，这边是通过Lambda Web Adapter的镜像层构建Lambda容器）
aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws
```


```
# CDK依赖
npm install
# CDK在AWS上做环境准备的。引导Stacksets在AWS环境配置S3存储桶和ECR镜像仓库的配置
cdk bootstrap
# 
cdk deploy
```


## Useful commands

* `npm run build`   compile typescript to js
* `npm run watch`   watch for changes and compile
* `npm run test`    perform the jest unit tests
* `npx cdk deploy`  deploy this stack to your default AWS account/region
* `npx cdk diff`    compare deployed stack with current state
* `npx cdk synth`   emits the synthesized CloudFormation template
>>>>>>> fangyi-specialty-builder
