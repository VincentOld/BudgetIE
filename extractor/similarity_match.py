import torch
from transformers import BertTokenizer, BertModel
import spacy
import re
from sklearn.metrics.pairwise import cosine_similarity
from config import Config

# 加载中文BERT模型和tokenizer
tokenizer = BertTokenizer.from_pretrained(Config.pretrained_model_name_or_path)
bert_model = BertModel.from_pretrained(Config.pretrained_model_name_or_path)
indicators = Config.indicators
amount_pattern = re.compile(Config.amount_pattern)


def extract_amount(text):
    return amount_pattern.findall(text)[0]


def extract_noun_phrases(text):
    """
    使用spacy提取文本中的名词短语，同时将特定词汇作为名词处理
    """
    nlp = spacy.load("zh_core_web_sm")
    doc = nlp(text)
    for token in doc:
        if token.text in Config.custom_nouns:
            token.tag_ = "NN"
    return [chunk.text for chunk in doc.noun_chunks]


def get_bert_embedding(text):
    """
    使用BERT模型获取文本的嵌入
    """
    inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=512)
    with torch.no_grad():
        outputs = bert_model(**inputs)
    # 获取[CLS]标记的嵌入（即文本的表示）
    return outputs.last_hidden_state[:, 0, :].squeeze().cpu().numpy()


def get_most_similar_indicator(text, indicators):
    """
    找到与文本中名词短语最相似的指标
    """
    # 计算文本和所有指标的BERT嵌入
    text_embedding = get_bert_embedding(text).reshape(1, -1)
    indicator_embeddings = [get_bert_embedding(indicator) for indicator in indicators]

    # 计算余弦相似度
    similarities = cosine_similarity(text_embedding, indicator_embeddings)
    most_similar_idx = similarities.argmax()
    return indicators[most_similar_idx]


def similarity_match(text, indicators=Config.indicators):
    """
    提取文本中的指标及其对应的金额
    """
    noun_phrases = extract_noun_phrases(text)
    results = {}

    for phrase in noun_phrases:
        # 获取与当前名词短语最相似的指标
        similar_indicator = get_most_similar_indicator(phrase, indicators)
        amount = extract_amount(text)
        if amount:
            results[similar_indicator] = amount
    return results


# 示例文本
text = "2022年，全市政府性基金预算支出安排207.99亿元，加上上解上级支出4.95亿元，调出资金20.74亿元，专项债务还本支出22.01亿元，政府性基金预算支出安排数总计255.69亿元。"

# 提取指标和金额
# result = extract_indicators_and_amounts(text, indicators)
# print(result)
