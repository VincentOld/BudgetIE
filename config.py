# -*- coding: utf-8 -*-
"""
@Time ： 2024/11/12 20:59
@Auth ： vincent
@File ：config.py
@IDE ：PyCharm
"""
import os
import re
import pandas as pd
from sparkai.llm.llm import ChatSparkLLM
from util import result_list


# 定义配置类
class Config:
    current_dir = os.path.abspath(os.path.dirname(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, ''))
    # 设置数据目录的路径
    base_dataset_path = os.path.join(project_root, 'data').replace("\\", "/")
    # bert模型路径
    pretrained_model_name_or_path = os.path.join(project_root, 'model',
                                                 'bert-base-chinese').replace("\\", "/")
    # 定义目标结果模板路径
    target_excel_path = os.path.join(project_root, '目标结果模板.xlsx').replace("\\", "/")
    # 定义budget_dataset路径
    budget_dataset_path = os.path.join(project_root, 'extractor', "binary_classification_bert",
                                       'budget_dataset.xlsx').replace("\\", "/")

    # BERT模型配置路径
    model_path = os.path.join(project_root, "model",
                              'finetuned_budget_bert.bin').replace("\\", "/")
    tokenizer_path = os.path.join(project_root, "model",
                                  'bert-base-chinese').replace("\\", "/")
    #定义TAPAS模型路径
    tapas_model_path = os.path.join(project_root, "model",
                                  'tapas-base-finetuned-wtq').replace("\\", "/")
    tapas_tokenizer_path = os.path.join(project_root, "model",
                                  'tapas-base-finetuned-wtq').replace("\\", "/")
    # 定义是否需要从word提取excel表格
    process_word = True
    # 定义是否需要将doc文件转换为docx文件
    convert_doc = True
    # 读取文件夹时是否读取table
    read_table = False
    # 读取报告时是否使用ocr
    OCR = True

    # ChatSparkLLM星火大模型
    ChatSparkLLM_Max = ChatSparkLLM(
        spark_api_url='wss://spark-api.xf-yun.com/v3.5/chat',
        spark_app_id='7d387d47',
        spark_api_secret='OTM0NzMxMGJlNmE2NTEyN2I0M2Y4NTZk',
        spark_api_key='239196233c4a3dc2bf5e09a219d05374',
        spark_llm_domain='generalv3.5'
    )
    ChatSparkLLM_Pro = ChatSparkLLM(
        spark_api_url='wss://spark-api.xf-yun.com/v3.1/chat',
        spark_app_id='7d387d47',
        spark_api_secret='OTM0NzMxMGJlNmE2NTEyN2I0M2Y4NTZk',
        spark_api_key='239196233c4a3dc2bf5e09a219d05374',
        spark_llm_domain='generalv3'
    )
    ChatSparkLLM_Lite = ChatSparkLLM(
        spark_api_url='wss://spark-api.xf-yun.com/v1.1/chat',
        spark_app_id='7d387d47',
        spark_api_secret='OTM0NzMxMGJlNmE2NTEyN2I0M2Y4NTZk',
        spark_api_key='239196233c4a3dc2bf5e09a219d05374',
        spark_llm_domain='lite'
    )
    # 提取金额的正则表达式
    amount_pattern = re.compile(r'(\d+\.?\d*)(亿元|万元|亿|万|元)?')
    # 定义需要提取的指标
    indicators = [
        "一般公共预算收入",
        "税收收入",
        "一般公共预算支出",
        "一般公共服务支出",
        "预算稳定基金",
        "支出年终结余",
        "政府性基金收入",
        "政府性基金支出",
        "国有资本经营预算收入",
        "国有资本经营预算支出",
        "一般债务余额",
        "专项债务余额",
        "债务余额决算数"
    ]

    # 转换字典
    conversion_dict = {
        "市级": "本级",
        "州级": "本级",
        "本市": "全市",
        "本州": "全州",
        "我市": "全市",
        "我州": "全州",
    }

    # 名词：用于识别名词短语
    custom_nouns = ["收入", "支出","税收", "公共", "稳定", "年终", "结余","经营","专项","余额","基金", "政府", "债务", "国有资本", "一般"]

    # 目标结果字典
    target_result_dict = {"一般公共预算收入": "", "税收收入": "", "一般公共预算支出": "", "一般公共服务支出": "",
                          "预算稳定基金": "", "支出年终结余": "", "政府性基金收入": "", "政府性基金支出": "",
                          "国有资本经营预算收入": "", "国有资本经营预算支出": "", "一般债务余额": "",
                          "专项债务余额": "",
                          "债务余额决算数": ""}

    #输出到表格时的mapping_dict,keyword_match的key，value是输出到表格的列名
    output_mapping_dict = {
        '2022年一般公共预算收入': '2022年一般公共预算收入',
        '2022年税收收入': '2022年税收收入',
        '2022年一般公共预算支出': '2022年一般公共预算支出',
        '2022年一般公共服务支出': '2022年一般公共服务支出',
        '2022年预算稳定基金': '2022年安排预算稳定基金',
        '2022年一般公共预算支出年终结余': '2022年一般公共预算支出年终结余',
        '2022年政府性基金收入': '2022年政府性基金收入',
        '2022年政府性基金支出': '2022年政府性基金支出',
        '2022年国有资本经营预算收入': '2022年国有资本经营预算收入',
        '2022年国有资本经营预算支出': '2022年国有资本经营预算支出',
        '2022年一般债务余额': '2022年地方政府一般债务余额',
        '2022年专项债务余额': '2022年年度地方政府专项债务余额',
        '2022年债务余额决算数': '2022年年末地方政府债务余额决算数'
    }

    # 用于第二轮匹配的关键词，作为筛选条件
    second_round_match_keywords = ["税收", "公共", "稳定", "年终", "基金", "政府", "债务", "国有资本","一般"]
    @staticmethod
    def get_folder_structure(base_dataset_path):
        """获取训练集文件夹结构"""
        structure = {}
        for province in os.listdir(base_dataset_path):
            province_path = os.path.join(base_dataset_path, province)
            if os.path.isdir(province_path):
                structure[province] = {}
                for city in os.listdir(province_path):
                    city_path = os.path.join(province_path, city)
                    if os.path.isdir(city_path):
                        structure[province][city] = city_path
        return structure

    @staticmethod
    def get_excel_row_count(target_excel_path):
        try:
            df = pd.read_excel(target_excel_path, sheet_name=None)
            total_rows = 0
            for sheet_name, sheet_data in df.items():
                total_rows += sheet_data.shape[0]
            return total_rows
        except FileNotFoundError:
            print(f"文件 {target_excel_path} 未找到，请检查路径。")
            return None
        except Exception as e:
            print(f"读取 Excel 文件时发生错误: {e}")
            return None

    folder_structure = get_folder_structure(base_dataset_path)
    row_num = get_excel_row_count(target_excel_path)
    RESULT_LIST = result_list.result.RESULT_LIST
