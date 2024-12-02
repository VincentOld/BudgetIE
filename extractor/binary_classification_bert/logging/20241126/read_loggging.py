import tensorflow as tf
import matplotlib.pyplot as plt
import numpy as np
import os
from tensorboard.backend.event_processing import event_accumulator
from PIL import Image
from io import BytesIO

# 设置.tfevents文件的路径
log_dir = r"E:\python_project\Budget_IE\extractor\binary_classification_bert\logging\20241126"

# 使用EventAccumulator读取tfevents文件
ea = event_accumulator.EventAccumulator(log_dir)
ea.Reload()  # 加载数据

# 获取所有的标量事件标签
scalar_tags = ea.Tags()['scalars']
print(f"Available scalar tags: {scalar_tags}")

# 获取所有图像事件标签（如果有的话）
image_tags = ea.Tags().get('images', [])
print(f"Available image tags: {image_tags}")

# 1. 获取所有标量数据并打印
for tag in scalar_tags:
    print(f"Tag: {tag}")
    events = ea.Scalars(tag)  # 获取与该标签相关的所有标量事件
    steps = []
    values = []
    for event in events:
        steps.append(event.step)
        values.append(event.value)
    print(f"Steps: {steps}")
    print(f"Values: {values}")

    # 可选：绘制标量数据（如损失、准确度等）
    plt.plot(steps, values, label=tag)

# 绘制所有标量图（如损失、准确度等）
plt.xlabel('Step')
plt.ylabel('Value')
plt.title('Scalar Data Over Time')
plt.legend()
plt.show()

# 2. 如果有图像数据，显示它们
for tag in image_tags:
    print(f"Tag: {tag}")
    images = ea.Images(tag)  # 获取与该标签相关的所有图像事件
    for i, image_event in enumerate(images):
        # 将图像数据从字节流转换为PIL Image
        image_data = image_event.encoded_image_string
        image = Image.open(BytesIO(image_data))
        plt.imshow(image)
        plt.title(f"Image {i} for tag {tag}")
        plt.axis('off')  # 关闭坐标轴
        plt.show()

# 3. 获取所有音频事件标签（如果有的话）
audio_tags = ea.Tags().get('audio', [])
print(f"Available audio tags: {audio_tags}")

# 如果有音频数据，可以进一步处理
# 这里暂时不进行音频的提取和显示，但可以根据需要实现。
