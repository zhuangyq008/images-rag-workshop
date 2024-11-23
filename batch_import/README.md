# 批量导入工具文档

```shell
本目录包含将图片及其元数据批量导入到OpenSearch的工具。

## 目录内容

- `batch_import_to_opensearch.py`: 批量导入图片到OpenSearch的主脚本
- `clean_index.py`: 清理/重置OpenSearch索引的工具脚本
- `config.py`: AWS服务和OpenSearch的配置设置
- `embedding_generator.py`: 处理图片嵌入向量生成
- `opensearch_client.py`: OpenSearch服务交互客户端
- `meta_2023_100.json`: 图片元数据示例文件
- `import_progress.txt`: 导入进度跟踪日志
- `requirements.txt`: Python包依赖

## 使用前准备

1. 安装所需依赖：
```bash
pip install -r requirements.txt
```

2. 在`config.py`中配置AWS凭证和设置

## 使用说明

### 批量导入流程

使用主脚本`batch_import_to_opensearch.py`来导入图片和元数据到OpenSearch。

基本用法：

```bash
python batch_import_to_opensearch.py --meta-file meta_2023_100.json --start-index 0 --batch-size 100
```

参数说明：

* `--meta-file`: 必需，指定元数据JSON文件路径
* `--start-index`: 可选，指定从元数据文件中的第几条记录开始导入，默认为0
* `--batch-size`: 可选，指定本次导入的记录数量，默认为100
* `--resume`: 可选，从上次中断的位置继续导入，会读取import_progress.txt中的进度

示例：

```bash
# 导入前100条记录
python batch_import_to_opensearch.py --meta-file meta_2023.json --batch-size 100

# 从第200条记录开始导入300条
python batch_import_to_opensearch.py --meta-file meta_2023.json --start-index 200 --batch-size 300

# 从上次中断的位置继续导入
python batch_import_to_opensearch.py --meta-file meta_2023.json --resume
```

脚本将：

1. 根据参数从指定的JSON文件读取图片元数据
2. 使用AWS Bedrock为每张图片生成嵌入向量
3. 将数据上传到OpenSearch
4. 在import_progress.txt中跟踪进度

### 清理索引

要重置或清理OpenSearch索引：

```bash
python clean_index.py
```

## 组件详情

### batch_import_to_opensearch.py

* 主要导入脚本
* 支持分批次导入数据
* 支持断点续传
* 通过AWS Bedrock生成嵌入向量
* 上传数据到OpenSearch
* 包含进度跟踪和错误处理

### clean_index.py

* 删除现有索引
* 创建带有适当映射的新索引
* 重置导入进度

### config.py

* AWS服务配置
* OpenSearch端点设置
* 嵌入向量模型配置

### embedding_generator.py

* 使用AWS Bedrock生成图片嵌入向量
* 处理图片预处理
* 管理Bedrock服务API调用

### opensearch_client.py

* 管理OpenSearch连接
* 处理文档索引
* 提供搜索功能

## 进度跟踪

导入进度自动记录在`import_progress.txt`中。该文件显示：

* 需要处理的图片总数
* 已处理的图片数量
* 当前处理状态
* 遇到的任何错误'


```
