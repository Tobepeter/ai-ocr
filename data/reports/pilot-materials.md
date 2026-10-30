# 首批 OCR 物料采集与选样

历史批次；当前运行名单已更新为 [中文优先 60 份](balanced60-materials.md)，本文保留最初 50 份的采集和筛查记录

日期：2026-10-30。已下载 50 份物料，完成文件与标注检查、全部图像缩略图筛查以及 8 份 PDF 首页面渲染检查；未运行 OCR 模型，未逐字人工校对参考答案

## 已采集

| 来源 | 数量 | 选择依据 | 当前用途 |
| --- | ---: | --- | --- |
| OmniDocBench | 30 | 1,651 页候选，30 个文档类型 × 语言组合，每层固定种子选 1 页 | 中英文字、表格、公式、阅读顺序，另含繁体、古籍与手写 |
| FUNSD | 12 | 官方完整包约 16.1 MiB，仅从 50 份测试表单随机选取 | 英文噪声扫描、文字框、实体及关系 |
| olmOCR-bench | 8 | old_scans 的 98 个 PDF 候选，按来源 URL 目录分组后取样 | 旧扫描的文字存在/缺失及顺序断言，部分为历史手稿 |

实际输入共 **27.07 MiB**，连同来源标注、FUNSD 原包、参考答案和 PDF 预览，本地约 **86 MiB**。没有下载整个 OmniDocBench 图片库或完整 olmOCR 文档库

按上游语言标签：英文 29、简体中文 10、中英混排 6、繁体中文 4、其他语言 1。属于多来源试评测池，**没有达到此前中文优先 120+10 的目标配额**，不能把原计划写成已完成

## 本轮拍板

- **6 份开发样本**：omni-003、omni-007、omni-022、funsd-82573104、funsd-86263525、olm-24，先用于验证加载、输出、框坐标和断言接口
- **34 份试评测样本**：作为首轮批量运行池，按来源、语言与能力单列结果，不产生通用总排名
- **8 份挑战样本**：omni-018、omni-019、omni-025、omni-027、olm-44、olm-55、olm-74、olm-84，古籍竖排、中文笔记、混排手写和英文历史手稿，单独看失败模式
- **omni-021**：意大利语封面，保留多语言探索，不混入中英文主表
- **omni-026**：几乎空白的横线笔记页，但有 `NO. Date` 页眉，作为稀疏文字检查，不能算无字负例

该分流是基于输入内容与标注类型作出的选择，未查看任何模型输出。开发样本不参与后续试评测汇总；因部分原始文档和模板归属未知，这批数据不宣称是严格独立的最终留出集

## 已验证与尚未验证

- 50/50 下载完成，SHA256 全部不同，所有图像可解码、8 份 PDF 可解析及渲染
- OmniDocBench 图片尺寸与页面标注一致；参考 JSON 可解析且非空；PDF 断言页码落在合法范围
- OmniDocBench 原标注与官方 LFS SHA256 一致；FUNSD ZIP 的 Git blob SHA1 与官方仓库记录一致，ZIP CRC 检查通过
- 简单 dHash 与长宽比检查未发现近重复候选；这不能证明原文档/模板独立。FUNSD 中相似表格仍可能属于相近模板
- 全部缩略图已人工视觉筛查，但不等于逐字验收。参考保留 `upstream-not-locally-verified`，模型开始前需针对目标指标复核
- OmniDocBench 原始答案含 Markdown/LaTeX，不能直接拼接后与纯文本混算 CER；FUNSD 不预设实体数组顺序是阅读顺序；olmOCR 使用断言通过率，不能冒充完整转录准确率
- OmniDocBench 上游文档归属多数未知，不能把 30 页宣称为 30 份独立文档；olm 的来源目录只是保守聚类线索，完整原始 URL 在参考中保留

## 缺口与后续顺序

当前英文偏多，OmniDocBench 占 60%，没有满足正式方案的单来源占比目标。下一轮优先补独立中文来源与实际软件/网页截图，而不是继续从 OmniDocBench 加页。CTW/ReCTS、中文票据、CASIA 独立书写者和真正无字负例仍待补；现有笔记不能替代跨书写者手写基准

先用 6 份开发样本接通单引擎，再复核将参与评分的标注，运行 34 份试评测及 8 份挑战。公开测试集可能与模型训练/调参重合，当前仅作功能覆盖与初步比较，不为细微差距下普遍结论

## 复现与版本管理

```sh
# 在项目根目录执行：标准库 + curl，恢复固定来源元数据及选中输入
python3 scripts/prepare-materials.py --restore
# 检查：Python Pillow、系统 Poppler 的 pdfinfo/pdftoppm
python3 scripts/audit-materials.py
```

运行环境本轮使用本机 Python、Pillow 与 Poppler，未安装 OCR 依赖或模型。已在现有文件上重跑恢复入口，全部哈希保持一致；未用空目录重新下载全部文件。`--plan` 是初次选样入口，已有计划时拒绝覆盖，日常恢复以冻结计划为准

