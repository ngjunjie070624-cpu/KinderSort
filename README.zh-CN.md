# KinderSort — 幼儿园学生照片整理工具

[![Platform](https://img.shields.io/badge/platform-Windows-0078D6?logo=windows&logoColor=white)](https://github.com/lerlerchan/KinderSort/releases)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![CPU Only](https://img.shields.io/badge/GPU-not_required-orange)](https://github.com/lerlerchan/KinderSort)
[![Release](https://img.shields.io/github/v/release/lerlerchan/KinderSort?color=blue&logo=github)](https://github.com/lerlerchan/KinderSort/releases)

[English](README.md)

KinderSort 是一款面向幼儿园教师的桌面应用。它会扫描活动照片，检测并识别人脸，与参考照片文件夹进行比对，并自动将每张照片复制到对应学生的输出文件夹——无需任何编程知识。

---

## 项目概述

手动整理成百上千张活动照片、辨认每张照片里有哪些孩子，既耗时又容易出错。KinderSort 通过本地、**纯 CPU** 运行的人脸检测与识别流程自动完成这项工作，并配有 **CustomTkinter** 图形界面，点击即可操作。

启动时，界面会立即显示，AI 模型在后台加载。就绪后，教师选择三个文件夹（参考照片、活动照片、输出目录），点击 **Start Sorting**，即可查看实时进度和完成摘要。匹配成功的照片复制到各学生文件夹；无法识别或无检测到人脸的照片复制到 `_unmatched/`。原始文件不会被移动或删除。

---

## 功能特性

| 功能 | 说明 |
|---|---|
| 自动人脸检测与整理 | 检测活动照片中的人脸，与参考学生比对，复制到 `Output/<StudentName>/` |
| 支持合照 | 一张照片会复制到所有匹配学生的文件夹 |
| 未匹配处理 | 无人脸、无法提取特征或匹配置信度不足的照片放入 `Output/_unmatched/` |
| 纯 CPU 推理 | 所有模型通过 ONNX Runtime 在 CPU 上运行，无需显卡 |
| CustomTkinter 界面 | Windows 11 风格，支持浅色/深色模式，含进度条、状态面板和运行摘要 |
| 快速启动 | 窗口立即显示；YOLOv8、InsightFace、ONNX Runtime 在后台线程加载 |
| 实时状态面板 | 显示检测到的人脸数、匹配数、未匹配数和已用处理时间 |
| 系统性能面板 | 每次整理运行期间，通过 `psutil` 实时显示 8 项进程级指标（CPU、内存、耗时） |
| 安全文件操作 | 照片仅**复制**，不移动、不删除——原始文件始终保留 |
| 操作日志 | 输出目录自动生成详细日志 `kindersort_log.txt` |
| 支持取消 | 整理过程中可随时取消，已处理的照片会保留 |
| 多张参考照片 | 支持根目录 `StudentName.jpg`，或在 `Reference/StudentName/` 子文件夹中存放多张参考图 |

---

## AI 架构

```
 参考照片 ─┐
           ├─▶ 人脸检测（YOLOv8 可选 → InsightFace SCRFD 回退）─▶ 人脸框
 活动照片 ─┘
                          │
                          ▼
              人脸识别（InsightFace ArcFace，buffalo_l）
                          │
                  512 维 L2 归一化特征向量
                          │
                          ▼
        与每位学生的参考特征向量计算余弦距离——
        距离阈值 0.55 内最近、且与次近结果拉开差距（< 0.02）的学生获胜
                          │
                          ▼
        匹配成功 → 复制到 Output/<StudentName>/（合照可复制到多个文件夹）
        无匹配 / 无人脸 → 复制到 Output/_unmatched/
```

**检测（`face_detector.py`）：** 当权重文件存在且有效时，优先尝试 YOLOv8 人脸模型（`yolov8n-face.pt`）。若权重缺失、无效或不是人脸训练模型，流程自动回退到 **InsightFace SCRFD**（CPU，ONNX Runtime 后端）。两条路径均返回 `(x1, y1, x2, y2)` 格式的人脸框。

**识别（`face_recognizer.py`）：** 使用 InsightFace **`buffalo_l`** 模型包中的 **ArcFace**，为每张检测到的人脸生成 512 维、L2 归一化的特征向量。

**匹配（`sorter.py`）：** 将活动照片中每张人脸的特征向量与所有学生的参考特征计算余弦距离。距离阈值 `0.55` 内最近的匹配被接受；两名学生距离过于接近（差距 `< 0.02`）时视为模糊匹配并拒绝。参考照片中有多张人脸时，取面积最大的人脸作为该学生。

**图像预处理：** 检测前将活动照片和参考照片的长边缩放至最多 1000 像素，在基本不影响准确率的前提下降低 CPU 负载。

---

## 技术栈

[![OpenCV](https://img.shields.io/badge/OpenCV-image_processing-red)](https://opencv.org/)
[![InsightFace](https://img.shields.io/badge/InsightFace-SCRFD_+_ArcFace-blueviolet)](https://github.com/deepinsight/insightface)
[![Ultralytics YOLOv8](https://img.shields.io/badge/YOLOv8-optional_detector-yellow)](https://github.com/ultralytics/ultralytics)
[![ONNX Runtime](https://img.shields.io/badge/ONNX_Runtime-CPU-lightgrey)](https://onnxruntime.ai/)
[![CustomTkinter](https://img.shields.io/badge/CustomTkinter-GUI-1E90FF)](https://github.com/TomSchimansky/CustomTkinter)
[![psutil](https://img.shields.io/badge/psutil-resource_monitoring-green)](https://github.com/giampaolo/psutil)
[![PyInstaller](https://img.shields.io/badge/PyInstaller-packaging-purple)](https://pyinstaller.org/)

| 组件 | 库 / 说明 |
|---|---|
| 人脸检测 | InsightFace SCRFD（默认回退）/ Ultralytics YOLOv8（可选，`yolov8n-face.pt`） |
| 人脸识别 | InsightFace ArcFace（`buffalo_l`），通过 ONNX Runtime（`CPUExecutionProvider`）运行 |
| 图像处理 | OpenCV、Pillow |
| 图形界面 | CustomTkinter |
| 资源监控 | psutil（`perf_monitor.py`） |
| 打包工具 | PyInstaller（`KinderSort.spec`） |
| 开发语言 | Python 3.10+ |

---

## 安装

### 1. Clone the repository

```bash
git clone https://github.com/ngjunjie070624-cpu/KinderSort.git
cd KinderSort
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv .venv
```

Activate the virtual environment:
**Windows**

```bash
.venv\Scripts\activate
```
**macOS / Linux**

```bash
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the application

```bash
python main.py
```
## 下载（Windows 可执行文件）

如果您不想自行安装 Python 环境，可以直接下载已经打包好的 Windows 可执行文件。

步骤：

1. 前往本项目的 **GitHub Releases** 页面。
2. 下载最新版本。
3. （如果下载的是 ZIP）先解压缩。
4. 双击 **KinderSort.exe** 即可运行。

使用已打包的版本时，无需安装 Python 或任何额外依赖。

> **注意：** 第一次启动时，程式可能需要几秒钟初始化 AI 模型，这是正常现象。
> **首次运行需要联网。** InsightFace 会在程序第一次运行时，将 `buffalo_l` 模型（约 300 MB）下载到 `~/.insightface/models`。下载完成后，后续整理操作即可完全离线运行。

---

## 环境要求

- **操作系统：** Windows 10/11（主要目标平台；源码亦可在 Linux 上开发运行）
- **Python：** 3.10+（仅源码运行需要，打包后的 `.exe` 不需要）
- **显卡：** 不需要——纯 CPU 运行
- **磁盘空间：** 约 2 GB 可用空间（模型权重 + 依赖库）
- **网络：** 首次运行需联网下载 InsightFace 模型（见上文）

依赖包版本见 [`requirements.txt`](requirements.txt)：

```
opencv-python, ultralytics, insightface, onnxruntime, numpy, Pillow, psutil, customtkinter
```

---

## 运行方法

**源码运行：**

```bash
python main.py
```

1. 等待状态显示 **"Ready"**（窗口打开后，AI 模型在后台加载）。
2. 选择 **Reference**（参考照片）、**Classroom**（活动照片）、**Output**（输出目录）三个文件夹。
3. 点击 **▶ Start Sorting**。
4. 整理完成后，查看状态面板、系统性能面板和运行摘要。
5. 打开输出目录——匹配成功的照片在 `<StudentName>/` 文件夹；未匹配的照片在 `_unmatched/`。

**打包后使用（教师）：**

1. 从 [Releases](https://github.com/ngjunjie070624-cpu/KinderSort/releases/tag/v1.0.0) 页面下载 `KinderSort.exe`。
2. 双击运行 `KinderSort.exe`。
3. 按上述步骤选择文件夹并开始整理。

完整图文手册：[`guidebook.md`](https://github.com/ngjunjie070624-cpu/KinderSort/blob/main/guidebook.md)

**自行打包 `.exe`：**

```bash
pip install pyinstaller
pyinstaller KinderSort.spec
# 输出：dist/KinderSort.exe
```

---

## 目录结构

**代码仓库：**

```
KinderSort/
├── main.py              ← CustomTkinter 图形界面入口
├── sorter.py             ← PhotoSorter：参考加载 + 整理流程
├── face_detector.py      ← 人脸检测（YOLOv8 / SCRFD 回退）
├── face_recognizer.py    ← ArcFace 特征提取
├── perf_monitor.py       ← 基于 psutil 的 CPU/内存监控
├── utils.py              ← 文件处理、命名、日志设置
├── requirements.txt      ← Python 依赖
├── KinderSort.spec       ← PyInstaller 打包配置
├── guidebook.md          ← 面向教师的使用手册
├── README.md             ← 英文说明
├── README.zh-CN.md       ← 本文件
├── quick_screenshots.py  ← 开发者工具：截取界面截图
├── generate_guide.py     ← 开发者工具：重新生成手册素材
├── docx_export.py        ← 开发者工具：导出 Word 版手册
└── dist/
    └── KinderSort.exe    ← 打包输出（打包后生成）
```

**运行时（教师选择的文件夹，不在代码仓库中）：**

```
Reference/                  Classroom/                Output/
  Ali.jpg                     Sports_Day/               Ali/
  Siti.png                    Concert/                  Siti/
  Kumar/                      Field_Trip/               Kumar/
    Kumar_2.jpg                                         _unmatched/
                                                          kindersort_log.txt
```

- **参考照片文件夹：** 根目录放置单张参考图（如 `Ali.jpg`），和/或在子文件夹中放置多张参考图（如 `Kumar/Kumar_2.jpg`）。
- **活动照片文件夹：** 按活动分子文件夹存放（如 `Sports_Day/`、`Concert/`）。若子文件夹中没有图片，则扫描活动文件夹根目录下的图片。
- **输出文件夹：** 匹配成功的照片复制到各学生文件夹，其余放入 `_unmatched/`。日志文件：`kindersort_log.txt`。

支持的图片格式：`.jpg`、`.jpeg`、`.png`、`.bmp`、`.webp`

---

## 性能监控

KinderSort 在图形界面中提供 **System Performance**（系统性能）面板，由 `perf_monitor.py` 和 **psutil** 驱动。用户点击 **Start Sorting** 后开始监控，以每秒 1 次（1 Hz）的频率采样 KinderSort 进程，直至整理结束。

| 指标 | 说明 |
|---|---|
| Current CPU Usage（当前 CPU 占用） | 最新进程 CPU 份额，归一化为 **0–100%** 整体利用率 |
| Average CPU Usage（平均 CPU 占用） | 本次运行所有采样点的 CPU 平均值 |
| Current Memory Usage（当前内存占用） | 最新常驻内存（RSS），单位 MB |
| Peak Memory Usage（峰值内存占用） | 本次运行观察到的最高 RSS，单位 MB |
| Average Memory Usage（平均内存占用） | 本次运行所有采样点的 RSS 平均值，单位 MB |
| Total Processing Time（总处理时间） | 从点击 Start 到完成的秒数 |
| Average Time per Image（平均每张耗时） | 总时间 ÷ 已处理图片数 |
| Images Processed（已处理图片数） | 整理流程已完成的活动照片数量 |

上述数据同时显示在 **Run Summary**（运行摘要）文本框中，并写入整理完成后的日志摘要部分。

**CPU 归一化：** psutil 报告的进程 CPU 占用是所有逻辑核心的累加值（例如 12 线程 CPU 上可能显示 620%）。KinderSort 会除以逻辑核心数，使面板显示整体 CPU 份额（例如约 52%），与任务管理器的整体 CPU 视图一致。

监控范围**仅限 KinderSort 进程**，不测量整个系统；采样使用非阻塞的 `cpu_percent(interval=None)`，不会阻塞图形界面或后台整理线程。

---

## 低资源优化

KinderSort 面向普通教室笔记本电脑设计，无需独立显卡：

| 优化手段 | 实现方式 |
|---|---|
| 纯 CPU 推理 | 所有 ONNX Runtime 会话使用 `CPUExecutionProvider`；全程 `ctx_id=-1` |
| 图像降采样 | 检测前长边限制为 1000 像素（`sorter.py` 中的 `MAX_IMAGE_DIMENSION`） |
| 懒加载 + 共享模型 | 启动时在后台线程加载一次 AI 权重，后续整理运行复用同一实例 |
| 响应式启动 | 界面立即渲染；重型依赖（InsightFace、YOLOv8、ONNX Runtime）在非主线程加载 |
| 逐张处理 | 活动照片按顺序逐张处理，保持内存占用稳定 |
| 轻量监控 | psutil 以 1 Hz 采样——每次仅两次内核计数器读取，不侵入识别流程 |
| 复制而非移动 | 文件 I/O 使用 `shutil.copy2`；原始文件不会被删除 |

这些设计使内存占用可预测，并使系统性能面板成为展示低资源优化效果的可靠依据，适合课程作业演示。

---

## 界面截图

| 步骤 | 截图 |
|---|---|
| 应用启动（模型加载中） | `guidebook_assets/01_launch.png` |
| 已选择参考照片文件夹 | `guidebook_assets/02_reference_selected.png` |
| 已选择活动照片文件夹 | `guidebook_assets/03_events_selected.png` |
| 三个文件夹均已设置 | `guidebook_assets/04_all_folders_set.png` |
| 整理进行中 | `guidebook_assets/05_sorting_in_progress.png` |
| 整理完成 | `guidebook_assets/06_sorting_complete.png` |

*（占位截图——界面已更新，提交前请使用 `quick_screenshots.py` 针对当前界面重新生成。）*

---

## 未来改进

- 将 InsightFace `buffalo_l` 模型权重打包进 PyInstaller 构建，使首次运行也能完全离线（目前仍需联网一次以下载模型）
- 在界面中引导教师为每位学生添加多张参考照片（代码已支持子文件夹方式）
- 在文本日志之外，增加匹配结果的 CSV/Excel 导出
- 为 `sorter.py` 的匹配逻辑补充自动化测试（目前依赖人工验证）

---

## 许可协议

本仓库目前未包含许可证文件。如计划公开发布供他人复用，请在发布前添加 `LICENSE` 文件（例如 MIT 协议）；在此之前，默认版权保留所有权利。
