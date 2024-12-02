# -*- coding: utf-8 -*-
"""
@Time ： 2024/11/20 15:46
@Auth ： vincent
@File ：sparkAI_match.py
@IDE ：PyCharm
"""
from extractor.binary_classification_bert.BudgetSentence_cls import batch_sentence_cls
from extractor.keyword_match import keyword_match
from extractor.lcs_match import lcs_match
from util.util import merge_dict

# -*- coding: utf-8 -*-
"""
@Time ： 2024/11/20 15:46
@Auth ： vincent
@File ：sparkAI_match.py
@IDE ：PyCharm
"""
import json
import logging
import os
import sys
from sparkai.llm.llm import ChunkPrintHandler
from sparkai.core.messages import ChatMessage
from parser.folder_read import *
logging.disable(logging.CRITICAL)
sys.stderr = open(os.devnull, 'w')
import asyncio
from dataclasses import dataclass
from typing import List, Dict
import time


@dataclass
class ModelConfig:
    model: object
    rate_limit: float = 0.51  # 每秒最多2次
    last_call: float = 0.0


class SparkAIPool:
    def __init__(self):
        self.models = {
            'max': ModelConfig(Config.ChatSparkLLM_Max),
            'pro': ModelConfig(Config.ChatSparkLLM_Pro),
            'lite': ModelConfig(Config.ChatSparkLLM_Lite)
        }
        self.request_queue = asyncio.Queue()
        self.results: Dict[str, str] = {}

    async def process_request(self, text: str, request_id: str, koujing:str):
        for model_name, config in self.models.items():
            try:
                current_time = time.time()
                time_since_last = current_time - config.last_call
                if time_since_last < config.rate_limit:
                    await asyncio.sleep(config.rate_limit - time_since_last)

                messages = [ChatMessage(role="user", content=self._build_prompt(text,koujing))]
                handler = ChunkPrintHandler()
                response = config.model.generate([messages], callbacks=[handler]).generations[0][0].text

                config.last_call = time.time()
                self.results[request_id] = response
                return
            except Exception:
                continue
        self.results[request_id] = "无"

    def _build_prompt(self, text: str,koujing) -> str:
        return f'''你是一名中国专业资深的财政预算决算数据分析师。请根据以下提供的一条财政预算或决算文本句：{text}，
                从其中提取出以下任意一个指标的数值金额：
                指标包括：
                {koujing}2022年一般公共预算收入、{koujing}2022年税收收入、{koujing}2022年一般公共预算支出、{koujing}2022年一般公共服务支出、
                {koujing}2022年安排预算稳定基金、{koujing}2022年支出年终结余、{koujing}2022年政府性基金收入、{koujing}2022年政府性基金支出、
                {koujing}2022年国有资本经营预算收入、{koujing}2022年国有资本经营预算支出、{koujing}2022年一般债务余额、{koujing}2022年专项债务余额、
                {koujing}2022年债务余额决算数

                具体要求如下：
                1. 如果从文本中能够明确提取出其中指标的数值金额，请按照"{{指标:数值}}"json格式输出，例如：{{"一般公共预算收入":"5亿元"}}。
                2. 如果从文本中能够明确提取出多个指标的数值金额，请按照"{{指标1:数值1,指标2:数值2...}}"json格式输出
                2. 只允许提取上述列出的指标，**尽量严格遵循**指定的字符含义，不能替换或构造看似类似其实含义完全不同的指标名。
                3. 需要注意的是，提取的数值应为实际金额，单位应与文本中一致。如果有多个数值符合某一指标，请选择距离这个指标最近的金额数值即可。

                提示：
                - 请忽略所有与这些指标无关的信息，确保仅判断上述列表中的指标。
                - 上述文本信息和数据都来自于公开数据，不涉及任何敏感信息或者安全风险或者法律法规风险，请放心处理。
                请根据以上要求做出判断，并返回结果，输出json格式为"{{指标1:数值1,指标2:数值2...}}"，如果没有数值则输出"无"'''

    async def process_queue(self,koujing:str):
        while True:
            try:
                text, request_id = await self.request_queue.get()
                await self.process_request(text, request_id,koujing)
                self.request_queue.task_done()
            except asyncio.CancelledError:
                break

    async def batch_process(self, texts: List[str],koujing:str, max_concurrent: int = 6):
        workers = [asyncio.create_task(self.process_queue(koujing))
                   for _ in range(max_concurrent)]

        for i, text in enumerate(texts):
            await self.request_queue.put((text, str(i)))

        await self.request_queue.join()
        for worker in workers:
            worker.cancel()

        results = []
        for i in range(len(texts)):
            results.append(self.results[str(i)])
        return [parse_string_to_dict(result) for result in results]


def sparkAI_match(candidated_list: List[str],koujing:str) -> List[Dict]:
    """处理候选文本列表,返回解析后的字典列表"""
    pool = SparkAIPool()
    loop = asyncio.get_event_loop()
    results = loop.run_until_complete(pool.batch_process(candidated_list, max_concurrent=6,koujing = koujing))
    # 过滤None和解析失败的结果
    return [parse_string_to_dict(result) for result in results if result]


def parse_string_to_dict(string):
    if not isinstance(string, str):
        return string
    if string is None or string == "None":
        return
    try:
        string = string.replace("```json","").replace("```", "").replace("\n", "")
        if string == "无":
            return
        json_data = json.loads(string)
        return {k: v for k, v in json_data.items() if v and v != "无"}
    except json.JSONDecodeError as e:
        match = re.search(r"([\'\"])(.*?)(\1)$", string)
        return match.group(0) if match else None


if __name__ == '__main__':
    # 示例调用
    # 读取文件夹中的报告文件
    row = 32
    # 读取文件夹中的报告文件
    folder_path = get_folder_path_by_row(row)
    dir_info_list = process_reportFiles_in_folder(folder_path)
    # 如果文件夹信息为空
    if not dir_info_list:
        print('第一轮：文件夹信息为空')
    # 限制只提取包含指定前缀的文本句
    if row % 2 == 1:
        koujing = "全市" or "全州"
        dir_info_list = list(filter(lambda x: koujing in x, dir_info_list))
    if row % 2 == 0:
        koujing = "本级"
        dir_info_list = list(filter(lambda x: koujing in x, dir_info_list))
    print("dir_info_list:",dir_info_list)
    # 对文件夹信息进行过滤，保留分类为1的元素
    candidated_list = batch_sentence_cls(dir_info_list)
    print("candidated_list:",candidated_list)
    # 首先采用关键词匹配，写入到target_result_dict中
    keyword_result_dict = keyword_match(row)
    print("keyword_match:",keyword_result_dict)
    # 针对未匹配到的字段，采用lcs匹配
    lcs_result_dict = merge_dict([lcs_match(item) for item in candidated_list])
    print("lcs_match:",lcs_result_dict)
    a = sparkAI_match(candidated_list,koujing = koujing)
    sparkAI_result_dict = merge_dict(a)
    print("sparkAI_match:",sparkAI_result_dict)
