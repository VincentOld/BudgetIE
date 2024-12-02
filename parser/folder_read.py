# -*- coding: utf-8 -*-
"""
@Time ： 2024/11/8 16:26
@Auth ： vincent
@File ：folder_read.py
@IDE ：PyCharm
"""
import re

from parser.report_trans_table import report_transform_table
from parser.report_read import process_reportFiles_in_folder
from parser.table_read import process_tableFiles_in_folder
import openpyxl
from config import Config

# 定义配置类
base_dataset_path = Config.base_dataset_path
target_excel_path = Config.target_excel_path
folder_structure = Config.folder_structure

# 加载 Excel 文件
workbook = openpyxl.load_workbook(target_excel_path)
sheet = workbook.active


# 反向匹配省市以获取路径，实现文件路径定位
def get_folder_path_by_row(row_number):
    row = sheet[row_number + 1]  # Excel 行从 1 开始
    province = row[0].value  # 省
    city = row[1].value  # 市
    # 尝试找到省、市的对应文件夹名称
    matched_province = None
    matched_city = None
    for folder_province in folder_structure:
        if folder_province in province:  # 反向匹配省份
            matched_province = folder_province
            for folder_city in folder_structure[folder_province]:
                if folder_city in city:  # 反向匹配城市
                    matched_city = folder_city
                    break
            if matched_city:
                break
    # 返回匹配的省市文件夹路径
    if matched_province and matched_city:
        return folder_structure[matched_province][matched_city]
    else:
        return None  # 无匹配项时返回 None


#转换一些字段
def convert_list(sentences):
    conversion_dict= Config.conversion_dict
    return [conversion_dict.get(item, item) for item in sentences]


#功能：将句子列表中的句子添加标签
def add_tags_to_sentences(sentences):
    sentences = convert_list(sentences)
    result = []
    previous_tag = None  # 用于存储前一个有效的标签
    for sentence in sentences:
        # 使用正则来检查是否包含"本市""本州"或"本级"
        match = re.search(r'(本级|全市|全州)', sentence)
        if match:
            # 如果句子包含标签，更新 previous_tag
            previous_tag = match.group(0)
            result.append(sentence)
        elif previous_tag:  # 如果没有标签，且前面有有效标签
            # 检查句子是否已经以标签开头
            if not sentence.startswith(previous_tag):
                # 将前一个标签添加到当前句子的开头
                result.append(previous_tag + sentence)
            else:
                result.append(sentence)
        else:
            result.append(sentence)

    return result


# 读取一个文件夹下的所有文件，输入是文件夹路径，输出是字符串set
def read_folder(row_number,read_table=Config.read_table):
    folder_path = get_folder_path_by_row(row_number)
    report = process_reportFiles_in_folder(folder_path)
    report = add_tags_to_sentences(report)
    #如果不读取表格文件
    if not read_table:
        return report
    #如果读取表格文件
    report_transform_table(folder_path)
    table = process_tableFiles_in_folder(folder_path)
    total = report.union(table)
    folder_info = list(total)
    return folder_info


if __name__ == '__main__':
    for i in range(1,15,2):
        try:
            folder_info = read_folder(i)
            print(folder_info)
        except Exception as e:
            print(f"读取文件夹时发生错误: {e}")
            continue
