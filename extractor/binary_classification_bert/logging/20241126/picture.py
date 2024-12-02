import matplotlib.pyplot as plt

# 数据：从控制台输出中提取的各个指标
scalar_data = {
    'Precision': {
        'steps': [1, 2, 3, 4, 5],
        'values': [0.9826, 0.9920, 0.9922, 0.9853, 0.9853],
    },
    'Recall': {
        'steps': [1, 2, 3, 4, 5],
        'values': [0.7958, 0.7873, 0.8127, 0.8540, 0.8508],
    },
    'F1-Score': {
        'steps': [1, 2, 3, 4, 5],
        'values': [0.8794, 0.8779, 0.8935, 0.9150, 0.9131],
    },
    'Accuracy': {
        'steps': [1, 2, 3, 4, 5],
        'values': [0.8450, 0.8353, 0.8544, 0.8807, 0.8783],
    }
}

# 绘制 Precision, Recall, F1-Score, Accuracy 四个指标在同一张图上
plt.figure(figsize=(10, 6))

# 绘制每个指标的曲线
plt.plot(scalar_data['Precision']['steps'], scalar_data['Precision']['values'], label='Precision', color='blue', marker='o')
plt.plot(scalar_data['Recall']['steps'], scalar_data['Recall']['values'], label='Recall', color='green', marker='o')
plt.plot(scalar_data['F1-Score']['steps'], scalar_data['F1-Score']['values'], label='F1-Score', color='orange', marker='o')
plt.plot(scalar_data['Accuracy']['steps'], scalar_data['Accuracy']['values'], label='Accuracy', color='red', marker='o')

# 添加标题和标签
plt.title('Precision, Recall, F1-Score, Accuracy over Epochs')
plt.xlabel('Epochs')
plt.ylabel('Score')

# 添加图例
plt.legend()

# 显示网格
plt.grid(True)

# 显示图表
plt.show()
