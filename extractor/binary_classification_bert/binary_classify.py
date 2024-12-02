# -*- coding: utf-8 -*-
"""
@Time ： 2024/11/18 12:26
@Auth ： vincent
@File ：binary_classify.py
@IDE ：PyCharm
"""
import os
import pandas as pd
import numpy as np
import torch
from torch import nn
from tqdm import tqdm
from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix
from sklearn.utils import class_weight
from sklearn.model_selection import train_test_split
from torch.utils.data import TensorDataset, DataLoader, RandomSampler, SequentialSampler
from transformers import BertTokenizer, BertModel, AdamW, get_linear_schedule_with_warmup
from imblearn.over_sampling import RandomOverSampler
from torch.utils.tensorboard import SummaryWriter
from datetime import datetime
from config import Config

pretrained_model_name_or_path = Config.pretrained_model_name_or_path


class ClassifyModel(nn.Module):
    def __init__(self, pretrained_model_name_or_path, num_labels, freeze_bert_layers=8):
        super(ClassifyModel, self).__init__()
        self.bert = BertModel.from_pretrained(pretrained_model_name_or_path)
        self.dropout = nn.Dropout(0.1)
        self.classifier = nn.Linear(self.bert.config.hidden_size, num_labels)

        # 冻结 BERT 的前 freeze_bert_layers 层
        for name, param in self.bert.named_parameters():
            if name.startswith('encoder.layer'):
                layer_num = int(name.split('.')[2])
                if layer_num < freeze_bert_layers:
                    param.requires_grad = False
            else:
                param.requires_grad = True  # 训练池化层和嵌入层

    def forward(self, input_ids, attention_mask, token_type_ids):
        # 前向传播函数，返回分类 logits
        outputs = self.bert(input_ids=input_ids,
                            attention_mask=attention_mask,
                            token_type_ids=token_type_ids)
        pooled_output = outputs[1]  # 池化的输出
        pooled_output = self.dropout(pooled_output)
        logits = self.classifier(pooled_output)
        return logits


class DataProcessForSingleSentence:
    def __init__(self, tokenizer, max_seq_len=128):
        # 初始化，设置分词器和最大序列长度
        self.tokenizer = tokenizer
        self.max_seq_len = max_seq_len

    def get_input(self, dataset):
        # 将数据集转换为模型输入格式
        sentences = dataset.iloc[:, 1].tolist()
        labels = dataset.iloc[:, 2].tolist()

        inputs = self.tokenizer(
            sentences,
            padding='max_length',
            truncation=True,
            max_length=self.max_seq_len,
            return_tensors='pt'
        )
        input_ids = inputs['input_ids']
        attention_mask = inputs['attention_mask']
        token_type_ids = inputs['token_type_ids']
        labels = torch.tensor(labels, dtype=torch.long)

        return TensorDataset(input_ids, attention_mask, token_type_ids, labels)


def load_data(filepath, pretrained_model_name_or_path, max_seq_len, batch_size):
    # 加载数据集，并进行预处理
    io = pd.io.excel.ExcelFile(filepath)
    raw_train_data = pd.read_excel(io, sheet_name='train')
    raw_test_data = pd.read_excel(io, sheet_name='test')
    io.close()

    # 划分训练集和验证集
    train_data_df, val_data_df = train_test_split(raw_train_data, test_size=0.1, random_state=42)

    tokenizer = BertTokenizer.from_pretrained(pretrained_model_name_or_path)
    processor = DataProcessForSingleSentence(tokenizer=tokenizer, max_seq_len=max_seq_len)

    train_data = processor.get_input(train_data_df)
    val_data = processor.get_input(val_data_df)
    test_data = processor.get_input(raw_test_data)

    # 对训练数据进行过采样
    def oversample_data(train_data):
        # 过采样少数类，平衡数据集
        input_ids = train_data.tensors[0]
        attention_mask = train_data.tensors[1]
        token_type_ids = train_data.tensors[2]
        labels = train_data.tensors[3]

        # 将数据展开为二维数组
        X = input_ids.view(input_ids.size(0), -1).numpy()
        y = labels.numpy()

        ros = RandomOverSampler(random_state=42)
        X_resampled, y_resampled = ros.fit_resample(X, y)

        # 将数据重新转换为张量
        input_ids_resampled = torch.tensor(X_resampled).view(-1, input_ids.size(1)).long()
        labels_resampled = torch.tensor(y_resampled).long()

        # 对 attention_mask 和 token_type_ids 进行过采样
        attention_mask_resampled = attention_mask[ros.sample_indices_]
        token_type_ids_resampled = token_type_ids[ros.sample_indices_]

        return TensorDataset(input_ids_resampled, attention_mask_resampled, token_type_ids_resampled, labels_resampled)

    train_data = oversample_data(train_data)

    train_sampler = RandomSampler(train_data)
    val_sampler = SequentialSampler(val_data)
    test_sampler = SequentialSampler(test_data)

    train_iter = DataLoader(dataset=train_data, sampler=train_sampler, batch_size=batch_size)
    val_iter = DataLoader(dataset=val_data, sampler=val_sampler, batch_size=batch_size)
    test_iter = DataLoader(dataset=test_data, sampler=test_sampler, batch_size=batch_size)

    return train_iter, val_iter, test_iter, train_data_df, val_data_df


