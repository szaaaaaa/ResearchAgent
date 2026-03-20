# Claim-Evidence 映射弱问题工程落地说明

> 更新说明：本文聚焦 claim-evidence 子问题。跨问题不回归总方案请参考 `docs/final-no-regression-remediation-plan.md`。

## 1. 背景与问题

在运行 `outputs/run_20260222_174809`（时间戳：2026-02-22 18:08:13）中，报告生成成功，但验收失败，核心问题为：

- `claim_evidence_support: fail`
- `claim_report_traceability: warn`
- `report_critic.issues` 包含 `claim_evidence_mapping_weak`

现象：`research_state.json` 中有 `claim_evidence_map`，但最终 `research_report.md` 中缺少足够显式的 claim-evidence 对应表达，导致校验脚本无法确认“每条 claim 被证据支撑并落到正文”。

## 2. 影响

1. 严格验收（`validate_run_outputs --strict`）不通过。  
2. 报告可读性与可追溯性下降（读者难以快速核验结论来源）。  
3. 评估指标失真（状态中有证据，但报告层面表现为“无支撑”）。

## 3. 根因（工程视角）

1. 报告模板未强制保留或重建 `Claim-Evidence Map` 章节。  
2. 报告修复阶段（repair）未把“claim 与 evidence URL 共现”作为硬约束。  
3. critic 校验依赖“报告文本中 claim/evidence 可检索”，与最终文稿结构耦合较强。

## 4. 目标（高标准但不死板）

1. 不要求固定章节名称，但要求每条 claim 在报告中可追溯到至少 1 条证据 URL/标题。  
2. 报告生成后若缺失映射，自动执行一次“映射补全修复”。  
3. 保持当前软门控策略：`experiment_results_missing` 仅作为 soft issue，不阻断通过。

## 5. 改造方案（最小改动）

### 方案 A（推荐，优先）

在 `generate_report` 末尾增加一步“映射补全器”：

1. 读取 `claim_evidence_map`。  
2. 检查每条 claim 是否在报告中出现，且对应 evidence（URL 或标题前缀）是否共现。  
3. 若不满足，则在“结论/讨论后、参考文献前”插入简版 `Claim-Evidence Mapping` 章节（每条 claim + 1~2 条证据链接）。

优点：改动集中、可控、对现有 prompt 侵入小。  

### 方案 B

强化报告主 prompt，明确要求“每个 Key Finding 行内必须附带 evidence URL”。  

优点：实现简单；缺点：受模型随机性影响，稳定性不如方案 A。

## 6. 验收标准

以单次 run 为单位，满足：

1. `validate_run_outputs` 中 `claim_evidence_support` = pass。  
2. `claim_report_traceability` 不低于阈值（默认 70%）。  
3. `report_critic.issues` 不再包含 `claim_evidence_mapping_weak`。  
4. `references` 计数正常（已支持 `*`/`-`/`+`/编号列表）。

## 7. 实施步骤

1. 在报告生成节点增加映射补全函数（插入章节，不改主流程）。  
2. 新增/更新单测：
   - 报告无映射时会自动插入；
   - 插入后 critic 不再报 `claim_evidence_mapping_weak`；
   - 不破坏 references 预算和章节预算。  
3. 用同一 topic 回归测试（至少 2 次）验证稳定性。

## 8. 风险与回滚

风险：

1. 报告长度增加，可能触发 section/reference 预算边界。  
2. 若 claim 本身过长，字符串匹配仍可能不稳定。

回滚：

1. 映射补全步骤可通过配置开关关闭（建议新增 `agent.report_enforce_claim_mapping`）。  
2. 保留旧 prompt 流程，必要时一键退回。