- [完整物料清单](../manifests/pilot-materials.csv)：50 行，含来源、版本、哈希、标注路径和使用分组
- [冻结采样计划](../manifests/pilot-plan.json)：固定 ID 与抽样规则，不复制原文标注
- [来源包恢复清单](../manifests/pilot-resources.json)：固定 URL、字节数与 SHA256
- [下载记录](../manifests/pilot-downloads.json)、[核验结果](../manifests/pilot-audit.json)
- 原件与参考答案位于 `data/input/pilot-20261030/{case_id}/`，来源元数据位于其 `metadata/`

原图、参考答案和来源包保留本地，正式清单、恢复脚本和本报告可纳入 Git。OmniDocBench 与 FUNSD 官方说明限定研究/非商业用途，不能因为文件小就默认公开再分发；olmOCR-bench 数据卡标 ODC-BY-1.0，原始文档权利仍需保留

官方来源：[OmniDocBench 数据卡](https://huggingface.co/datasets/opendatalab/OmniDocBench/blob/aa1ee96d106dbe53d0ae59474d75c6e6d9b53fec/README.md)、[FUNSD 下载](https://guillaumejaume.github.io/FUNSD/download/)、[FUNSD 使用条件](https://guillaumejaume.github.io/FUNSD/work/)、[olmOCR-bench 数据卡](https://huggingface.co/datasets/allenai/olmOCR-bench/blob/54a96a6fb6a2bd3b297e59869491db4d3625b711/README.md)

## 样本使用表

| case_id | 来源 | 语言 | 用途 |
| --- | --- | --- | --- |
| omni-001 | OmniDocBench | en_ch_mixed | pilot-evaluation |
| omni-002 | OmniDocBench | english | pilot-evaluation |
| omni-003 | OmniDocBench | simplified_chinese | development |
| omni-004 | OmniDocBench | en_ch_mixed | pilot-evaluation |
| omni-005 | OmniDocBench | english | pilot-evaluation |
| omni-006 | OmniDocBench | simplified_chinese | pilot-evaluation |
| omni-007 | OmniDocBench | en_ch_mixed | development |
| omni-008 | OmniDocBench | english | pilot-evaluation |
| omni-009 | OmniDocBench | simplified_chinese | pilot-evaluation |
| omni-010 | OmniDocBench | traditional_chinese | pilot-evaluation |
| omni-011 | OmniDocBench | en_ch_mixed | pilot-evaluation |
| omni-012 | OmniDocBench | english | pilot-evaluation |
| omni-013 | OmniDocBench | simplified_chinese | pilot-evaluation |
| omni-014 | OmniDocBench | en_ch_mixed | pilot-evaluation |
| omni-015 | OmniDocBench | english | pilot-evaluation |
| omni-016 | OmniDocBench | simplified_chinese | pilot-evaluation |
| omni-017 | OmniDocBench | traditional_chinese | pilot-evaluation |
| omni-018 | OmniDocBench | simplified_chinese | challenge |
| omni-019 | OmniDocBench | traditional_chinese | challenge |
| omni-020 | OmniDocBench | english | pilot-evaluation |
| omni-021 | OmniDocBench | other | exploratory |
| omni-022 | OmniDocBench | simplified_chinese | development |
| omni-023 | OmniDocBench | english | pilot-evaluation |
| omni-024 | OmniDocBench | simplified_chinese | pilot-evaluation |
| omni-025 | OmniDocBench | en_ch_mixed | challenge |
| omni-026 | OmniDocBench | english | sparse-text |
| omni-027 | OmniDocBench | simplified_chinese | challenge |
| omni-028 | OmniDocBench | english | pilot-evaluation |
| omni-029 | OmniDocBench | simplified_chinese | pilot-evaluation |
| omni-030 | OmniDocBench | traditional_chinese | pilot-evaluation |
| funsd-86075409_5410 | FUNSD | english | pilot-evaluation |
| funsd-82573104 | FUNSD | english | development |
| funsd-82251504 | FUNSD | english | pilot-evaluation |
| funsd-83573282 | FUNSD | english | pilot-evaluation |
| funsd-86263525 | FUNSD | english | development |
| funsd-82250337_0338 | FUNSD | english | pilot-evaluation |
| funsd-85629964 | FUNSD | english | pilot-evaluation |
| funsd-83641919_1921 | FUNSD | english | pilot-evaluation |
| funsd-86079776_9777 | FUNSD | english | pilot-evaluation |
| funsd-87086073 | FUNSD | english | pilot-evaluation |
| funsd-86328049_8050 | FUNSD | english | pilot-evaluation |
| funsd-82253245_3247 | FUNSD | english | pilot-evaluation |
| olm-84 | olmOCR-bench | english | challenge |
| olm-31 | olmOCR-bench | english | pilot-evaluation |
| olm-44 | olmOCR-bench | english | challenge |
| olm-24 | olmOCR-bench | english | development |
| olm-55 | olmOCR-bench | english | challenge |
| olm-65 | olmOCR-bench | english | pilot-evaluation |
| olm-74 | olmOCR-bench | english | challenge |
| olm-67 | olmOCR-bench | english | pilot-evaluation |
