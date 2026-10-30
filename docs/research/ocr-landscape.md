# OCR 方案概览

历史调研快照，整理迁入正式文档时未重新联网核验版本、部署条件或许可证；集成前须复核对应官方来源

查询日期：2026-10-30，使用 Exa Search / Fetch，优先项目官方仓库与产品文档。本轮是能力与部署路线调研，未安装、运行或横向测评模型

## 结论与分类

OCR 需要先区分输出目标：图片转文字与坐标、扫描 PDF 加可搜索文字层、整份文档还原为 Markdown/JSON/表格/公式、按业务要求提取字段。相应方案有引擎、流水线工具、专用视觉语言模型和云 API，不宜把它们直接放在同一准确率排行榜

推荐方向是本轮基于功能与用户既有本地 CLI 偏好的判断，不是实测排名

## 本地文字识别

| 方案 | 定位与能力 | 使用判断 |
| --- | --- | --- |
| [RapidOCR](https://github.com/RapidAI/RapidOCR) | 将 PaddleOCR 模型工程化部署到 ONNX 等后端，默认中英，可离线、多平台 | 日常截图、脚本识字的第一候选；延续历史工作，但不能把旧样本结论当作新版本评测 |
| [PaddleOCR / PP-OCR](https://github.com/PaddlePaddle/PaddleOCR) | 场景文字检测与识别，可训练与部署；检索到 PP-OCRv6 的 tiny/small/medium 路线 | 需要模型选择、专项优化或更完整中文 OCR 工具链时使用 |
| [Tesseract](https://github.com/tesseract-ocr/tesseract) | 成熟 CLI 与库，支持纯文本、hOCR、TSV、PDF 等输出 | 规整扫描文本、批量脚本与 PDF 工具链的基础候选 |
| [EasyOCR](https://github.com/JaidedAI/EasyOCR) | Python / PyTorch，返回框、文字、置信度，支持多语与 CPU 模式 | 已有 Python/PyTorch 环境时易于接入 |
| [Apple Vision](https://developer.apple.com/videos/play/wwdc2021/10041/) | Apple 平台原生文本识别 API，提供语言配置与识别结果 | Mac 原生工具可纳入比较；框架本身不是现成通用 OCR CLI，支持语言应按系统和请求配置查询 |

RapidOCR 官方文档推荐先用 ONNX Runtime CPU。RapidOCR 与 PaddleOCR 并非完全独立的模型家族：比较时需要同时记录模型版本与推理后端，否则可能只比较了部署包装

来源：[RapidOCR 推理后端文档](https://github.com/RapidAI/RapidOCRDocs/blob/main/docs/install_usage/rapidocr/how_to_use_infer_engine.md)、[模型列表](https://rapidai.github.io/RapidOCRDocs/main/en/model_list/)

## PDF 与完整文档工具

| 方案 | 主要作用 | 部署与边界 |
| --- | --- | --- |
| [OCRmyPDF](https://github.com/ocrmypdf/OCRmyPDF/blob/main/README.md) | 给扫描 PDF 加可搜索、复制的文字层，可旋转纠正和去歪斜 | 默认使用 Tesseract，可通过插件换引擎；目标主要是可搜索 PDF，不是复杂文档语义解析 |
| [PP-StructureV3](https://github.com/PaddlePaddle/PaddleOCR) | 版面分析、表格、文本与结构化输出 | 与 PP-OCR、PaddleOCR-VL 区分；官方介绍强调较细的文本与表格单元格坐标 |
| [MinerU](https://github.com/opendatalab/MinerU) | PDF/文档解析，Markdown/JSON 等导出、表格、公式与阅读顺序 | 当前文档分 Flash/Basic/Standard/Advanced；Basic 可用 CPU，高档位采用小模型加 VLM |
| [Docling](https://github.com/docling-project/docling) | 多格式文档转换、统一文档结构、表格/阅读顺序、CLI 与 API | 本地运行，支持 macOS/Linux/Windows；可选 OCR 后端，也可用 VLM 流水线 |
| [Marker / Surya](https://github.com/datalab-to/marker) | Marker 提供文档转换，Surya 提供 OCR/版面/表格能力 | 当前有 CPU/MPS 与 GPU 路线；代码许可与模型权重许可分别确认 |

Mac 本地重点可比较 MinerU 和 Docling。MinerU 当前文档列出 Apple Silicon 的 Torch/MPS + llama.cpp/Metal 路线，建议至少 16 GB 统一内存；这只是官方规划建议，不保证具体文件的速度和峰值内存。本轮没有跑本机验证

来源：[MinerU 运行层级与硬件](https://opendatalab.github.io/MinerU/usage/tiers/)、[Docling OCR 后端](https://docling-project.github.io/docling/concepts/OCR/)、[Surya](https://github.com/datalab-to/surya)

许可方面：Docling 代码 MIT，但模型各自授权；Marker 代码 Apache 2.0，权重附带商业条件；MinerU 当前仓库声明基于 Apache 2.0 加附加条件的项目许可证，不沿用早期 AGPL 介绍作为当前结论。正式集成前以选定版本的 LICENSE 和模型条款为准

## OCR 专用视觉语言模型

这类模型把图像编码后生成文字和结构，适合复杂文档、公式、表格、字段提取。是否支持本地并不等于轻量；需区分模型权重、推理后端和上层文档工具

| 模型/项目 | 本次确认的能力与路线 |
| --- | --- |
| [PaddleOCR-VL-1.6](https://github.com/PaddlePaddle/PaddleOCR/releases) | 官方记录 2026-05-28 发布，0.9B 文档解析路线，文字、公式、表格等；不能与 PP-OCRv6 的场景文字模型混为一谈 |
| [GLM-OCR](https://github.com/zai-org/GLM-OCR) | 0.9B，复杂文档、表格、公式与信息提取；官方列出 vLLM、SGLang、Ollama 支持；SDK 也有云 API 路线 |
| [HunyuanOCR-1.5](https://github.com/tencent-hunyuan/hunyuanocr) | 官方记录 2026-07-07 发布，统一文档解析、文字定位、信息提取、图文翻译，提供 llama.cpp 的 PC 部署路线 |
| [DeepSeek-OCR 2](https://github.com/deepseek-ai/DeepSeek-OCR-2) | 文档转 Markdown / 自由 OCR，官方安装示例以 CUDA、PyTorch、vLLM/Transformers 为主；未验证 Mac 移植 |
| [dots.ocr / dots.mocr](https://github.com/studio-dots-ai/dots.mocr) | 多语文档解析，dots.mocr 进一步涉及结构图、UI/图表转 SVG 等；原仓库记录 2026-03-19 的命名变化 |
| [olmOCR](https://github.com/allenai/olmocr) | PDF/图片转 Markdown，表格、公式、手写、阅读顺序；官方描述为 7B VLM，需要 GPU |

不按各家不同基准中的 SOTA 宣传排名。需要比较时应固定同一批中文截图、扫描 PDF、表格与公式样本，检查漏字、补字、阅读顺序、表格结构和资源成本

## 云 API

| 方案 | 适合目标 | 关键边界 |
| --- | --- | --- |
| [Mistral OCR / Document AI](https://docs.mistral.ai/studio/document-processing/basic_ocr) | 文档转 Markdown、表格、结构和坐标 | 字段与功能按模型版本区分；本轮不报价 |
| [Google Document AI](https://docs.cloud.google.com/document-ai/docs/enterprise-document-ocr) | OCR、文档质量检测、后续结构化文档处理 | 具体提取能力需选择相应 processor，不把通用 OCR 等同于所有业务字段提取 |
| [Azure Document Intelligence](https://docs.azure.cn/en-us/ai-services/document-intelligence/language-support/ocr?view=doc-intel-4.0.0) | Read、Layout、表格、表单与预建业务模型 | 支持语言依模型和印刷/手写任务不同，不能笼统概括 |
| [腾讯云 OCR](https://cloud.tencent.com/product/ocr)、[百度 OCR](https://cloud.baidu.com/product/OCR/general.html) | 中文票据、卡证、手写、表格与通用识别 | 可按具体业务接口提取结构化字段；页面价格与宣传准确率未作为本轮选型依据 |
| [Amazon Textract](https://aws.amazon.com/textract/) | 文本、表单、表格与文档结构 | 官方列出的文本语言为英法德意葡西，未列中文；不作为中文优先候选 |

Textract 语言边界来源：[官方限制](https://docs.aws.amazon.com/textract/latest/dg/limits-document.html)

## 对本任务的建议

1. 日常截图和 UI 自动化：保留 RapidOCR，增加 Apple Vision 作为 Mac 原生对照；Tesseract 继续作规整扫描文本候选
2. 扫描 PDF 只需可搜索/复制：优先 OCRmyPDF
3. PDF 转 Markdown、表格、公式：先比较 MinerU 与 Docling，必要时加入 PaddleOCR-VL
4. 专门体验本地 OCR 大模型：GLM-OCR 与 HunyuanOCR 可作为候选，安装前核对所选后端和硬件，不把模型规模等同于运行内存
5. 云端省部署：文档解析看 Mistral/Google/Azure；中文制式票据字段看国内专用 API

已知材料只证明历史微爱截图里 RapidOCR 被选中；上述新候选均未经过本机实测，不需要因这次调研立即安装所有工具
