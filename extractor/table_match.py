import torch
import pandas as pd
import re
from transformers import TapasTokenizer, TapasForQuestionAnswering
from typing import Dict, List, Union
import logging
from config import Config
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
#效果很一般 暂时弃用

class BudgetIndicatorExtractor:
    def __init__(self, model_name: str = Config.tapas_model_path):
        self.indicators = {
            "一般公共预算收入": ["一般公共预算收入", "公共预算收入"],
            "税收收入": ["税收收入", "税收", "税收总额"],
            "一般公共预算支出": ["一般公共预算支出", "公共预算支出"],
            "一般公共服务支出": ["一般公共服务支出", "公共服务支出"],
            "预算稳定基金": ["预算稳定基金", "稳定基金"],
            "一般公共预算支出年终结余": ["年终结余", "结余资金", "一般公共预算结余"],
            "政府性基金收入": ["政府性基金收入", "基金收入"],
            "政府性基金支出": ["政府性基金支出", "基金支出"],
            "国有资本经营预算收入": ["国有资本经营预算收入", "国有资本收入"],
            "国有资本经营预算支出": ["国有资本经营预算支出", "国有资本支出"],
            "地方政府一般债务余额": ["一般债务余额", "一般债务"],
            "地方政府专项债务余额": ["专项债务余额", "专项债务"],
            "地方政府债务余额决算数": ["债务余额决算数", "债务余额合计"]
        }

        try:
            self.tokenizer = TapasTokenizer.from_pretrained(model_name)
            self.model = TapasForQuestionAnswering.from_pretrained(model_name)
            self.model.eval()
            if torch.cuda.is_available():
                self.model = self.model.cuda()
        except Exception as e:
            logger.error(f"模型加载失败: {str(e)}")
            raise

    def clean_value(self, value: str) -> float:
        """清理并转换数值"""
        try:
            # 移除非数字字符，保留小数点
            cleaned = re.sub(r'[^\d.]', '', str(value))
            return float(cleaned) if cleaned else 0.0
        except:
            return 0.0

    def find_matching_cells(self, df: pd.DataFrame, keywords: List[str]) -> List[Dict]:
        """在表格中查找匹配的单元格"""
        matches = []

        # 转换所有数据为字符串
        df = df.astype(str)

        # 检查列名和单元格内容
        for i, row in df.iterrows():
            for j, col in enumerate(df.columns):
                col_str = str(col).strip()
                cell_str = str(row[col]).strip()

                # 检查是否包含关键词
                for keyword in keywords:
                    if keyword in col_str or keyword in cell_str:
                        value = None
                        # 尝试在相邻单元格中找到数值
                        for di in [-1, 0, 1]:
                            for dj in [-1, 0, 1]:
                                try:
                                    adj_val = df.iloc[i + di, j + dj]
                                    cleaned_val = self.clean_value(adj_val)
                                    if cleaned_val > 0:
                                        value = cleaned_val
                                        break
                                except:
                                    continue
                            if value:
                                break

                        if value:
                            matches.append({
                                'value': value,
                                'row': i,
                                'col': j,
                                'context': f"{col_str}: {cell_str}"
                            })

        return matches

    def extract_indicators(self, excel_path: str) -> Dict[str, Dict]:
        """提取所有预算指标"""
        results = {indicator: [] for indicator in self.indicators.keys()}

        try:
            xl = pd.ExcelFile(excel_path)

            for sheet_name in xl.sheet_names:
                try:
                    df = pd.read_excel(excel_path, sheet_name=sheet_name)
                    if df.empty:
                        continue

                    # 查找每个指标
                    for indicator, keywords in self.indicators.items():
                        matches = self.find_matching_cells(df, keywords)
                        if matches:
                            for match in matches:
                                results[indicator].append({
                                    'value': match['value'],
                                    'sheet': sheet_name,
                                    'context': match['context']
                                })

                except Exception as e:
                    logger.warning(f"处理工作表 '{sheet_name}' 时出错: {str(e)}")
                    continue

        except Exception as e:
            logger.error(f"处理Excel文件时出错: {str(e)}")

        return results

    def format_results(self, results: Dict[str, List]) -> Dict[str, Union[float, str]]:
        """格式化结果"""
        formatted = {}
        for indicator, matches in results.items():
            if not matches:
                formatted[indicator] = {'value': None, 'source': '未找到'}
                continue

            # 根据数值大小和上下文选择最可能的匹配
            best_match = max(matches, key=lambda x: x['value'])
            formatted[indicator] = {
                'value': best_match['value'],
                'source': f"工作表: {best_match['sheet']}, {best_match['context']}"
            }

        return formatted


def main():
    try:
        excel_file = r"E:\python_project\Budget_IE\data\福建\泉州\2022泉州决算报表.xlsx"
        extractor = BudgetIndicatorExtractor()

        # 提取所有指标
        results = extractor.extract_indicators(excel_file)
        formatted_results = extractor.format_results(results)

        # 输出结果
        logger.info("\n2022年预算指标数据：")
        for indicator, data in formatted_results.items():
            if data['value']:
                logger.info(f"{indicator}: {data['value']:,.2f}")
                logger.debug(f"来源: {data['source']}")
            else:
                logger.warning(f"{indicator}: 未找到数据")

    except Exception as e:
        logger.error(f"程序执行失败: {str(e)}")


if __name__ == "__main__":
    main()