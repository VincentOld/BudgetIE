# -*- coding: utf-8 -*-
"""
@Time ： 2024/11/26 21:26
@Auth ： vincent
@File ：main.py
@IDE ：PyCharm
"""
import sys
import time
from collections import defaultdict
from extractor.keyword_match import keyword_match
from extractor.lcs_match import lcs_match
from extractor.sparkAI_match import sparkAI_match
from extractor.binary_classification_bert.BudgetSentence_cls import batch_sentence_cls
import logging
from parser.folder_read import *
from parser.report_read import *
from util.util import *
import gc

logging.disable(logging.CRITICAL)
sys.stderr = open(os.devnull, 'w')
target_result_dict = Config.target_result_dict

'''
主要功能：读取报告文本，进行指标值匹配，并写入到Excel文件中
'''


# 主match函数：采用三种方法进行匹配，关键词匹配、lcs匹配、sparkAI匹配，返回值为三个dict（key已经统一）
def match(row, round=1):
    # 读取文件夹中的报告文件
    if round == 1:
        # 读取文件夹中的报告文件
        folder_path = get_folder_path_by_row(row)
        dir_info_list = process_reportFiles_in_folder(folder_path)
        # 如果文件夹信息为空
        if not dir_info_list:
            print('第一轮：文件夹信息为空')
            return

    # 第二轮：读取文件夹中的非报告类文件
    if round == 2:
        folder_path = get_folder_path_by_row(row)
        other_report_list = process_reportFiles_in_folder(folder_path, is_valid_filename=is_valid_filename2)
        tabel_list = process_tableFiles_in_folder(folder_path)
        dir_info_list = other_report_list + tabel_list
        dir_info_list = [
            item for item in dir_info_list
            if any(keyword in item for keyword in Config.second_round_match_keywords)
        ]
        # 如果文件夹信息为空
        if not dir_info_list:
            print('第二轮：文件夹信息为空')
            return {}, {}, {}
    # 限制只提取包含指定前缀的文本句
    if row % 2 == 1:
        koujing = "全市" or "全州"
        dir_info_list = list(filter(lambda x: koujing in x, dir_info_list))
    if row % 2 == 0:
        koujing = "本级"
        dir_info_list = list(filter(lambda x: koujing in x, dir_info_list))

    # 对文件夹信息进行过滤，保留分类为1的元素
    # print("第{round}轮：原始信息为：", dir_info_list)
    candidated_list = batch_sentence_cls(dir_info_list)
    if len(candidated_list) > 100:
        candidated_list = merge_short_texts(candidated_list)
    print(f"第{round}轮：符合条件的候选句子（包含指标数值金额）的数量为：", len(candidated_list))

    # 首先采用关键词匹配，写入到target_result_dict中
    keyword_result_dict = keyword_match(row)

    # 针对未匹配到的字段，采用lcs匹配
    lcs_result_dict = merge_dict([lcs_match(item) for item in candidated_list])

    # 针对未匹配到的字段，采用sparkAI匹配
    sparkAI_result_dict = sparkAI_match(koujing, candidated_list)
    keyword_result_dict, lcs_result_dict, sparkAI_result_dict = unify_keys(keyword_result_dict, lcs_result_dict,
                                                                           sparkAI_result_dict)
    return keyword_result_dict, lcs_result_dict, sparkAI_result_dict


# 置信度综合决策
def compute_score_final_result(keyword_result_dict, lcs_result_dict, sparkAI_result_dict, CONFIDENCE_THRESHOLD=0.6):
    final_result_dict = {}

    for key in set(keyword_result_dict.keys()):
        value_confidence_map = defaultdict(float)
        value_to_amount_map = {}
        unit_count_map = defaultdict(int)

        # Process keyword_result_dict
        if key in keyword_result_dict and keyword_result_dict[key]:
            data = keyword_result_dict[key]
            value = data.get('value')
            confidence = data.get('confidence', 0) / 100
            if value:
                value_confidence_map[value] += confidence
                amount, unit = extract_amount_and_unit(value)
                value_to_amount_map[value] = convert_to_base_unit(amount, unit)
                if unit:
                    unit_count_map[unit] += 1

        # Process lcs_result_dict - handle both list and dict cases
        if key in lcs_result_dict and lcs_result_dict[key]:
            data = lcs_result_dict[key]
            if isinstance(data, list):
                # Handle list of dictionaries
                for item in data:
                    value = item.get('value')
                    confidence = item.get('confidence', 0) / 100
                    if value:
                        value_confidence_map[value] += confidence
                        amount, unit = extract_amount_and_unit(value)
                        value_to_amount_map[value] = convert_to_base_unit(amount, unit)
                        if unit:
                            unit_count_map[unit] += 1
            else:
                # Handle single dictionary
                value = data.get('value')
                confidence = data.get('confidence', 0) / 100
                if value:
                    value_confidence_map[value] += confidence
                    amount, unit = extract_amount_and_unit(value)
                    value_to_amount_map[value] = convert_to_base_unit(amount, unit)
                    if unit:
                        unit_count_map[unit] += 1

        # Process sparkAI_result_dict
        if key in sparkAI_result_dict and sparkAI_result_dict[key]:
            data = sparkAI_result_dict[key]
            value = data.get('value')
            confidence = data.get('confidence', 0) / 100
            if value:
                value_confidence_map[value] += confidence
                amount, unit = extract_amount_and_unit(value)
                value_to_amount_map[value] = convert_to_base_unit(amount, unit)
                if unit:
                    unit_count_map[unit] += 1

        # Skip if no valid results
        if not value_confidence_map:
            continue

        # Find highest confidence value
        max_confidence_value = max(value_confidence_map.items(), key=lambda x: x[1])
        final_value = max_confidence_value[0]
        final_confidence = max_confidence_value[1]

        # Skip if below threshold
        if final_confidence < CONFIDENCE_THRESHOLD:
            continue

        # Process units and amounts
        amount, unit = extract_amount_and_unit(final_value)
        most_common_unit = max(unit_count_map.items(), key=lambda x: x[1])[0] if unit_count_map else "亿元"

        # Standardize unit format
        if not unit:
            if most_common_unit and len(str(int(amount))) <= 4:
                final_value = f"{round(amount, 2)}{most_common_unit}"
            elif 4 < len(str(int(amount))) <= 8:
                final_value = f"{round(amount / 10000, 2)}亿元"
            elif len(str(int(amount))) > 8:
                final_value = f"{round(amount / 100000000, 2)}亿元"

        if "万" in final_value:
            amount, _ = extract_amount_and_unit(final_value)
            final_value = f"{round(amount / 10000, 2)}亿元"

        final_result_dict[key] = {
            'value': final_value,
            'confidence': round(final_confidence * 100, 1)
        }

    return final_result_dict


