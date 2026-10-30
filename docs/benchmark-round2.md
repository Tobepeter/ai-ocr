# OCR 第二轮协议

日期2026-10-30，承接用户“都不大，可以做，试试吧”的授权，解除第一轮单方案新增权重1 GiB软预算。仍控制实际运行开销：进程树RSS采样超过24 GiB停止；MLX额外限制分配16 GiB、缓存1 GiB，单页约180秒上限；开发6份至少5份成功且中位耗时≤30秒，才扩至冻结60份

## 对照与候选

沿用balanced60-v1及第一轮预处理PNG，40份中文及混排、20份英文，长边最多2000像素，无PDF原有文字层。第二轮不重选“有利样本”，不覆盖第一轮输出

- Apple Vision：macOS26.3，VNRecognizeTextRequest revision3，accurate、zh-Hans/zh-Hant/en-US，minimumTextHeight=0，languageCorrection=true，自动设备调度
- GLM-OCR：mlx-community/GLM-OCR-bf16，MLX Metal，固定提示Text Recognition:
- PaddleOCR-VL：官方PaddleOCR-VL-1.6，MLX Metal，固定提示OCR:
- MinerU4.1.2：Basic、ONNX、CPU、ocr_mode=ocr，完整本地小模型文档流水线；不启用VLM或远端API
- Tesseract5.5.2补测：原配置重新跑60份，主要补进程树内存统计

两款VLM先测直接整图输入的模型，**没有接入官方布局检测+区域切分完整流水线**，不能将其结果当成官方产品/完整pipeline上限。模型自有图像处理参数保持默认，生成上限8192 tokens、temperature0；命中上限标记truncated，不算完整成功。每页记录生成token、时间和MLX内存池峰值，页后清理可释放缓存

## 内存、耗时和质量

本轮不同引擎串行推理，模型下载/环境准备可能重叠；本机并非专用隔离压测环境。GPU和自动调度单列，不与第一轮CPU4线程当作同设备基准

每200ms读取父进程与后代RSS之和，记录整轮与逐页采样峰值。共享页可能重复计数、瞬时峰值可能漏采；Apple系统服务和驱动开销可能在进程树外。MLX内存池峰值另列，不能直接与RSS相加。第一轮的ru_maxrss与本轮采样RSS方法不同，均非全系统物理占用

报告初始化、预热、逐页中位/P95、60份识别合计及退出状态。下载失败、环境修复、中断恢复与推理失败分别记录。超时导致进程终止时，仅标记已完成范围，不补造完整60份结果

MinerU Markdown可能内嵌base64图片；原始结果保留，评分前剥离图片data URI，防止二进制编码被误计为文字命中

质量继续用第一轮冻结参考与评分脚本：表单/文档严格片段覆盖、街景指定答案检出、招牌字符错误率、旧扫描局部严格断言。失败/截断不从分母剔除。没有新增全页人工金标准，故不将覆盖率称为整体正确率

## 复跑

Apple工具源代码在scripts/bench-vision.swift，二进制放本地输出目录。实测时Python隔离环境为.venv-mlx、.venv-mineru；后者现迁移为用户级MinerU工具，见[CLI使用](cli-setup.md)，冻结依赖见data/reports/requirements-*.txt，模型保存到用户级缓存

```sh
swiftc -O scripts/bench-vision.swift -o data/outputs/bench-20261030b/setup/vision-ocr
uv run scripts/bench-round2-run.py vision glm paddlevl mineru tesseract
python3 scripts/bench-round2-score.py
```

需要先按scripts/bench-download-vlm.py下载固定模型，MinerU模型准备命令为`mineru-kit models download --tier basic --small-backend onnx --source huggingface`。完成阶段默认跳过；重新测量应另建运行目录，不能用旧exit.json误认为新测试

## 官方依据

- [Apple文字识别](https://developer.apple.com/documentation/vision/recognizing-text-in-images)
- [GLM-OCR MLX](https://github.com/zai-org/GLM-OCR/blob/main/examples/mlx-deploy/README.md)
- [MLX-VLM GLM模型用法](https://github.com/Blaizzy/mlx-vlm/blob/main/mlx_vlm/models/glm_ocr/README.md)
- [PaddleOCR-VL Apple Silicon](https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/pipeline_usage/PaddleOCR-VL-Apple-Silicon.en.md)
- [MinerU档位](https://opendatalab.github.io/MinerU/usage/tiers/)、[Python SDK](https://opendatalab.github.io/MinerU/usage/sdk_api/)
