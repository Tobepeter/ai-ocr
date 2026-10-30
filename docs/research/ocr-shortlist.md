# OCR 重测候选与历史边界

日期：2026-10-30。以下保留选型过程；后续用户扩展为八个候选并授权轻量实测，实际执行与清理状态以[本轮报告](../../data/reports/benchmark-20261030.md)为准

实际决策：先完成RapidOCR、PaddleOCR、Tesseract、EasyOCR、Docling五条CPU路线；GLM-OCR和PaddleOCR-VL因原版权重预算暂缓，MinerU为控制新增运行时范围暂缓。不是五个完全独立模型家族，Docling使用RapidOCR后端

## 历史实际记录

原始依据是 ai-test 项目 sim-dev 的 `docs/welove/product-ui-map.md` 中 2026-05-02 的对比记录，以及 welove-job 的 OCR 配置。历史涉及 RapidOCR、PaddleOCR 和 Tesseract：RapidOCR 对微爱游戏截图最适合并被接入页面状态识别；PaddleOCR 记录为本机可用、输出方式不如 RapidOCR 直接；Tesseract 对彩色截图噪声较多

输入是 Android 彩色游戏截图，输出是文字及状态摘要，不是完整 PDF/表格/公式/手写横评。旧配置对 RapidOCR 有速度和稳定性的定性评价，但缺少可复核的完整版本、样本量、耗时与准确率，所以只能作历史经验

本轮回查来源：旧产品UI记录（本机历史材料，不作为客户复现依赖）；最小历史结论已沉淀于本页，旧交接副本已清理

## 最初建议：六条路线（历史）

| 候选 | 选择理由 | 主要观察 |
| --- | --- | --- |
| [RapidOCR](https://github.com/RapidAI/RapidOCR) | 历史默认、轻量部署代表 | 中文识字、速度、内存和原始坐标 |
| [PaddleOCR / PP-OCR](https://github.com/PaddlePaddle/PaddleOCR) | 中文传统检测识别主线，保留旧工具对照 | 文字检测、识别、旋转和小字；固定具体模型与预处理 |
| [Tesseract](https://github.com/tesseract-ocr/tesseract) | 成熟 CLI 和历史基线 | 规整扫描文字及复杂图像的退化，中文语言包配置 |
| [GLM-OCR](https://github.com/zai-org/GLM-OCR) | 0.9B 文档视觉模型，官方提供多种部署入口 | 表格、公式、复杂页面、漏字和补字 |
| [PaddleOCR-VL](https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/pipeline_usage/PaddleOCR-VL.md) | 与 PP-OCR 不同的文档 VLM 路线 | 和 GLM 比结构还原、中文质量、资源开销 |
| [MinerU](https://github.com/opendatalab/MinerU) | 完整文档解析工具，验证最终 Markdown/JSON 实用性 | 阅读顺序、表格和公式保留、端到端时间 |

这是推荐名单，尚未把“最新版”当作冻结版本。执行前检查本机资源、当前稳定版与可用后端，再记录确切软件版本、模型 revision、量化及运行配置。各项目官方宣称的榜单成绩不替代本次实测

RapidOCR 模型来自 PaddleOCR，不能将二者当作完全独立模型家族；如使用相同模型，应把差异解释为部署后端/预处理差异。MinerU 是完整流水线，不能仅凭整页耗时就与单独识字引擎横排

## 当时的关注度与暂缓建议（历史）

本轮通过 GitHub API 核对的 stars 快照：PaddleOCR 91,970、MinerU 82,785、Tesseract 77,235、Docling 69,835、EasyOCR 30,121、RapidOCR 8,385、GLM-OCR 7,555。PaddleOCR-VL 共用 PaddleOCR 仓库，不能单独计算 stars。数字会变化，表示累计关注度，不代表效果排名或近期增速

- [Docling](https://github.com/docling-project/docling)：值得第二轮增加，尤其需要多格式、结构化输出或 RAG 集成时；首轮先用 MinerU 代表完整解析工具，控制接入规模。Docling 可以组合 OCR 后端，不能把包装层和独立识字模型混为一谈
- [EasyOCR](https://github.com/JaidedAI/EasyOCR)：常见且受关注，首轮已有三条传统识字路线，暂缓以避免重复覆盖；并非判定其效果较差
- [DeepSeek-OCR 2](https://github.com/deepseek-ai/DeepSeek-OCR-2)：保留候选，官方运行示例以 CUDA 为主；先核对资源和可部署路线再决定，不因热度直接加重首轮范围。本轮 API 查询失败，未记录其 stars
- Apple Vision：作为后续 Mac 原生延迟/部署成本对照；本轮不据此扩展第七个实现

## 新一轮评价

使用 balanced60-v1（中文及混排40、英文20）。统一输入与版本，先验证6份开发样本，再按任务评价冻结60份。新物料主要是文档与街景，不复现旧微爱截图业务效果，不能用本次结果声称旧场景结论已被推翻

文字指标与结构指标分开；ReCTS 测裁剪行识字，EST-VQA 测答案检出/问答，olmOCR 测断言。不能把六套工具在不同能力上的得分压成一个未定义的总准确率。预处理、模型加载、纯推理、完整流水线分别计时

## 重跑后清理约定

用户要求新一轮跑完后清理旧交接与旧测试物料，以新物料为准。本轮执行后按清单校验再删除历史批次；开发6份保留用于复跑预检，未混入主测60份

收尾顺序：先保存新结果与版本、确认退出及产物完整，再按 balanced60 清单把仍被引用的原图和参考整理到正式冻结物料目录，更新路径、验证哈希与恢复入口，最后删除不再引用的旧候选、重复下载包、旧开发物料及交接临时副本，压缩过时任务叙述

重要边界：当前60份中34份仍来自 pilot-20261030，另26份来自 zh-expansion-20261030；不能按“旧目录名”整批删除。保留新60份原件、参考、来源与哈希、复现脚本、新报告和最小历史出处。旧项目仍在使用的 welove-job 业务代码和运行数据不属于本工程交接副本，不因本次整理清理
