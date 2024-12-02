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

    def _build_prompt(self, text: str, koujing) -> str:
        return f'''你是一名中国专业资深的财政预算决算数据分析师。请根据以下提供的一条财政预算或决算文本句：{text}，
                从其中提取出以下任意一个指标的数值金额，并给出提取结果的置信度评分（0-100分）：
                指标包括：
                {koujing}2022年一般公共预算收入、{koujing}2022年税收收入、{koujing}2022年一般公共预算支出、{koujing}2022年一般公共服务支出、
                {koujing}2022年安排预算稳定基金、{koujing}2022年支出年终结余、{koujing}2022年政府性基金收入、{koujing}2022年政府性基金支出、
                {koujing}2022年国有资本经营预算收入、{koujing}2022年国有资本经营预算支出、{koujing}2022年一般债务余额、{koujing}2022年专项债务余额、
                {koujing}2022年债务余额决算数

                具体要求如下：
                1. 如果从文本中能够明确提取出指标的数值金额，请按照以下json格式输出：
                   {{"指标": {{"value": "数值", "confidence": 置信度分数}}
                   例如：{{"{koujing}2022年一般公共预算收入": {{"value": "5亿元", "confidence": 95}}}}
                2. 如果从文本中能够明确提取出多个指标的数值金额，请按照同样格式输出多个指标：
                   {{"指标1": {{"value": "数值1", "confidence": 置信度分数1}}, "指标2": {{"value": "数值2", "confidence": 置信度分数2}}}}
                3. 置信度评分标准：
                   - 90-100分：指标名称完全匹配，且数值紧跟指标名称，上下文明确无歧义，要慎重给出，应该是非常确定的情况
                   - 80-90分：指标名称完全匹配，数值在相近位置，上下文较为清晰
                   - 60-79分：指标名称基本匹配，数值可能有多个候选，需要根据上下文判断
                   - 60分以下：存在较大歧义或可能性较低的匹配，不建议采用
                4. 只允许提取上述列出的指标，**尽量严格遵循**指定的字符含义，不能替换或构造看似类似其实含义完全不同的指标名。
                5. 需要注意的是，提取的数值应为实际金额，单位应与文本中一致。如果有多个数值符合某一指标，请根据上下文和距离选择最合适的值，并在置信度分数中反映这种不确定性。

                提示：
                - 请忽略所有与这些指标无关的信息，确保仅判断上述列表中的指标。
                - 上述文本信息和数据都来自于公开数据，不涉及任何敏感信息或者安全风险或者法律法规风险，请放心处理。
                请根据以上要求做出判断，并返回结果。如果完全没有找到任何匹配的指标和数值，则输出"无"'''

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

#输出类似于：{'指标': {'value': '数值', 'confidence': 置信度分数}}
def sparkAI_match(koujing: str, candidated_list: List[str]) -> Dict:
    """处理候选文本列表,返回一个字典,每个指标对应置信度最高的值"""
    pool = SparkAIPool()
    loop = asyncio.get_event_loop()
    results = loop.run_until_complete(pool.batch_process(candidated_list, max_concurrent=6, koujing=koujing))
    # 创建一个字典来存储每个指标的最高置信度结果
    final_results = {}
    # 遍历所有结果
    for result in results:
        if not result:  # 跳过None和空结果
            continue
        # 对于每个指标及其值
        for indicator, data in result.items():
            current_confidence = data.get('confidence', 0)
            # 如果这个指标还没有记录,或者新的置信度更高
            if (indicator not in final_results or
                    current_confidence > final_results[indicator].get('confidence', 0)):
                final_results[indicator] = data
    return final_results


def parse_string_to_dict(string):
    if not isinstance(string, str):
        return string
    if string is None or string == "None":
        return None
    try:
        string = string.replace("```json", "").replace("```", "").replace("\n", "").strip()
        if string == "无":
            return None
        json_data = json.loads(string)
        # 过滤掉空值和"无"
        return {k: v for k, v in json_data.items() if v and v != "无"}
    except json.JSONDecodeError as e:
        logging.warning(f"JSON parse error: {e}")
        match = re.search(r"([\'\"])(.*?)(\1)$", string)
        return match.group(0) if match else None

