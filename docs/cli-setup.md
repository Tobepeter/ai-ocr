# 用户级 OCR 工具

2026-10-30：日常调试统一使用uv用户级CLI，不在项目安装MinerU、Docling、RapidOCR的重复运行环境

## 安装与使用

```sh
uv tool install --python 3.12 --with 'onnxruntime==1.31.1' 'rapidocr==3.8.1'
uv tool install --python 3.12 --constraints data/reports/requirements-mineru.txt 'mineru==4.1.2'
uv tool install --python 3.12 --constraints data/reports/requirements-round1.txt --with 'rapidocr==3.8.1' --with 'onnxruntime==1.31.1' 'docling==2.108.0'
```

RapidOCR不自动安装ONNX Runtime，命令中的`--with`不可省略；已在临时独立工具环境验证该组合，完成后删除临时环境，正式环境仍只保留用户级一份

安装后执行`.venv/bin/python scripts/prepare-global-models.py`，初始化并核对RapidOCR权重，补齐历史模型名，再链接Docling的共享权重。已有不同文件不会覆盖，工具重装后可重跑；完整顺序见[复现指南](reproduce.md)

现有工具无需重复安装。依赖约束保留实测版本；不要用未固定版本升级覆盖历史结果

项目入口只转发给PATH中的全局CLI，MinerU默认Basic/ONNX/CPU，Docling默认RapidOCR后端：

```sh
python3 scripts/ocr-tools.py rapid -img '图片.png'
python3 scripts/ocr-tools.py mineru '文档.pdf' -o '结果.md'
python3 scripts/ocr-tools.py docling '文档.pdf' --output './结果'
```

也可以直接使用全局rapidocr、mineru-kit、docling。MinerU命令使用`mineru-kit parse`处理全部页面，不混用文档库读取命令的默认分页行为

## Apple Vision状态

Apple Vision是第四条已评测路线，但不是上述用户级CLI之一。已有[scripts/bench-vision.swift](../scripts/bench-vision.swift)批量评测程序和[src/ocr_ui/vision.swift](../src/ocr_ui/vision.swift)单图程序，后者由[Gradio页面](ocr-ui.md)调用；尚未接入ocr-tools.py。它使用macOS系统框架，无需另外下载上述OCR模型

## 缓存与环境

- `uv tool dir`给出用户工具环境根目录；命令入口由uv管理，任意项目均可用
- MinerU复用`~/.mineru/models/`的ONNX权重
- Docling复用`~/.cache/huggingface/hub/`中的版面/表格权重
- RapidOCR小型权重随Python包位于工具环境；Docling环境需要自己的RapidOCR库，不能直接共享另一个环境的Python依赖。日常CLI默认模型名通过符号链接复用全局RapidOCR已有权重；评测脚本显式复用独立RapidOCR工具的模型路径，保持原评测设置
- 项目`.venv`只保留Pillow、rapidfuzz、psutil等轻量辅助依赖；不保留`.venv-mineru`
- `.venv-mlx`是另两款视觉模型的独立实验环境，与这三个CLI不重复，本次保留
- EasyOCR仅为历史可选实验，`uv sync --extra easy`可按需恢复；默认不装

## 评测复跑

```sh
uv sync
.venv/bin/python scripts/bench-v3-run.py --run-dir data/outputs/bench-next --engines rapid apple mineru docling
.venv/bin/python scripts/bench-v3-report.py --run-dir data/outputs/bench-next
```

评测为保留模型常驻、逐页时间与结构化结果，使用`uv tool dir`定位全局工具自带Python执行worker；不会逐页启动CLI导致计时口径变化。批次目录与报告目录必须不存在，已有目录会在写入前拒绝。runner、worker和report共享明确的批次路径，旧成绩不会被覆盖。前两轮脚本仅作为历史实现保留，当前使用上面的v3入口

安装/迁移不等于重新测量60份。模型和物料缓存保留；Gradio服务是否运行以当前进程为准
