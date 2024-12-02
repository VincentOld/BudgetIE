# -*- coding: utf-8 -*-
"""
@Time ： 2024/11/26 17:06
@Auth ： vincent
@File ：BudgetSentence_cls.py
@IDE ：PyCharm
"""
import torch
from transformers import BertTokenizer, BertForSequenceClassification
from config import Config
import warnings

warnings.filterwarnings("ignore")

# 全局初始化
tokenizer = BertTokenizer.from_pretrained(Config.tokenizer_path, local_files_only=True)
model = BertForSequenceClassification.from_pretrained(Config.tokenizer_path, num_labels=2)
model.load_state_dict(torch.load(Config.model_path))
model.eval()
model = model.float()
device = torch.device('cpu')
model.to(device)


def batch_predict(sentences, batch_size=32):
    global model, tokenizer
    predictions = []
    for i in range(0, len(sentences), batch_size):
        batch = sentences[i:i + batch_size]
        inputs = tokenizer.batch_encode_plus(
            batch,
            padding=True,
            truncation=True,
            max_length=256,
            return_tensors='pt'
        )
        with torch.no_grad(), torch.inference_mode():
            input_ids = inputs['input_ids'].to(device)
            attention_mask = inputs['attention_mask'].to(device)
            token_type_ids = inputs['token_type_ids'].to(device)

            outputs = model(input_ids, token_type_ids=token_type_ids, attention_mask=attention_mask)
            probs = torch.softmax(outputs[0], dim=1)
            preds = torch.argmax(probs, dim=1).tolist()
            predictions.extend(preds)
    return predictions


def batch_sentence_cls(dir_info_list, batch_size=48):
    predictions = batch_predict(dir_info_list, batch_size)
    return [sent for sent, pred in zip(dir_info_list, predictions) if pred == 1]
    del model
    del tokenizer
    import gc
    gc.collect()

# 示例调用
if __name__ == "__main__":
    sentence = "全市政府性基金预算支出安排207.99亿元"
    # 调用预测函数
    prediction = batch_predict(sentence)[0]
    print(type(prediction))
    print(f"预测结果: {prediction}")
