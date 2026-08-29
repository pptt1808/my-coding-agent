# BigCodeBench 基准结果（30 题子集）

> 环境：本机 Python 3.14 + DeepSeek flash/pro（OpenAI 兼容网关）。数据：`bigcode/bigcodebench` v0.1.4，**只保留纯标准库**题目（避免 numpy/pandas 等重依赖在本机装不上）。运行方式：`python tools/run_bigcodebench.py --limit 30`（可断点续跑，结果落盘 `swe_work/bcb/results.jsonl`）。

## 汇总
| 指标 | 值 |
|---|---|
| 题目数 | 30 |
| **通过（PASS）** | **12 / 30 = 40%** |
| 平均耗时 | 25.4 s / 题 |
| 平均 tokens | 20,497 / 题（flash 档，`max_steps=10` 限步） |
| LLM-judge rubric（正确性/质量/整体） | 4.67 / 4.50 / 4.63 |
| 总耗时 | ~15 分钟 |

## 逐题
| task | pass | s | tokens |
|---|---|---|---|
| bcb-BigCodeBench/365 | FAIL | 15.6 | 8,664 |
| bcb-BigCodeBench/1098 | PASS | 12.8 | 11,450 |
| bcb-BigCodeBench/833 | FAIL | 19.9 | 24,951 |
| bcb-BigCodeBench/644 | FAIL | 20.1 | 19,238 |
| bcb-BigCodeBench/682 | FAIL | 23.2 | 18,924 |
| bcb-BigCodeBench/1117 | PASS | 22.3 | 19,525 |
| bcb-BigCodeBench/778 | FAIL | 10.7 | 13,004 |
| bcb-BigCodeBench/716 | FAIL | 9.4 | 8,958 |
| bcb-BigCodeBench/930 | PASS | 27.5 | 32,296 |
| bcb-BigCodeBench/342 | PASS | 19.6 | 23,389 |
| bcb-BigCodeBench/892 | FAIL | 122.8 | 62,068 |
| bcb-BigCodeBench/733 | PASS | 26.7 | 14,668 |
| bcb-BigCodeBench/740 | PASS | 12.1 | 11,355 |
| bcb-BigCodeBench/384 | FAIL | 28.5 | 24,113 |
| bcb-BigCodeBench/1041 | FAIL | 18.7 | 21,375 |
| bcb-BigCodeBench/287 | FAIL | 17.4 | 12,559 |
| bcb-BigCodeBench/1111 | PASS | 21.9 | 16,746 |
| bcb-BigCodeBench/753 | PASS | 56.0 | 44,981 |
| bcb-BigCodeBench/818 | FAIL | 7.8 | 6,998 |
| bcb-BigCodeBench/333 | PASS | 9.1 | 9,687 |
| bcb-BigCodeBench/1038 | FAIL | 34.1 | 28,644 |
| bcb-BigCodeBench/1 | FAIL | 26.3 | 31,351 |
| bcb-BigCodeBench/766 | PASS | 36.8 | 42,787 |
| bcb-BigCodeBench/848 | FAIL | 20.5 | 17,199 |
| bcb-BigCodeBench/295 | FAIL | 11.4 | 8,823 |
| bcb-BigCodeBench/954 | FAIL | 58.5 | 36,725 |
| bcb-BigCodeBench/1099 | FAIL | 46.1 | 17,351 |
| bcb-BigCodeBench/860 | PASS | 8.3 | 9,861 |
| bcb-BigCodeBench/937 | PASS | 7.6 | 7,754 |
| bcb-BigCodeBench/202 | FAIL | 11.4 | 9,468 |

## 判分口径（重要）
- 对 BigCodeBench 这类**隐藏测试**基准，**测试 PASS/FAIL 是权威判分**；
- LLM-judge 的 "correctness" 不可信——它只看 diff、看不到隐藏测试结果，**连 FAIL 的题也常打 5.0**（本次 rubric 均值 4.6 明显虚高）。因此这里**只以测试 PASS/FAIL 为准**，judge 分仅供参考/作质量维度。

## 控制与鲁棒性
- **成本控制**：flash 便宜档 + `max_steps=10`；此前某题曾一次烧 **417k tokens**，限步后降到 ~8.7k；
- **网络鲁棒**：LLM 客户端加 **API 重试**（连接错误/超时/限流自动重试，3 次）；运行器**可断点续跑**（每题落盘，重启跳过已完成）——本次 30 题在多次网络波动下仍完整跑完。