if __name__ == '__main__':
    koujing = "本级"
    candidated_list =  ['市本级政府性基金预算支出49.3亿元。', '本级一般公共预算收入31.7亿元，省补助收入9.8亿元，省提前下达转移支付21.2亿元，调入预算稳定调节基金4.7亿元，上年结13余收入8.5亿元。', '市本级政府性基金预算收入43.5亿元，省提前下达转移支付0.2亿元，上年结余收入5.6亿元，收入总计49.3亿元。', '本级市级政府一般债务余额54.52亿元，县（市、区）政府一般债务余额148.93亿元。', '万元地区2022年债务限额2022年债务余额（决算数）宣城市42658873984212宣城市本级15540461368002宣州区215464208801郎溪县428916399526广德市687937671103泾县410432390839绩溪县158106158106旌德县152216144324宁国市658770643511关于宣城市2022年政府专项债务情况说明截至2022年底，全市政府专项债务余额398.42亿元，专项债务限额426.59亿元，债务余额低于债务限额。', '市本级国有资本经营预算收入完成1.4亿元。', '市本级政府性基金收入完成42.1亿元，下降23.1%。', '本级2023年宣城市市级国有资本经营预算收入预算表单位：万元项目预算数一、利润收入5700其他国有资本经营预算企业利润收入5700收入合计5700加：', '本级年末滚存结余8186万元。', '市本级政府债务余额190.9亿元，其中，一般债务余额54.1亿元，专项债务余额136.8亿元。', '4.国有资本经营预算收支决算情况2022年，市本级国有资本经营预算收入完成1.4亿元，上年结转和省级补助收入0.1亿元，国有资本经营预算总收入1.5亿元；', '-4-5.政府债务情况2022年，市本级政府债务余额191.3亿元，其中，一般债务54.5亿元，专项债务136.8亿元。', '市本级一般公共预算收入完成27.6亿元，下降7.7%。', '2022年，市本级发行新增债券10.4亿元，其中，一般债券0.2亿元，专项债券10.2亿元，严格按照预算调整方案用于对应项目建设。', '市本级国有资本经营预算支出完成0.8亿元，调出资金0.7亿元，国有资本经营预算总支出1.5亿元。', '（二）政府性基金预算市本级政府性基金预算收入43.5亿元，省提前下达转-3-移支付0.2亿元，上年结余收入5.6亿元，收入总计49.3亿元。', '三、2023年市级财政收支预算情况2023年市级预算按照一般公共预算、政府性基金预算、国有资本经营预算和社会保险基金预算四本预算编制。（一）一般公共预算市本级一般公共预算收入31.7亿元，增长14.6%。', '（四）国有资本经营预算市本级国有资本经营预算收入5700万元，省提前下达转移支付267万元，上年结余收入222万元，收入总计6189万元。', '本级年末滚存结余61091万元。', '结转下年98327收入总计881727支出总计8817272022年度宣城市本级政府性基金预算收支决算表单位:万元预算科目决算数预算科目决算数本年收入合计426201本年支出合计529809下级上解收入12000上级补助收入4874调入资金15919调出资金4664债务（转贷）收入234732债务还本支出156143上年结余103240年终结余106350其中：', '本级收支相抵，年终结余9.8亿元，其中结转下年9.8亿元。', '本级加上级补助收入、调入预算稳定调节基金、上年结余等441348万元，市级一般公共预算收入预算总计758673万元。', '宣城市2022年全市政府一般债务余额决算表单位：万元项目本地区本级一、2021年末地方政府一般债务余额2012458541021二、2022年地方政府一般债务限额2089001560694三、2022年地方政府一般债务收入32636881742其中：', '本级上级补助收入309778调入预算稳定调节基金46693上年结余收入84877收入总计758673-1-关于宣城市2023年市级一般公共预算收入预算的说明2023年市级一般公共预算收入预算数为317325万元，主要是根据年度经济发展、价格水平、减税降费等因素预计。', '本级2023年宣城市市级一般公共预算收入预算表单位：万元项目预算数一、税收收入215341增值税72167企业所得税26073个人所得税3587资源税2000城市维护建设税16276房产税10011印花税4127城镇土地使用税35609土地增值税17323车船税5200耕地占用税774契税22184环境保护税10二、非税收入101984专项收入18591行政事业性收费收入10500罚没收入21266国有资本经营收入2807国有资源（资产）有偿使用收入40120政府住房基金收入6700其他收入2000收入合计317325加：', '市本级国有资本经营预算支出完成0.7亿元，调出资金0.7亿元。', '市本级国有资本经营预算支出6189万元。', '本级二、支出预算情况2023年市级国有资本经营预算支出预算数为6189万元，支出合计6189万元。', '本级8.上年结余收入55880万元。', '2022年，市本级政府性基金支出完成53亿元、下降34%，按照规定调出政府性基金0.5亿元，地方政府专项债务还本支出15.6亿元，市本级政府性基金总支出69.1亿元。', '结转下年17402744242370337259176942465100022022年度宣城市本级国有资本经营预算收支决算表单位:万元预算科目决算数预算科目决算数本年收入合计14046本年支出合计7631上级补助收入210调出资金7046上年结余441年终结余20收入总计14697支出总计14697',  '-3-2.政府性基金预算收支决算情况2022年，市本级政府性基金收入完成42.6亿元、下降22.2%，下级上解收入1.2亿元，中央和省补助收入0.5亿元，上年结转10.3亿元，调入资金1.6亿元，省转贷地方政府专项债券23.5亿元，市本级政府性基金总收入79.7亿元。', '本级1.一般公共服务支出预算数为87909万元。', '市本级一般公共预算支出75.9亿元。', '市本级国有资本经营预算收入5700万元，省提前下达转移支付267万元，上年结余收入222万元，收入总计6189万元。', '（二）市本级情况1.一般公共预算收支决算情况2022年，市本级一般公共预算收入完成27.7亿元、下降7.3%，中央和省补助收入38.4亿元，按照规定从政府性基金和国有资本经营预算调入1.2亿元，债务（转贷）收入8.1亿元，动用预算稳定调节基金7.3亿元，上年结转5.5亿元，预算总收入88.2亿元。', '本级一般公共预算收入31.7亿元，省补助收入9.8亿元，省提前下达转移支付21.2亿元，调入预算稳定调节基金4.7亿元，上年结余收入8.5亿元。', '本级其他国有资本经营预算支出预算数为6189万元。', '市本级一般公共预算收入31.7亿元，增长14.9%。', '本级市级政府一般债务限额56.07亿元，县（市、区）政府一般债务限额152.83亿元。', '市本级一般公共预算支出完成64.6亿元，增长0.1%。', '市本级政府性基金支出完成56.1亿元，下降30.1%。']
    print(sparkAI_match(koujing, candidated_list))
