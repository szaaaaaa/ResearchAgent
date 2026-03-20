# 最终收敛方案：问题彻底修复与不回归策略

## 1. 目标与约束

目标：一次性解决当前暴露的问题，并避免“修新问题导致旧问题复发”。

硬约束：
1. 不降低现有验收标准阈值（不走“放宽标准”路线）。
2. 新增逻辑必须可回归测试覆盖。
3. 指标口径在 `critic` 与 `validator` 之间保持一致。
4. 迭代过程中的中间产物不得在末轮被空结果覆盖。

---

## 2. 现状结论（基于已有运行）

关键运行对照：
1. `run_20260222_222740`：claim 支撑通过，但有 RQ 对齐和引用结构告警。
2. `run_20260223_115419`：前期抓取/分析成功，但最终 state 归零，导致 claim/evidence 全线失败。

结论：当前最大根因是“状态累积语义错误”，其次是“引用提取口径双轨不一致”。

---

## 3. 根因依赖图（避免头痛医头）

1. `fetch/analyze` 返回增量列表  
-> 末轮空增量覆盖历史  
-> `papers/analyses` 归零  
-> claim map 退化为“Insufficient evidence”  
-> `claim_evidence_support`/`traceability`/`missing_references` 连锁失败。

2. `validator` 与 `critic` 的 references 提取逻辑不一致  
-> 同一报告可能出现“一个通过、一个失败”的口径冲突  
-> 调优方向被误导。

---

## 4. 最优工程策略（最终版）

采用 **S1 + S2 + S3 + S4 + S5** 的组合，按顺序落地。

### S1. 修复状态累积语义（P0，先做）

修改点：
1. `src/agent/nodes.py:fetch_sources`
2. `src/agent/nodes.py:analyze_sources`

规则：
1. 节点返回值改为“累计值”而非“本轮增量值”。
2. 按 `uid/url/title` 去重，保持稳定顺序。
3. `status` 保留“本轮新增数”用于观测。

不回归保证：
1. 任意后续迭代返回 0，历史数据不丢失。
2. `events.log` 统计与 `research_state.json` 终态一致。

### S2. 统一 references 提取口径（P0）

修改点：
1. 抽出共享函数（建议放 `src/agent/core/reference_utils.py`）。
2. `src/agent/nodes.py:_extract_reference_urls` 与 `scripts/validate_run_outputs.py:extract_reference_urls` 统一调用同一实现。

规则：
1. 只在 `References/Bibliography/参考文献` 章节内统计证据 URL。
2. 不把 `Experimental Blueprint` 的 dataset/resource URL 计入证据引用统计。

不回归保证：
1. `critic` 与 `validator` 对同一报告的 references 计数一致。
2. 消除“口径不一致导致的假冲突”。

### S3. 引用规范化为 URL-first（P1）

修改点：
1. `src/agent/nodes.py:_clean_reference_section` 后新增一步“引用规范化”。

规则：
1. `arXiv:xxxx` 统一转 `https://arxiv.org/abs/xxxx`。
2. DOI 统一转 `https://doi.org/<doi>`。
3. 无法转成 URL 的条目不计入证据引用，且记录告警。

不回归保证：
1. 解决“有引用文本但无可解析 URL”导致的 `missing_references`。
2. 保持 reference budget 与 domain profile 的可解释性。

### S4. 保持 claim-RQ 对齐 + 映射补全（P1，已做能力不回退）

保留并校验现有能力：
1. claim 对齐器（RQ anchor terms）保持启用。
2. 报告末端 claim-evidence mapping 自动补全保持启用。

新增约束：
1. 仅当 `claim_map` 非空时补全映射章节。
2. 映射补全不突破 section/reference 预算。

不回归保证：
1. 不再回到“state 有映射，报告不可追溯”的旧问题。

### S5. 实验闭环采用“高标准但不死板”（P1）

规则：
1. 有实验计划但无验证结果：保留 `experiment_results_missing` 作为 soft issue。
2. 不因 soft issue 直接否决基础研究报告。
3. 若有 validated 结果，必须进入结果章节并参与 claim 支撑优先级。

不回归保证：
1. 不阻塞测试阶段。
2. 不牺牲严谨性（结果存在时必须对齐 RQ）。

---

## 5. 不回归检查矩阵（旧问题逐项兜底）

1. 旧问题：429/403/404 噪音  
防回归：维持白名单下载 + 403 短期负缓存 + 429 退避重试；不回退配置。

2. 旧问题：claim_evidence_mapping_weak  
防回归：S1 保证证据不丢，S4 保证文本可追溯。

3. 旧问题：claim_rq_relevance warn  
防回归：保持 deterministic 对齐器，不新增随机 LLM 改写链路。

4. 旧问题：reference_domain_profile 噪声  
防回归：S2 统一“只统计 References 章节”。

5. 新暴露问题：末轮清空历史  
防回归：S1 的累计语义 + 终态一致性测试。

---

## 6. 代码落地顺序（最小改动）

1. 先做 S1（状态累积）并补单测。  
2. 再做 S2（引用提取共享函数）并补一致性测试。  
3. 然后做 S3（URL 规范化）并补格式化测试。  
4. 最后执行全链路回归（含实验闭环场景）。

---

## 7. 验收标准（必须同时满足）

1. 一致性：
   - `events.log` 中累计产出与 `research_state.json` 终态一致。
2. 支撑性：
   - `claim_evidence_support = pass`
   - `rq_min2_evidence_rate > 0`
3. 引用性：
   - `missing_references` 不再由“非 URL 引用”触发。
   - `critic` 与 `validator` 的 references 计数一致。
4. 稳定性：
   - 同一 topic 连跑 2 次，结果不出现“前期有数据、终态清空”。

---

## 8. 结论

彻底方案不是继续叠加 prompt，而是先修“状态语义 + 口径统一”这两个基础层问题。  
只要 S1/S2 先落地，后续 claim、references、实验闭环都会进入可稳定优化区间，不会再出现“修新问题把旧问题带回来”的循环。


