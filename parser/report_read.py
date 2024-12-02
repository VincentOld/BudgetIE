import itertools
import os
import re
import docx
import win32com.client as win32
from bs4 import BeautifulSoup
from config import Config
import easyocr
import numpy as np
from PIL import Image
import io
import fitz
os.environ["NUM_WORKERS"] = "4"
# 初始化 OCR Reader
ocr_reader = easyocr.Reader(['ch_sim'], gpu=False, download_enabled=False)
convert_doc = Config.convert_doc


# 提取PDF文件中的文本
def process_page_batch(pages, ocr_reader, batch_size=4):
    text_results = []
    for i in range(0, len(pages), batch_size):
        batch_pages = pages[i:i + batch_size]
        batch_images = []
        target_size = (600, 600)
        for page in batch_pages:
            pix = page.get_pixmap(dpi=200)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            img = img.resize(target_size)
            img_np = np.array(img)
            batch_images.append(img_np)
        results = ocr_reader.readtext_batched(batch_images, detail=0)
        # 确保每个页面的文本是字符串
        for page_result in results:
            if isinstance(page_result, list):
                text_results.append(" ".join(str(x) for x in page_result))
            else:
                text_results.append(str(page_result))
    return [text for text in text_results if text.strip()]


def extract_text_from_pdf(pdf_path, ocr=True):
    text = ""
    try:
        with fitz.open(pdf_path) as pdf:
            # 先收集需要OCR的页面
            pages_needing_ocr = []
            regular_text = []

            for page_number in range(pdf.page_count):
                page = pdf[page_number]
                page_text = page.get_text()

                if page_text.strip():
                    regular_text.append(clean_text(page_text))
                elif ocr:
                    pages_needing_ocr.append(page)

            # 合并常规文本
            text = "\n".join(regular_text)

            # 如果有需要OCR的页面，批量处理
            if pages_needing_ocr and ocr:
                if len(pages_needing_ocr) >10:
                    pages_needing_ocr = pages_needing_ocr[:10]
                print(f"使用OCR处理{len(pages_needing_ocr)}页")
                ocr_results = process_page_batch(pages_needing_ocr, ocr_reader)
                ocr_text = "".join(itertools.chain(*map(split_text_by_period, ocr_results)))
                text = text + "\n" + ocr_text if text else ocr_text
    except Exception as e:
        print(f"OCR处理错误: {e}")
    return clean_text(text)


# 提取Word文件中的文本（支持 .docx 文件）
def extract_text_from_word(word_path):
    if word_path.endswith('.docx'):
        # 使用 python-docx 处理 .docx 文件
        doc = docx.Document(word_path)
        text = ""
        # 遍历文档中的每个段落
        for para in doc.paragraphs:
            text += para.text + "\n"  # 将每个段落的文本连接起来
        return clean_text(text)
    else:
        raise ValueError

#读取doc文件
def extract_text_from_doc(doc_path):
    try:
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        word = win32com.client.Dispatch("Word.Application")  # 使用Dispatch而不是gencache，避免缓存问题
        word.DisplayAlerts = 0
        doc = word.Documents.Open(doc_path)
        # 提取文本内容
        text = doc.Content.Text
        # 关闭文件并退出Word应用
        doc.Close()
        word.Quit()
        pythoncom.CoUninitialize()
        return text.strip()  # 返回提取的文本内容
    except Exception as e:
        print(f"读取文件失败: {e}")
        return ""  # 如果无法读取文件，返回空字符串

# 提取HTML文件中的文本
def extract_text_from_html(html_path):
    with open(html_path, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'lxml')  # 使用lxml解析器
        # 提取所有的文本内容
        text = soup.get_text(separator=' ', strip=True)
    return clean_text(text)


# 清理文本，去掉多余的空白字符（如换行符、制表符等）
def clean_text(text):
    # 使用正则表达式去除多余的空白字符（换行符、制表符、连续空格）
    cleaned_text = re.sub(r'\s+', '', text)  # 将所有空白字符（包括换行符、制表符、连续空格）替换为单个空格
    cleaned_text = cleaned_text.strip()  # 去掉开头和结尾的空格
    return cleaned_text


