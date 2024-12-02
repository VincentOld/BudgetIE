# -*- coding: utf-8 -*-
"""
@Time ： 2024/11/27 16:25
@Auth ： vincent
@File ：util.py
@IDE ：PyCharm
"""
import re


# 主要用于辅助main函数的调用
# 合并多个dict为一个dict
def merge_dict(dict_list):
    merged_dict = {}
    for item_dict in dict_list:
        try:
            for key, value in item_dict.items():
                if key in merged_dict:
                    # 如果值相同，则不做任何操作，跳过
                    if value == merged_dict[key]:
                        continue
                    # 如果值不同，则将值存储为一个列表
                    elif isinstance(merged_dict[key], list):
                        if value not in merged_dict[key]:
                            merged_dict[key].append(value)
                    else:
                        merged_dict[key] = [merged_dict[key], value]
                else:
                    # 如果 key 不在 merged_dict 中，则直接添加
                    merged_dict[key] = value
        except AttributeError as e:
            print(f"Error: {e}")
            continue
    return merged_dict


def unify_keys(keyword_result_dict, lcs_result_dict, sparkAI_result_dict):
    """
    统一三个字典的 key 值，将 sparkAI 和 lcs 的 key 映射到 keyword 的 key
    """
    unified_lcs_result_dict = {}
    unified_sparkAI_result_dict = {}
    # 创建一个映射字典，处理关键词的差异
    key_mapping = {
        '安排预算稳定基金': '预算稳定基金',
        '支出年终结余': '一般公共预算支出年终结余'
    }
    def find_matching_key(target_key, keyword_keys):
        """查找最匹配的keyword key"""
        # 首先尝试直接匹配
        if target_key in keyword_keys:
            return target_key
        # 处理特殊映射
        for old_key, new_key in key_mapping.items():
            if old_key in target_key:
                modified_key = target_key.replace(old_key, new_key)
                if modified_key in keyword_keys:
                    return modified_key
        # 基于关键词匹配
        max_common = 0
        best_match = None
        target_chars = set(target_key)
        for keyword_key in keyword_keys:
            keyword_chars = set(keyword_key)
            common_chars = len(target_chars.intersection(keyword_chars))
            if common_chars > max_common and (
                    '预算稳定基金' in target_key and '预算稳定基金' in keyword_key or
                    '年终结余' in target_key and '年终结余' in keyword_key or
                    ('预算稳定基金' not in target_key and '年终结余' not in target_key)
            ):
                max_common = common_chars
                best_match = keyword_key
        return best_match
    # 处理 lcs_result_dict
    for lcs_key, value in lcs_result_dict.items():
        matching_key = find_matching_key(lcs_key, keyword_result_dict.keys())
        if matching_key:
            unified_lcs_result_dict[matching_key] = value
    # 处理 sparkAI_result_dict
    for sparkAI_key, value in sparkAI_result_dict.items():
        matching_key = find_matching_key(sparkAI_key, keyword_result_dict.keys())
        if matching_key:
            unified_sparkAI_result_dict[matching_key] = value
    return keyword_result_dict, unified_lcs_result_dict, unified_sparkAI_result_dict


# 提取数值和单位
def extract_amount_and_unit(value):
    if not isinstance(value, str):
        return 0.0, ""
    # 先匹配并忽略年份
    value = re.sub(r'20\d{2}年?', '', value)
    # 提取金额和单位
    match = re.search(r'([\d,]+\.?\d*)(亿元|万元|亿|万|元)?', value)
    if match:
        amount_str = match.group(1).replace(',', '')
        try:
            amount = float(amount_str)
            unit = match.group(2) if match.group(2) else ""
            return amount, unit
        except ValueError:
            return 0.0, ""
    return 0.0, ""


# 将金额转换为元为单位
def convert_to_base_unit(amount, unit):
    """将金额转换为元为单位"""
    unit_conversion = {
        "亿元": 100000000,
        "千万元": 10000000,
        "万元": 10000,
        "元": 1,
        "亿": 100000000,
        "万": 10000,
    }
    if unit in unit_conversion:
        return amount * unit_conversion[unit]
    return amount


#先将final_result_dict1写入target_result_dict，然后再将final_result_dict2写入target_result_dict中value仍为空的key中
def merge_result_dicts(target_result_dict, final_result_dict1, final_result_dict2):
    # 先处理 final_result_dict1
    for key, value in final_result_dict1.items():
        # 去掉 dict1 中 key 的前两个字
        key_substr = key[2:]
        for target_key in target_result_dict:
            if target_key == key_substr and not target_result_dict[target_key]:
                target_result_dict[target_key] = value
                break
    for key, value in final_result_dict2.items():
        # 去掉 dict2 中 key 的前两个字
        key_substr = key[2:]
        for target_key in target_result_dict:
            if target_key == key_substr and not target_result_dict[target_key]:
                target_result_dict[target_key] = value
                break
    return target_result_dict


def merge_short_texts(candidated_list, target_length=100, min_text_length=20):
    """
    合并相邻的短文本，直到列表长度小于等于目标长度，保持原始格式

    Args:
        candidated_list (list): batch_sentence_cls的输出列表
        target_length (int): 目标列表长度
        min_text_length (int): 判定为短文本的长度阈值

    Returns:
        list: 和输入格式相同的处理后的列表
    """
    if len(candidated_list) <= target_length:
        return candidated_list

    result = candidated_list.copy()

    while len(result) > target_length:
        merged = False

        # 从前往后遍历，寻找可以合并的相邻短文本
        for i in range(len(result) - 1):
            if len(str(result[i])) <= min_text_length and len(str(result[i + 1])) <= min_text_length:
                # 合并相邻文本，保持原始格式
                merged_text = str(result[i]) + " " + str(result[i + 1])
                # 删除原始的两个文本，插入合并后的文本
                result.pop(i + 1)
                result[i] = merged_text
                merged = True
                break

        # 如果没有找到可以合并的短文本，增加短文本的判定阈值
        if not merged:
            min_text_length += 10

        # 防止无限循环
        if min_text_length > 200:  # 设置一个合理的上限
            break

    return result