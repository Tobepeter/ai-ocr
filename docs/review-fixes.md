# 六项审查问题修复

2026-10-30 · R1–R6全部修复 · 历史原始结果、冻结参考和原报告保持不变

| 问题 | 修复 | 验证 |
|---|---|---|
| R1 新轮覆盖旧轮 | runner/worker/report显式传递run-dir；独占批次与报告目录；写入前校验；保存参考快照 | 隔离回归、新目录四引擎实跑12项、旧目录实际拒绝启动；601个历史文件哈希不变 |
| R2 列表编号漏计 | 枚举编号和orig中的真实符号还原，已存在的不重复，生成的项目符号不补入 | 原错误例CER由14.29%变0；240个区域评分无变化，2张Docling整图提取文本恢复标记 |
| R3 安装缺推理后端 | RapidOCR安装显式添加onnxruntime==1.31.1 | 临时独立uv工具环境离线安装及真实识别通过，复用权重，临时环境已删除 |
| R4 缺失计0秒 | 缺失耗时null；成功延时、失败耗时、覆盖数量分开；中止批次不展示可比较速度 | 2秒成功+缺失的均值仍为2秒；中止报告标incomplete与实际结果数量 |
| R5 评分异常击穿UI | 识别/评分状态分离；异常不重试同一评分器、不计伪100%；future逐项隔离 | 模拟OCR/评分分别及同时失败、未预期future异常；实际网页四引擎并行成功 |
| R6 中断遗留worker | finally统一清理进程组，TERM/等待/KILL，记录interrupted；SIGTERM按中断处理 | 真子进程及孙进程测试，SIGINT后都退出并保留exit记录 |

## 结果与入口

- 17项回归：`.venv/bin/python -m unittest discover -s tests -v`
- 新轮启动：`.venv/bin/python scripts/bench-v3-run.py --run-dir data/outputs/bench-next`
- 新轮报告：`.venv/bin/python scripts/bench-v3-report.py --run-dir data/outputs/bench-next`
- 只读重评旧轮：增加`--report-dir`指定不存在的新报告目录，不能覆盖旧报告
- [评分修复后的历史输出重评](../data/reports/benchmark-v3-review-fixes/report.md)：480条输出重评，区域主表未变，没有重新运行这480次推理
- [验证汇总](../data/reports/shareable/review-fixes.json)：安装、实跑、网页与历史哈希证据
- 真实小规模实跑位于data/outputs/validation-six-20261030，四方案各2区域+1整图；用于工程验收，不更新性能排名

网页恢复到127.0.0.1:7861，使用修复后的代码。安装验证没有改动全局工具环境，没有新增长期模型副本。项目仍未初始化Git/提交/CI
