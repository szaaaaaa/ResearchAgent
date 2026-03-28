"""用于 CIFAR-10 分类的默认 CNN 模型。"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class SimpleCNN(nn.Module):
    """适用于 CIFAR-10（32x32x3 图像）的简单三层 CNN。"""

    def __init__(self, num_classes: int = 10) -> None:
        super().__init__()
        self.conv1 = nn.Conv2d(3, 32, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm2d(32)
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm2d(64)
        self.conv3 = nn.Conv2d(64, 128, kernel_size=3, padding=1)
        self.bn3 = nn.BatchNorm2d(128)
        self.pool = nn.MaxPool2d(2, 2)
        self.fc1 = nn.Linear(128 * 4 * 4, 256)
        self.fc2 = nn.Linear(256, num_classes)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.pool(F.relu(self.bn1(self.conv1(x))))  # 32x32 -> 16x16 特征图下采样
        x = self.pool(F.relu(self.bn2(self.conv2(x))))  # 16x16 -> 8x8 特征图下采样
        x = self.pool(F.relu(self.bn3(self.conv3(x))))  # 8x8 -> 4x4 特征图下采样
        x = x.view(x.size(0), -1)
        x = F.relu(self.fc1(x))
        x = self.fc2(x)
        return x


def build_model(hparams: dict) -> nn.Module:
    """根据超参数构建并返回模型。"""
    num_classes = hparams.get("num_classes", 10)
    return SimpleCNN(num_classes=num_classes)
