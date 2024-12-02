import re
from config import Config


def longest_common_substring_length(s1, s2):
    m = len(s1)
    n = len(s2)
    maxlen = 0
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    # 构建动态规划表
    for i in range(m):
        for j in range(n):
            if s1[i] == s2[j]:
                dp[i + 1][j + 1] = dp[i][j] + 1
                if dp[i + 1][j + 1] > maxlen:
                    maxlen = dp[i + 1][j + 1]
    return maxlen


def lcs_match(text, indicators=Config.indicators, min_common_length=4):
    amounts = {}
    amount_confidences = {}  # 新增：存储每个匹配的置信度
    number_pattern = re.compile(Config.amount_pattern)
    amount_matches = list(number_pattern.finditer(text))

    for match in amount_matches:
        amount = match.group()
        amount_start = match.start()
        lookback_window = 20
        start_pos = max(0, amount_start - lookback_window)
        preceding_text = text[start_pos:amount_start]
        best_match = ''
        best_match_score = 0
        for indicator in indicators:
            indicator_length = len(indicator)
            lcs_length = longest_common_substring_length(indicator, preceding_text)
            if lcs_length < min_common_length:
                continue

            match_score = lcs_length / indicator_length

            if match_score > best_match_score:
                best_match = indicator
                best_match_score = match_score
            elif match_score == best_match_score and len(indicator) > len(best_match):
                best_match = indicator

        if best_match:
            # 计算最终置信度得分（0-100分制）
            confidence = calculate_confidence(
                match_score=best_match_score,
                distance=amount_start - start_pos,
                lookback_window=lookback_window
            )

            if best_match not in amounts or confidence > amount_confidences.get(best_match, 0):
                amounts[best_match] = {
                    'value': amount,
                    'confidence': confidence
                }
                amount_confidences[best_match] = confidence

    return amounts


def calculate_confidence(match_score, distance, lookback_window):
    """
    计算置信度得分（0-100分制）

    参数:
        match_score: 最长公共子串匹配得分 (0-1)
        distance: 指标词与数值之间的距离
        lookback_window: 向前查找窗口大小
    """
    # 基础分数：由匹配得分决定（60-80分）
    base_score = 60 + (match_score * 20)
    # 距离惩罚：距离越远，扣除越多分数（最多扣20分）
    distance_penalty = min(20, (distance / lookback_window) * 20)
    # 最终得分
    final_score = base_score - distance_penalty
    return round(final_score, 1)


if __name__ == '__main__':
    text = ("2022年，全市政府性基金支出207.99亿元，加上上解上级支出4.95亿元，全市政府性基金支出217.99亿元，"
            "调出资金20.74亿元，专项债务还本支出22.01亿元，政府性基金预算支出安排数总计255.69亿元。")
    key_amounts = lcs_match(text)
    print(type(key_amounts))
    print(key_amounts)
    #{'政府性基金收入': {'value': '207.99亿元', 'confidence': 55.3}, '专项债务余额': {'value': '22.01亿元', 'confidence': 53.3}}