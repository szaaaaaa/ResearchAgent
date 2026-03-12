# 运行中 429 / 403 / 404 问题复盘（中文）

## 1. 现象总览

近期运行中出现的典型日志：

- `Semantic Scholar ... status=429 ... Retrying ...`
- `SerpAPI search failed ... 429 Client Error: Too Many Requests`
- `PDF download failed ... 403 Client Error: Forbidden`
- `PDF not found ... 404`

这些问题大多发生在 **fetch_sources / PDF 下载阶段**，表现为“搜得到条目，但下载不到 PDF”。

## 2. 根因分析

### 2.1 429（Too Many Requests）= 速率/配额限制

主要来源：

- Semantic Scholar API（公共接口限流）
- SerpAPI（Google Scholar/Google 搜索配额或速率上限）

典型原因：

1. 查询量大：每轮 query 数量多、每 query 请求多个学术源。  
2. 单次返回量大：`max_results_per_query` 偏高。  
3. 重试叠加：遇到 429 后指数退避重试，整体等待时间拉长。  
4. 外部配额限制：免费额度、同 IP/同 key 高频调用。

代码证据：

- `src/ingest/web_fetcher.py:545`：Semantic Scholar 对 `429`/`5xx` 做退避重试。  
- `src/ingest/web_fetcher.py:175`：SerpAPI 调用入口；失败时记录错误。  
- `src/agent/plugins/search/default_search.py:589`：S2 的 `max_retries/retry_backoff_sec` 来源配置。

---

### 2.2 403（Forbidden）= 有结果但无权限直链下载

主要来源：

- 出版社/期刊站点（Wiley/MDPI/Hindawi/IEEE 等）PDF 直链。

典型原因：

1. 付费墙/机构订阅限制。  
2. 反爬虫策略（UA、Referer、Cookie、频率控制）。  
3. DOI 或落地页给出的 PDF 链接对脚本访问不开放。  

为什么会“搜到但下不来”：

- 搜索 API 返回的是论文元数据或落地页 URL，不等于可匿名下载 PDF。  
- 系统未使用机构代理或登录态，因此对大量 publisher 直链会被拒绝。

代码证据：

- `src/agent/plugins/search/default_search.py:406`：仅允许白名单域名下载（默认开启）。  
- `src/agent/plugins/search/default_search.py:427`：遇到 `403` 时把 host 加入临时负缓存。  
- `src/agent/plugins/search/default_search.py:377`：负缓存 TTL 机制（避免重复打同一受限域名）。

---

### 2.3 404（Not Found）= 链接失效/地址模式变更

主要来源：

- 过期 PDF 链接、错误 DOI 映射、publisher URL 规则变化。

典型原因：

1. 元数据中的 PDF URL 已失效。  
2. DOI 对应版本变化，旧路径不存在。  
3. 站点重定向/路径改版。

代码证据：

- `src/agent/plugins/search/default_search.py:435`：404 被识别为 “PDF not found” 并跳过，不会中断主流程。

## 3. 当前实现中已经有的防护

1. **白名单下载策略**（减少无效直链尝试）  
   - `sources.pdf_download.only_allowed_hosts: true`  
   - 默认白名单在 `src/agent/core/config.py:85` 附近。
2. **403 域名短期负缓存**（降低噪音和重复失败）  
   - `forbidden_host_ttl_sec`，默认 1800 秒。
3. **429 指数退避重试**（避免瞬时失败直接中断）  
   - Semantic Scholar 重试与 backoff 已接入。
4. **失败不致命**  
   - 多数下载失败只记日志，不会让整个 run 崩溃。

## 4. 为什么看起来像“卡住”

常见误判场景：

1. 429 后触发退避重试（1.5s、3s、6s...），终端长时间无新业务输出。  
2. query 数量多，多个 provider 串行调用，整体耗时显著增加。  
3. PDF 下载失败很多，但每次都要走网络超时/重试。

结论：多数情况是 **慢**，不是 **死锁**。

## 5. 建议配置（降低噪音版）

可在 `configs/agent.yaml` 维持/加强以下策略：

```yaml
sources:
  google_scholar:
    enabled: false
  web:
    enabled: false
  semantic_scholar:
    enabled: true
    max_results_per_query: 5
    polite_delay_sec: 3.0
    max_retries: 1
    retry_backoff_sec: 1.5
  pdf_download:
    only_allowed_hosts: true
    forbidden_host_ttl_sec: 1800
```

如果目标是“稳定测试流程”而非“最大召回”，优先减少 query 数和 provider 数，再提高每条证据质量。

## 6. 运行后排查清单

1. 看 `outputs/run_xxx/events.log`，确认是否大量停在 `fetch_sources`。  
2. 搜索错误分布：
   - `rg -n "429|403|404|PDF download failed|Semantic Scholar|SerpAPI" outputs/run_xxx -S`
3. 对比 `research_state.json`：  
   - 是否 papers 数量增长正常；  
   - 是否只是 `pdf_path` 缺失而非条目缺失。  
4. 若 429 高发：降低 `max_queries_per_iteration`、`max_results_per_query`，或临时关闭 `google_scholar`。

## 7. 一句话结论

- `429` 本质是配额/速率问题；  
- `403` 本质是权限/反爬限制；  
- `404` 本质是链接失效；  
- “搜到但下不来 PDF”在学术爬取里是常态，正确策略是 **元数据优先 + 开放源下载 + 失败降噪**。

