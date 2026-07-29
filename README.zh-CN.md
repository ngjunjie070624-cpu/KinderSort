# KinderSort — 幼儿园学生照片整理工具

[![平台](https://img.shields.io/badge/平台-Windows-0078D6?logo=windows&logoColor=white)](https://github.com/lerlerchan/KinderSort/releases)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![无需 GPU](https://img.shields.io/badge/GPU-不需要-orange)](https://github.com/lerlerchan/KinderSort)
[![最新版本](https://img.shields.io/github/v/release/lerlerchan/KinderSort?color=blue&logo=github)](https://github.com/lerlerchan/KinderSort/releases)

[English](README.md)

KinderSort 是一个面向幼儿园老师的桌面工具。它会扫描活动照片,将检测到的人脸与参考照片文件夹比对,并自动把照片复制到对应学生的文件夹——无需任何编程知识。

---

## 1. 项目简介

手动整理成百上千张活动照片、辨认每张照片里有哪些学生非常耗时且容易出错。KinderSort 通过本地、纯 CPU 运行的人脸检测与识别流程自动完成这项工作,并配有简单的图形界面,老师只需双击一个文件即可运行。

---

## 2. 功能亮点

| 功能 | 说明 |
|---|---|
| 自动整理 | 检测并识别学生人脸,将匹配的照片复制到对应学生文件夹 |
| 支持合照 | 一张照片会被复制到照片中出现的每一位学生的文件夹 |
| 仅使用 CPU | 无需显卡即可在普通 Windows 电脑上运行 |
| 现代化界面 | CustomTkinter 界面,支持浅色/深色模式,Windows 11 风格卡片 |
| 安全操作 | 照片只会**复制**,不会移动或删除——原始文件始终安全 |
| 实时性能面板 | 整理过程中实时显示 CPU、内存、耗时与处理速度(基于 `psutil`) |
| 操作日志 | 输出目录中自动生成详细的 `kindersort_log.txt` |
| 支持取消 | 整理过程中可随时取消,已处理的照片会保留 |

---

## 3. AI 架构

```
 参考照片 ─┐
           ├─▶ 人脸检测(InsightFace SCRFD,可选 YOLOv8)─▶ 人脸框
 活动照片 ─┘
                          │
                          ▼
              人脸识别(InsightFace ArcFace, buffalo_l)
                          │
                  512 维归一化特征向量
                          │
                          ▼
        与每位学生的参考特征向量计算余弦距离——
        在阈值范围内距离最近、且与次近结果拉开明显差距的学生获胜
                          │
                          ▼
        匹配成功 → 复制到 Output/<学生姓名>/(合照可复制到多个文件夹)
        未检测到人脸 / 无匹配 → 复制到 Output/_unmatched/
```

**检测:** `face_detector.py` 主要使用 InsightFace 的 SCRFD 检测器(CPU、ONNX Runtime 后端)。代码中保留了可选的 YOLOv8 人脸检测路径——如果配置的权重文件不存在,或不是人脸检测模型,程序会自动回退到 SCRFD,默认配置下无需手动干预。

**识别:** `face_recognizer.py` 使用 InsightFace 的 `buffalo_l` ArcFace 模型,为每张检测到的人脸生成 512 维、L2 归一化的特征向量。匹配逻辑(`sorter.py`)将每个特征向量与每位学生存储的参考特征向量计算余弦距离,选择阈值内距离最近的学生,并拒绝两位学生距离过于接近(模糊匹配)的情况。

---

## 4. 技术栈

| 组件 | 库 |
|---|---|
| 人脸检测 | InsightFace SCRFD(默认)/ Ultralytics YOLOv8(可选) |
| 人脸识别 | InsightFace ArcFace(`buffalo_l`),通过 ONNX Runtime(CPU)运行 |
| 图像处理 | OpenCV、Pillow |
| 图形界面 | CustomTkinter |
| 资源监控 | psutil |
| 打包工具 | PyInstaller |
| 开发语言 | Python 3.10+ |

---

## 5. 安装指南

```bash
git clone https://github.com/lerlerchan/KinderSort.git
cd KinderSort
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

> **首次运行需要联网。** InsightFace 会在程序第一次运行时,将 `buffalo_l` 模型(约 300MB)下载到 `~/.insightface/models`。下载完成后,后续整理操作即可完全离线运行。此说明是对早期文档中"从第一次启动就完全离线"这一表述的修正。

---

## 6. 环境要求

- Windows 10/11(源码版本也可在 Ubuntu 上开发运行)
- Python 3.10+(仅源码运行需要,打包后的 `.exe` 不需要)
- 无需显卡——仅使用 CPU
- 约 2GB 可用磁盘空间(模型权重 + 依赖库)
- 首次运行需要联网以下载模型(见上文)

具体依赖版本见 [`requirements.txt`](requirements.txt)。

---

## 7. 运行方法

**源码运行:**
```bash
python main.py
```

**打包后使用(老师):**
1. 从 [Releases](https://github.com/lerlerchan/KinderSort/releases) 页面下载 `KinderSort.exe`
2. 双击运行 `KinderSort.exe`
3. 选择参考照片、活动照片、输出三个文件夹
4. 点击 **Start Sorting**
5. 查看完成摘要并打开输出目录

完整图文手册见:[`guidebook.md`](guidebook.md)

**自行打包 `.exe`:**
```bash
pip install pyinstaller
pyinstaller KinderSort.spec
# 输出:dist/KinderSort.exe
```

---

## 8. 目录结构

```
kindersort/
├── main.py              ← 图形界面入口(CustomTkinter)
├── sorter.py             ← PhotoSorter:参考加载 + 整理流程
├── face_detector.py      ← 人脸检测(SCRFD / 可选 YOLOv8)
├── face_recognizer.py    ← 人脸特征提取 + 余弦距离匹配
├── utils.py               ← 文件处理、命名、日志设置
├── perf_monitor.py        ← 基于 psutil 的 CPU/内存监控(供界面性能面板使用)
├── requirements.txt       ← 固定版本依赖
├── KinderSort.spec        ← PyInstaller 打包配置
├── README.md               ← 英文说明
├── README.zh-CN.md         ← 本文件
├── guidebook.md             ← 面向老师的图文使用手册
└── dist/
    └── KinderSort.exe        ← 打包输出(打包后生成)
```

---

## 9. 界面截图

*(占位——由于界面自上次截图后已更新,提交前请使用 `quick_screenshots.py` 针对当前界面重新生成截图。)*

---

## 10. 性能总结

通过内置的"System Performance"面板(基于 `psutil`)测得,纯 CPU 运行、无需显卡:

| 指标 | 参考数值* |
|---|---|
| 整理时 CPU 占用 | 约单核 15%–25%(视图片大小/数量而定) |
| 峰值内存 | 约 250–300 MB |
| 处理速度 | 每张约 0.3–1.5 秒,视分辨率与人脸数量而定 |

\* *以上数据来自开发测试,仅供参考,并非性能保证——实际数值取决于老师所用电脑的硬件配置和照片分辨率。可在完成摘要的"Performance"部分查看目标机器上的真实数据。*

---

## 11. 未来改进方向

- 将 InsightFace `buffalo_l` 模型权重打包进 PyInstaller 生成的 `.exe`,使首次运行也能完全离线(目前仍需联网一次以下载模型)
- 针对参考照片增加多尺度二次检测,减少合照式参考照片中漏检的人脸
- 在界面中直接引导/强制每位学生提供多张参考照片(目前仅通过文档说明支持 `Reference/学生姓名/*.jpg` 子文件夹方式)
- 在文本日志之外,增加匹配结果的 CSV/Excel 导出
- 为 `sorter.py` 的匹配逻辑补充基础自动化测试(目前依赖人工验证)

---

## 12. 许可协议

本仓库目前未包含许可证文件。如计划公开发布供他人使用,请在发布前添加 `LICENSE` 文件(例如 MIT 协议);在此之前,默认版权保留所有权利。

---

## 开发者本地运行(源码)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```
