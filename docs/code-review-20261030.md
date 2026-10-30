# 项目级 Code Review

2026-10-30 · 以下为审查时发现；随后用户授权的6项修复已完成并验证，见[修复记录](review-fixes.md)

范围：src评分与Gradio运行链路、三轮执行/报告脚本、CLI安装与模型路径、物料恢复/清理、正式文档与测试。工程未初始化Git，因此审查当前工程文件，不是某个commit的diff

审查当时发现6项问题（3项P1、3项P2）；目前全部已修。以下复现与定位保留为历史问题记录，修复后的路径和验证以修复记录为准；没有发现需要直接作废本轮区域CER的证据

## R1 · P1 · 新轮运行目录没有传到worker，可能覆盖历史结果

位置：scripts/bench-v3-run.py:13、21、27、29；scripts/bench-v3-worker.py:15、29；scripts/bench-v3-report.py:13、91

协议要求新轮改BASE，但Python worker自己的输入和输出都固定在bench-20261030c，父进程只传engine。只修改runner的BASE后，父进程在新目录监控，worker仍读取旧清单、覆盖旧结果；报告也固定读取旧目录、写同名报告。另一个问题是runner在检查summary并拒绝覆盖前，已经改写inputs.json并重新编译二进制

隔离复现：临时目录中创建旧结果HISTORICAL_RESULT和新清单，用假推理函数执行原worker；旧结果变成NEW_RESULT，新目录没有结果。未运行模型，也未碰真实历史文件

建议：显式run_id/run_dir贯穿runner、worker、report；启动前一次性校验输入/参考/输出占用；新run独立输出与报告；任何写入前拒绝已有批次，失败续跑另设明确协议

## R2 · P1 · Docling正文提取丢失真实列表编号

位置：src/ocr_eval/metrics.py:92–93

Docling的ListItem把列表编号放在marker字段，text只存内容。当前提取器只取text，导致本来识别正确的A.、B.、1.等丢失，随后被CER算成漏字。这属于正文信息，不应与生成的Markdown装饰一并去掉

实际证据：本轮docling/omni-014.json存在marker='A.'、text='How exciting!'；抽取仅得到How exciting!。对正确参考A.How exciting!评分，凭空产生2次删除，CER 14.29%。整图输出共有16个带marker节点；当前60区域没有这种节点，因此没有证据说明上一轮区域主表受此项影响，但Gradio识别整页列表时会受影响

建议：按Docling节点契约还原正文中的列表标记，区分真实枚举编号与生成的项目符号；补原始JSON回归样例，验证标记既不丢失也不重复

## R3 · P1 · RapidOCR首次安装命令缺少必需的推理后端

位置：docs/cli-setup.md:8

命令只安装rapidocr==3.8.1。检查本机该版本官方发行包METADATA，Requires-Dist没有onnxruntime；其ONNX推理模块直接导入onnxruntime，缺失时抛ImportError。本机能运行，是因为uv-receipt.toml中额外安装了onnxruntime，不能证明文档命令可用于干净环境

建议：安装命令显式添加与实测一致的ONNX Runtime依赖并冻结版本，再用一次最小导入/识别验证安装说明。无需再建项目模型环境

## R4 · P2 · 中止或缺文件会让速度统计虚假变快

位置：scripts/bench-v3-report.py:39–42、57、84、98

缺少单图JSON时填seconds=0，随后无条件纳入均值和分位数。发生进程超时/OOM、未跑完或文件丢失时，未执行样本会被当成瞬间完成；报告标题还固定声称480次正式推理，未依据完成数量生成

最小复现：一条成功耗时2秒，加一条missing耗时0秒，timing返回均值1秒、P50为1秒。错误率把缺失算删除可以，但速度不能把缺失当0秒。当前已核对四引擎各120条全部存在且退出0，本轮主表未触发此问题

建议：未执行时间记null；单列成功延时、失败/超时耗时和覆盖数量；中止批次显式标记incomplete，不生成完成措辞或可直接比较的速度榜

## R5 · P2 · 评分器异常被当作OCR失败，还可能击穿整组UI

位置：src/ocr_ui/app.py:69–76、116

识别与评分共用一个try。评分依赖不可用、评分子进程超时或结构提取失败，即使OCR已成功，也会标成识别失败并计100%CER；异常分支再次调用同一个evaluate。如果评分器持续不可用，第二次异常直接逃逸，future.result()无隔离，整组生成器中止

隔离复现：假OCR返回“正确文字”，evaluate连续抛错，异常直接逃到调用者；仅第一次结构提取抛错时，仍把正确OCR结果标成error+CER=100%。没有修改正在运行的服务

建议：分离识别状态和评分状态；评分失败保留正文、耗时、raw，CER为不可用；每个future异常单独收口，其余引擎继续展示，整组最终状态可明确部分成功

## R6 · P2 · Ctrl-C后评测worker仍在后台运行

位置：scripts/bench-v3-run.py:33–62

worker用start_new_session=True脱离父进程会话，runner仅在自身资源阈值分支清理子进程，没有覆盖KeyboardInterrupt/监控异常的finally。用户停止评测后，worker可能继续占内存和改写结果，且没有exit记录

隔离复现：使用原runner逻辑、临时清单及sleep假worker，向runner发送SIGINT；runner退出-2，worker仍存活，exit.json未写。复现后已清理测试worker

建议：统一finally清理进程组，先TERM、限时等待、必要时KILL；记录interrupted及退出状态，不依赖仅正常流程写退出记录

## 验证与边界

- 现有6项评分单元测试全部通过；目前主要覆盖编辑距离、Unicode和少量结构抽取，不覆盖上述执行/失败链路
- 当前60原图+6开发图共132个输入/参考文件哈希验证通过，无需恢复下载
- 本轮四引擎均退出0、各120条结果齐全，冻结参考哈希匹配；未重跑模型或改写报告
- 最小复现脚本保存在.temp/reviews/project-20261030/check-core.py、check-ui.py、check-interrupt.py，正式问题描述在本文件
- 本次未做依赖漏洞扫描、完整干净机器安装、长时并发压测；不把静态检查称为这些验证
- docs/workflow.md还写着“尚无已运行OCR实现或评测”，与项目现状不符；属于文档维护项，不单独抬高为功能缺陷

后续已完成R1–R6修复，17项回归与12项真实推理通过，旧输出只读重评后区域主表未变化，无须重新跑480次模型推理