# 按句号分割文本为列表，并筛选包含"元"的句子
def split_text_by_period(text):
    sentences = re.split(r'(?<=。|；|！|？|：)', clean_text(text))
    sentences_with_yuan = []
    # 临时存储合并句子的标志
    previous_sentence = ""
    for sentence in sentences:
        # 如果当前句子包含“元”，直接保留
        if '元' in sentence:
            if previous_sentence:
                # 如果前一句需要合并，合并到当前句
                sentences_with_yuan.append(previous_sentence + sentence)
                previous_sentence = ""  # 重置前一句
            else:
                sentences_with_yuan.append(sentence)
        else:
            # 如果当前句子不包含“元”，但是包含“预算”或“决算”或年份等
            if '预算' in sentence or '决算' in sentence or re.search(r'\d{4}年', sentence):
                previous_sentence = sentence  # 记录下来，准备与下一个句子合并
    if previous_sentence:
        sentences_with_yuan.append(previous_sentence)
    return sentences_with_yuan


# 将 .doc 文件转换为 .docx 文件
def convert_doc_to_docx(doc_path):
    try:
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        word = win32com.client.gencache.EnsureDispatch("Word.Application")  # 使用gencache
        word.DisplayAlerts = 0
        doc = word.Documents.Open(doc_path)
        new_file_path = doc_path.replace(".doc", ".docx")
        doc.SaveAs2(new_file_path, FileFormat=16)  # 使用SaveAs2
        doc.Close()
        word.Quit()
        pythoncom.CoUninitialize()
        return new_file_path
    except Exception as e:
        print(f"转换失败: {e}")
        return doc_path


# old：检查文件名是否符合条件(更精细，将表格类pdf也排除在外了）
def is_valid_filename1(file_name):
    if "报告" in file_name or "表" not in file_name:
        return True
    # 文件名最后一个字符不是"表"，且文件名不包含“决算表”、“预算表”、“执行报表”
    if file_name.endswith("表"):
        return False
    if any(keyword in file_name for keyword in ["决算表", "预算表", "执行报表"]):
        return False
    return True


# 检查文件名是否符合条件(更粗放，读取文件名中不包含“报告”的doc、docx、html、pdf文件，主要就是表格类PDF）
def is_valid_filename2(file_name):
    if "报告" in file_name:
        return False
    return True


# 处理文件夹下的所有文件，返回合并去重的句子集合，默认精细化读取纯报告类文件
def process_reportFiles_in_folder(folder_path, is_valid_filename=is_valid_filename1, convert_doc=convert_doc):
    from parser.folder_read import add_tags_to_sentences
    result_set = set()

    # 遍历文件夹中的所有文件
    for root, _, files in os.walk(folder_path):
        for file in files:
            file_path = os.path.join(root, file)
            file_name, file_extension = os.path.splitext(file)
            file_extension = file_extension.lower()

            # 只处理符合条件的文件
            if not is_valid_filename(file_name):
                continue  # 跳过不符合条件的文件
            if file_extension == '.pdf':
                # print(file_path)
                text = extract_text_from_pdf(file_path)
                sentences = split_text_by_period(text)
                result_set.update(sentences)
            elif file_extension == '.docx':
                text = extract_text_from_word(file_path)
                sentences = split_text_by_period(text)
                result_set.update(sentences)

            elif file_extension == '.html':
                text = extract_text_from_html(file_path)
                sentences = split_text_by_period(text)
                result_set.update(sentences)

            elif file_extension == '.doc':
                if convert_doc:
                    # 将 .doc 文件转换为 .docx 文件
                    try:
                        new_file_path = convert_doc_to_docx(file_path)
                        text = extract_text_from_word(new_file_path)
                        sentences = split_text_by_period(text)
                        result_set.update(sentences)
                    except Exception as e:
                        text = extract_text_from_doc(file_path)
                        sentences = split_text_by_period(text)
                        result_set.update(sentences)
                else:
                    print(f"跳过文件 {file_path} (未转换)")
    return add_tags_to_sentences(list(result_set))

# 使用示例：处理指定文件夹路径
# folder_path = r"H:\桌面\工作\已入职\1 项目内容\星火燎原\基于深度学习的自然场景文字信息提取模型\数据\test"  # 替换为你的文件夹路径
# unique_sentences = process_reportFiles_in_folder(folder_path, convert_doc=True)
# print(unique_sentences)