class FocalLoss(nn.Module):
    def __init__(self, alpha=None, gamma=2, reduction='mean'):
        # 初始化 Focal Loss，alpha 为类别权重，gamma 为调节参数
        super(FocalLoss, self).__init__()
        self.alpha = alpha  # 类别权重
        self.gamma = gamma
        self.reduction = reduction

    def forward(self, inputs, targets):
        # 计算 Focal Loss
        ce_loss = nn.functional.cross_entropy(inputs, targets, reduction='none', weight=self.alpha)
        pt = torch.exp(-ce_loss)
        focal_loss = ((1 - pt) ** self.gamma) * ce_loss

        if self.reduction == 'mean':
            return torch.mean(focal_loss)
        elif self.reduction == 'sum':
            return torch.sum(focal_loss)
        else:
            return focal_loss


def evaluate(model, data_iter, device, phase='Validation'):
    # 模型评估函数，计算各项指标
    model.eval()
    prediction_labels, true_labels = [], []
    prediction_probs = []

    with torch.no_grad():
        for batch in tqdm(data_iter, desc=f'评估 {phase}'):
            batch = tuple(t.to(device) for t in batch)
            input_ids, attention_mask, token_type_ids, labels = batch
            outputs = model(input_ids, attention_mask, token_type_ids)
            probs = nn.functional.softmax(outputs, dim=1)
            predictions = outputs.argmax(dim=1)
            prediction_labels.extend(predictions.cpu().numpy())
            true_labels.extend(labels.cpu().numpy())
            prediction_probs.extend(probs.cpu().numpy())

    report = classification_report(true_labels, prediction_labels, digits=4)
    roc_auc = roc_auc_score(true_labels, np.array(prediction_probs)[:, 1])
    cm = confusion_matrix(true_labels, prediction_labels)

    return report, roc_auc, cm


