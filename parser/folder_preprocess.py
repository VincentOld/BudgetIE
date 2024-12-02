# -*- coding: utf-8 -*-
"""
@Time ： 2024/11/6 17:35
@Auth ： vincent
@File ：folder_preprocess.py
@IDE ：PyCharm
"""

import shutil

'''文件夹预处理：主要功能如下：
1. 删除非指定类型的文件：仅保留 .pdf、.html、.xlsx、.xls、.doc、.docx 格式的文件，其他格式的文件会被删除。
2. 解压并删除压缩文件：对 .zip 格式的文件进行解压，解压完成后删除原压缩包文件。
3. 删除特定文件：删除文件名中包含“报告”二字的 .xlsx 和 .xls 文件。
4. 删除空文件：检查文件大小，如果文件为空（大小为 0），则将其删除。
5. 删除空文件夹：检查文件夹内容，如果文件夹为空，则将其删除。
6. 将大写后缀PDF、XLS、XLSX、DOC、DOCX、HTML都转换为对应的小写后缀
'''
import os
import zipfile
from config import Config


def folder_preprocess(folder_path):
    # 允许的文件扩展名（小写形式）
    allowed_extensions = {".pdf", ".html", ".xlsx", ".xls", ".doc", ".docx"}

    # 遍历文件夹中的所有文件和文件夹
    for root, dirs, files in os.walk(folder_path, topdown=False):
        # 首先，处理文件夹的重命名
        for dir in dirs:
            dir_path = os.path.join(root, dir)
            # 如果子文件夹名是"伊犁州"，则改为"伊犁"
            if dir == "伊犁州":
                new_dir_name = "伊犁"
                new_dir_path = os.path.join(root, new_dir_name)
                os.rename(dir_path, new_dir_path)  # 重命名文件夹
                dirs[dirs.index(dir)] = new_dir_name  # 更新dirs列表中的文件夹名称

        # 处理文件
        for file in files:
            file_path = os.path.join(root, file)
            _, ext = os.path.splitext(file)

            # 将文件扩展名转换为小写
            ext = ext.lower()

            # 如果是压缩文件（.zip），则解压并删除压缩包
            if ext == ".zip":
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(root)  # 解压到当前目录
                os.remove(file_path)  # 删除原始压缩包

            # 如果文件扩展名不在允许列表中，删除文件
            elif ext not in allowed_extensions:
                os.remove(file_path)

            # 删除文件名包含“报告”的 .xlsx 和 .xls 文件
            elif ext in {".xlsx", ".xls"} and "报告" in file:
                os.remove(file_path)

            # 如果文件为空（大小为0），删除文件
            elif os.path.getsize(file_path) == 0:
                os.remove(file_path)

            # 将文件扩展名更改为小写形式（如果不在允许的扩展名中，直接删除）
            else:
                new_file_name = file.lower()
                new_file_path = os.path.join(root, new_file_name)

                # 如果文件名和扩展名变更后路径不同，重命名文件
                if new_file_name != file:
                    os.rename(file_path, new_file_path)

        # 删除空文件夹
        for dir in dirs:
            dir_path = os.path.join(root, dir)
            if not os.listdir(dir_path):  # 检查文件夹是否为空
                os.rmdir(dir_path)

    print("文件过滤和清理已完成。")


# 弃用该函数
def organize_files(folder_path):
    for province in os.listdir(folder_path):
        province_path = os.path.join(folder_path, province)
        for city in os.listdir(province_path):
            city_path = os.path.join(province_path, city)

            budget_exec_path = os.path.join(city_path, '预算')
            final_account_path = os.path.join(city_path, '决算')

            # 创建决算和预算执行文件夹（如果不存在）
            os.makedirs(final_account_path, exist_ok=True)
            os.makedirs(budget_exec_path, exist_ok=True)

            # 遍历城市文件夹中的文件
            for item in os.listdir(city_path):
                item_path = os.path.join(city_path, item)

                # 检查是否是文件
                if os.path.isfile(item_path):
                    try:
                        if '预算' in item:
                            # 移动文件到预算执行文件夹
                            shutil.move(item_path, budget_exec_path)
                            print(f'Moved: {item} to {budget_exec_path}')
                        else:
                            shutil.move(item_path, final_account_path)
                            print(f'Moved: {item} to {final_account_path}')
                    except Exception as e:
                        print(f'Error moving {item}: {e}')
                elif os.path.isdir(item_path) and item not in ['预算', '决算']:
                    # 移动子文件夹中的文件到决算文件夹
                    for file in os.listdir(item_path):
                        file_path = os.path.join(item_path, file)
                        try:
                            if os.path.isfile(file_path) and not os.path.exists(os.path.join(final_account_path, file)):
                                shutil.move(file_path, final_account_path)
                        except Exception as e:
                            print(f'Error moving {file}: {e}')
                    # 删除空的子文件夹
                    shutil.rmtree(item_path, ignore_errors=True)

            # 对预算执行子文件夹的处理
            for item in os.listdir(budget_exec_path):
                item_path = os.path.join(budget_exec_path, item)
                if os.path.isdir(item_path):
                    for file in os.listdir(item_path):
                        file_path = os.path.join(item_path, file)
                        try:
                            if os.path.isfile(file_path) and not os.path.exists(os.path.join(budget_exec_path, file)):
                                shutil.move(file_path, budget_exec_path)
                        except Exception as e:
                            print(f'Error moving {file}: {e}')
                    shutil.rmtree(item_path, ignore_errors=True)


if __name__ == '__main__':
    folder_path = Config.base_dataset_path
    folder_preprocess(folder_path)