def write_to_target_excel(row, final_result_dict):
    """
    将结果写入目标Excel文件

    Args:
        row: 目标行号
        final_result_dict: 包含value和confidence的结果字典
    """
    if not final_result_dict:
        print("输入字典为空，退出。")
        return

    # 定义需要去除的前缀
    prefixes = ['全市', '全州', '本级']

    # 处理字典，去除前缀并只保留value值
    processed_dict = {}
    for key, data in final_result_dict.items():
        if isinstance(data, str):
            # Handle case where data is a string
            processed_value = data
        elif isinstance(data, dict):
            # Handle case where data is a dictionary
            processed_value = data.get('value', '')
        else:
            # Skip if data is neither string nor dict
            continue

        # 去除前缀
        processed_key = key
        for prefix in prefixes:
            if isinstance(key, str) and key.startswith(prefix):
                processed_key = key[len(prefix):].lstrip()
                break

        # 只保留value值
        processed_dict[processed_key] = processed_value

    # 使用映射转换键名
    converted_dict = {
        Config.output_mapping_dict[key]: value
        for key, value in processed_dict.items()
        if key in Config.output_mapping_dict
    }

    try:
        # 加载目标Excel文件
        wb = openpyxl.load_workbook(Config.target_excel_path)
        sheet = wb.active
        header = [cell.value for cell in sheet[1] if cell.value is not None]
    except Exception as e:
        print(f"加载Excel文件时发生错误: {e}")
        return

    try:
        # 将值写入到目标Excel中
        for col_idx, col_name in enumerate(header, start=1):
            if col_name in converted_dict:
                value = converted_dict[col_name]
                if isinstance(value, dict):
                    # If value is still a dict, extract the 'value' field
                    value = value.get('value', '')
                sheet.cell(row=row + 1, column=col_idx, value=value)

        wb.save(Config.target_excel_path)
        print(f"成功将数据写入到Excel的第{row}行。")
        print("===============================================\n\n")

        # 打印详细的匹配信息
        # print("写入详情:")
        # for key, value in converted_dict.items():
        #     print(f"{key}: {value}")

    except Exception as e:
        print(f"写入Excel时发生错误: {e}")
        return


if __name__ == '__main__':
    # 目标结果模版的第一行（去除标题行）
    for row in range(1, Config.row_num):
        try:
            print(f"正在处理第{row}行数据...")
            start = time.time()
            # try:
            target_result_dict = {key: '' for key in Config.output_mapping_dict}
            # 第一轮匹配：读取报告文件
            keyword_result_dict_1, lcs_result_dict_1, sparkAI_result_dict_1 = match(row, round=1)
            print("第一轮匹配三个dict：", keyword_result_dict_1, lcs_result_dict_1, sparkAI_result_dict_1)
            # 第一轮匹配，提高置信度要求，以提升准确率
            final_result_dict_1 = compute_score_final_result(keyword_result_dict_1, lcs_result_dict_1,
                                                             sparkAI_result_dict_1)
            print("第一轮匹配最终结果：", final_result_dict_1)

            # 第二层匹配：读取非报告类文件
            keyword_result_dict_2, lcs_result_dict_2, sparkAI_result_dict_2 = match(row, round=2)
            print("第二轮匹配三个dict：", keyword_result_dict_2, lcs_result_dict_2, sparkAI_result_dict_2)
            # 第二轮，适当降低置信度要求，以提升召回率
            final_result_dict_2 = compute_score_final_result(keyword_result_dict_2, lcs_result_dict_2,
                                                             sparkAI_result_dict_2, CONFIDENCE_THRESHOLD=0.4)
            print("第二轮匹配结果：", final_result_dict_2)

            merge_final_result_dict = merge_result_dicts(target_result_dict, final_result_dict_1, final_result_dict_2)
            print("最终匹配结果：", merge_final_result_dict)

            # 将结果写入到目标Excel文件
            print(f"处理第{row}行数据耗时{time.time() - start}秒。")
            write_to_target_excel(row, merge_final_result_dict)
        except Exception as e:
            print(f"处理第{row}行时发生错误{e}。", )
            continue