def train(model, train_iter, val_iter, loss_func, optimizer, scheduler, device, epochs, writer, patience, model_dir):
    # 模型训练函数，包含早停机制
    best_val_loss = float('inf')
    best_epoch = 0
    patience_counter = 0
    best_model_state = None

    for epoch in range(epochs):
        model.train()
        total_loss = 0
        total_correct = 0
        total_samples = 0

        for step, batch in enumerate(tqdm(train_iter, desc=f'训练 Epoch {epoch + 1}/{epochs}')):
            batch = tuple(t.to(device) for t in batch)
            input_ids, attention_mask, token_type_ids, labels = batch

            optimizer.zero_grad()
            outputs = model(input_ids, attention_mask, token_type_ids)
            loss = loss_func(outputs, labels)
            loss.backward()
            optimizer.step()
            scheduler.step()

            total_loss += loss.item() * input_ids.size(0)
            predictions = outputs.argmax(dim=1)
            total_correct += (predictions == labels).sum().item()
            total_samples += input_ids.size(0)

            # 日志记录
            if step % 10 == 0:
                writer.add_scalar('Train/Loss', loss.item(), epoch * len(train_iter) + step)

        avg_loss = total_loss / total_samples
        avg_acc = total_correct / total_samples
        print(f'Epoch {epoch + 1}/{epochs} - 训练损失: {avg_loss:.4f}, 训练准确率: {avg_acc:.4f}')

        # 在验证集上评估
        val_report, val_roc_auc, val_cm = evaluate(model, val_iter, device, phase='验证集')
        print(f'验证集 ROC-AUC: {val_roc_auc:.4f}')
        print(val_report)
        print(f'混淆矩阵:\n{val_cm}')

        # 日志记录
        writer.add_scalar('Validation/ROC-AUC', val_roc_auc, epoch)
        writer.add_text('Validation/Classification_Report', val_report, epoch)
        writer.add_scalar('Validation/Loss', avg_loss, epoch)

        # 早停机制
        val_loss = avg_loss  # 可以根据需要选择验证集上的指标，如损失或ROC-AUC
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_epoch = epoch
            patience_counter = 0
            best_model_state = model.state_dict()
            # 保存最佳模型
            model_save_path = os.path.join(model_dir, 'best_model.bin')
            torch.save(best_model_state, model_save_path)
            print(f'保存最佳模型于 Epoch {epoch + 1}')
        else:
            patience_counter += 1
            if patience_counter >= patience:
                print(f'早停于 Epoch {epoch + 1}')
                break

    # 加载最佳模型
    model.load_state_dict(torch.load(os.path.join(model_dir, 'best_model.bin')))
    return model


if __name__ == '__main__':
    # 参数设置
    batch_size = 16
    max_seq_len = 256
    epochs = 5
    learning_rate = 2e-5
    freeze_bert_layers = 8  # 冻结 BERT 的前 8 层
    patience = 3  # 早停的耐心值
    # 获取当前日期，格式为 'YYYYMMDD'
    current_date = datetime.now().strftime('%Y%m%d')
    # 设置模型保存目录
    model_dir = '../../model'
    if not os.path.exists(model_dir):
        os.makedirs(model_dir)

    # 设置日志目录
    logging_dir = os.path.join('logging', current_date)
    if not os.path.exists(logging_dir):
        os.makedirs(logging_dir)

    # 设置设备
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    # 初始化 TensorBoard
    writer = SummaryWriter(log_dir=logging_dir)

    # 加载数据
    train_iter, val_iter, test_iter, train_data_df, val_data_df = load_data(Config.budget_dataset_path,
                                                                            pretrained_model_name_or_path, max_seq_len,
                                                                            batch_size)

    # 初始化模型
    model = ClassifyModel(pretrained_model_name_or_path, num_labels=2, freeze_bert_layers=freeze_bert_layers)
    model.to(device)

    # 计算类别权重
    all_labels = train_data_df.iloc[:, 2].tolist()
    class_weights = class_weight.compute_class_weight('balanced', classes=np.unique(all_labels), y=all_labels)
    class_weights = torch.tensor(class_weights, dtype=torch.float).to(device)

    # 定义损失函数
    alpha = class_weights
    loss_func = FocalLoss(alpha=alpha, gamma=2)

    # 定义优化器和学习率调度器
    optimizer = AdamW(filter(lambda p: p.requires_grad, model.parameters()), lr=learning_rate, eps=1e-8)
    total_steps = len(train_iter) * epochs
    scheduler = get_linear_schedule_with_warmup(optimizer, num_warmup_steps=int(0.1 * total_steps),
                                                num_training_steps=total_steps)

    # 训练模型
    trained_model = train(model, train_iter, val_iter, loss_func, optimizer, scheduler, device, epochs, writer,
                          patience, model_dir)

    # 在测试集上评估
    test_report, test_roc_auc, test_cm = evaluate(trained_model, test_iter, device, phase='测试集')
    print(f'测试集 ROC-AUC: {test_roc_auc:.4f}')
    print(test_report)
    print(f'混淆矩阵:\n{test_cm}')

    # 日志记录测试结果
    writer.add_scalar('Test/ROC-AUC', test_roc_auc)
    writer.add_text('Test/Classification_Report', test_report)
    writer.close()

    # 保存最终模型
    final_model_path = os.path.join(model_dir, 'finetuned_budget_bert.bin')
    torch.save(trained_model.state_dict(), final_model_path)
