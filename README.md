# BudgetIE: 基于深度学习的财政预算数据提取系统

## 项目简介

BudgetIE 是一个基于深度学习的智能数据提取系统，专门用于从各类财政预算文件中自动提取关键财政指标数据。系统采用多模型融合的方式，结合BERT深度学习模型、规则匹配和大语言模型，实现了对多种格式文档的高精度信息抽取。

### 主要特性

- 🚀 支持多种文档格式 (PDF, Word, Excel, HTML等)
- 🎯 高精度信息提取，采用多模型融合策略
- 🔍 智能识别13类核心财政指标
- 💪 具备优秀的跨文档格式泛化能力
- ⚡ 高效的批处理能力

## 目标指标

系统可自动提取以下13类财政指标数据：
- 一般公共预算收入
- 税收收入
- 一般公共预算支出
- 一般公共服务支出
- 预算稳定基金
- 支出年终结余
- 政府性基金收入
- 政府性基金支出
- 国有资本经营预算收入
- 国有资本经营预算支出
- 一般债务余额
- 专项债务余额
- 债务余额决算数

## 系统架构

```
BudgetExtractor/
├── config.py                 # 配置文件
├── main.py                   # 主运行文件
├── 目标结果模板.xlsx          # 数据输出模板
├── data/                     # 财政文件数据
├── parser/                   # 文档解析模块
│   ├── folder_preprocess.py  # 数据预处理
│   ├── report_read.py       # 报告文件读取
│   ├── table_read.py        # 表格文件读取
│   └── folder_read.py       # 目录读取
├── extractor/               # 信息提取模块
│   ├── binary_classification_bert/  # BERT分类模型
│   │   ├── model/                  # 模型文件
│   │   ├── binary_classify.py      # 模型训练
│   │   └── BudgetSentence_cls.py   # 模型推理
│   ├── keyword_match.py     # 关键词匹配
│   ├── lcs_match.py         # 最长公共子串匹配
│   └── sparkAI_match.py     # 大语言模型提取
└── util/                    # 工具函数
    └── util.py
```

## 技术实现

### 1. 多模型融合策略

- **BERT二分类模型**: 判断文本是否包含目标指标信息
- **关键词匹配**: 基于精确匹配的高置信度提取
- **LCS算法**: 使用最长公共子串进行模糊匹配
- **星火大模型**: 通过API调用实现智能信息提取

### 2. 文档处理流程

1. 数据预处理：标准化文件格式、清理无效文件
2. 文档解析：支持多种格式文件的统一读取
3. 文本过滤：使用BERT模型初筛相关文本
4. 多模型提取：并行使用多种提取策略
5. 结果融合：基于置信度的结果选择和合并
6. 数据输出：将提取结果写入标准模板

## 环境要求

- Python 3.8+
- PyTorch 1.8+
- transformers 4.0+
- pandas, numpy, sklearn
- easyocr (用于PDF文档OCR)
- win32com (用于Word文档处理)

## 快速开始

1. 打开项目并安装依赖：
```bash
cd BudgetIE
pip install -r requirements.txt
```

2. 下载预训练模型：
```bash
# 下载BERT模型到 model/bert-base-chinese/
网盘链接：https://pan.baidu.com/s/1rX2QU7stVN4g6WNZNRRx4g?pwd=4eam 提取码: 4eam 
# 下载微调后的模型到 model/finetuned_budget_bert.bin
网盘链接https://pan.baidu.com/s/1v3O9b7CUx_pu2JjSlvaBKQ?pwd=9gqh 提取码: 9gqh 
```

3. 配置参数：
```python
# 在config.py中设置必要的配置参数
```

4. 运行系统：
```bash
#设置row值即可一键运行
python main.py
```

## 性能指标

- 二分类准确率：>95%
- 文档类查准率：80%左右
- 表格类查准率：60%左右
- 平均处理时间：30s/目标表格每行
