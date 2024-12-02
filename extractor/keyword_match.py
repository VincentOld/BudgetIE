import re
from collections import defaultdict
from config import Config
from parser.folder_read import read_folder


def keyword_match(row):
    """
    执行关键词匹配，返回带有置信度的匹配结果字典

    Args:
        row (int): 行号

    Returns:
        dict: 格式如 {'指标1': {'value': '金额1', 'confidence': 分数1}, ...}
    """

    def calculate_confidence(text_B, keyword, prefix, value, has_year, distance):
        """计算匹配的置信度得分（0-100分制）"""
        base_score = 75
        year_score = 10 if has_year else 0
        keyword_exact = 5 if keyword in text_B else 0
        prefix_score = 5 if prefix and prefix in text_B else 0
        distance_penalty = min(10, (distance / 50) * 10)

        try:
            num_value = float(re.search(r'\d+\.?\d*', value).group())
            value_score = 5 if 0 < num_value < 10000 else 0
        except:
            value_score = 0

        final_score = base_score + year_score + keyword_exact + prefix_score + value_score - distance_penalty
        return min(100, max(60, round(final_score, 1)))

    try:
        # 获取数据
        list_A = Config.RESULT_LIST[row - 1]
        list_B = read_folder(row)
        result_dict = {}
        previous_tag = ''

        # 处理每个指标
        for item_A in list_A:
            # 提取年份和关键词
            year_idx = item_A.find('年')
            if year_idx != -1:
                keyword = item_A[year_idx + 1:]
                prefix = item_A[:year_idx - 4]
            else:
                keyword = item_A
                prefix = ''

            candidates = []
            # 在文本中查找匹配
            for text_B in list_B:
                if keyword not in text_B or prefix not in text_B:
                    continue
                try:
                    start = text_B.find(keyword) + len(keyword)
                    text_after = text_B[start:]
                    value_match = re.search(Config.amount_pattern, text_after)
                    if value_match:
                        value = value_match.group()
                        num = float(re.search(r'\d+\.?\d*', value).group())
                        has_year = '2022' in text_B
                        distance = len(text_after[:value_match.start()])
                        confidence = calculate_confidence(
                            text_B, keyword, prefix, value,
                            has_year, distance
                        )
                        candidates.append((value, num, has_year, confidence))
                except:
                    continue

            # 选择最佳匹配
            if candidates:
                year_matches = [c for c in candidates if c[2]]
                best_match = max(year_matches if year_matches else candidates,
                                 key=lambda x: (x[3], x[1]))

                result_dict[item_A] = {
                    'value': best_match[0],
                    'confidence': best_match[3]
                }
            else:
                result_dict[item_A] = {
                    'value': '',
                    'confidence': 0
                }

            # 处理标签
            if '本市' in item_A or '本州' in item_A or '本级' in item_A:
                previous_tag = item_A.split()[0]
            elif previous_tag and result_dict[item_A]['value']:
                result_dict[item_A]['value'] = previous_tag + result_dict[item_A]['value']

        # 过滤掉空值结果
        return {k: v for k, v in result_dict.items() if v['value']}

    except Exception as e:
        print(f"Error in keyword_match: {str(e)}")
        return {}


if __name__ == '__main__':
    # 测试代码
    test_row = 1  # 测试第一行
    result = keyword_match(test_row)
    print(result)