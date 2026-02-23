# run_20260223_115419 问题分析与解决方案

> 更新说明：本文对应单次 run 复盘。跨问题的最终收敛方案请以 `docs/final-no-regression-remediation-plan.md` 为准。

## 1. 背景
- 运行目录：`outputs/run_20260223_115419`
- 主题：Embedding-aware Prototype Prioritized Replay for Online Time-Series Forecasting under Concept Drift
- 结果状态：`overall=fail`

## 2. 关键现象
1. 验收核心指标为 0。
2. 报告有正文和引用段，但 claim-evidence 映射几乎全部为“证据不足”。
3. 日志显示前期抓取与分析成功，但最终 state 中 `papers/web_sources/analyses` 变成空列表。

## 3. 证据链（可复核）
1. 指标失败：
   - 文件：`outputs/run_20260223_115419/metrics.json`
   - 关键值：`rq_min2_evidence_rate=0.0`、`avg_a_evidence_ratio=0.0`、`rq_coverage_pass=false`
2. 前期有成果：
   - 文件：`outputs/run_20260223_115419/events.log`
   - 迭代 0：`fetch_sources` 抓到 18 papers，`analyze_sources` 产出 14 analyses / 64 findings
3. 最终被“清空”：
   - 文件：`outputs/run_20260223_115419/research_state.json`
   - 最终值：`papers=[]`、`web_sources=[]`、`analyses=[]`
4. 引用提取不通过：
   - 文件：`outputs/run_20260223_115419/research_report.md:87`
   - References 里主要是 `[arXiv:xxxx]`、`[DOI]` 文本，缺少 `http/https` URL

## 4. 根因分析

### 4.1 根因 A：跨迭代状态被增量结果覆盖
- `src/agent/nodes.py:2232` 在 `fetch_sources` 返回 `papers: new_papers`、`web_sources: new_web`（仅本轮增量）。
- `src/agent/nodes.py:2600` 在 `analyze_sources` 返回 `analyses: new_analyses`、`findings: new_findings`（仅本轮增量）。
- 当后续迭代抓取为 0 时，增量空列表覆盖历史累计，最终状态被冲掉。

### 4.2 根因 B：引用结构与 validator 口径不一致
- `src/agent/nodes.py:1285` 的 `_extract_reference_urls` 只统计列表项中的 `http/https`。
- `scripts/validate_run_outputs.py:143` 的 `extract_reference_urls` 也主要按 URL 计数。
- 报告 References 未稳定输出 URL，触发 `missing_references` 与 traceability 降级。

### 4.3 根因 C：实验闭环缺失（软门控）
- `src/agent/nodes.py:1380` 起，若有实验计划但无 validated 结果，会标记 `experiment_results_missing`（soft issue）。
- 当前 run 未注入人工实验结果，属于预期“未闭环”状态。

## 5. 解决方案（按优先级）

### 5.1 P0：修复状态累积语义（必须先做）
1. `fetch_sources` 改为返回“累计列表”而非“本轮增量”：
   - `papers = state.papers + new_papers（按 uid 去重）`
   - `web_sources = state.web_sources + new_web（按 uid 去重）`
2. `analyze_sources` 同理改为累计返回：
   - `analyses = state.analyses + new_analyses（按 uid 去重）`
   - `findings = state.findings + new_findings（去重+截断）`
3. 保留 `status` 中的“本轮新增数量”，便于观测增量。

预期收益：解决“前面有结果、最后归零”的主故障，claim-evidence 统计恢复到真实水平。

### 5.2 P1：统一 References 输出格式（URL-first）
1. 报告 References 强制使用可解析 URL（优先 `https://arxiv.org/abs/...`、`https://doi.org/...`）。
2. 若模型输出仅 `[arXiv:xxxx]`，在后处理阶段补全为 URL。
3. 保留原 citation label 作为可读信息，但不替代 URL。

预期收益：`missing_references` 显著下降，validator 的 reference/traceability 指标可稳定计数。

### 5.3 P1：实验闭环采用“高标准但不死板”
1. 允许两种可通过路径：
   - Path A：有 validated 实验结果，正常闭环。
   - Path B：无结果但明确标注“待实验验证”与风险边界，作为 soft warning，不阻塞基础报告产出。
2. 在报告新增“实验执行状态”字段，明确是否已完成人工回填。

预期收益：兼顾工程可用性和研究严谨性，避免测试阶段被硬阻塞。

## 6. 验证与验收标准
1. 功能回归：
   - 同一 run 的 `events.log` 与 `research_state.json` 统计应一致（不再出现前期非零、最终归零）。
2. 指标回归：
   - `rq_min2_evidence_rate > 0`
   - `claim_evidence_support` 不再恒为 0%
   - `missing_references` 不再因 URL 缺失触发
3. 人工抽检：
   - 任取 3 条 claim，均可在 References 找到可访问 URL 对应证据。

## 7. 建议改动顺序（最小改动）
1. 先改 `fetch_sources` 与 `analyze_sources` 的返回累积语义。
2. 再改 References 后处理（URL 补全）。
3. 最后微调实验闭环 gate（保持 soft issue，不做硬失败）。
