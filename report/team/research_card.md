# Research card

File này nằm cố định ở `report/team/research_card.md`; `python -m lab8.check_submission` đọc cột "Nhóm điền" bằng máy.

Phần này nối tiếp phần mini research ở buổi lý thuyết (slide 62–63). Chọn **một** câu R1–R4, điền 6 dòng, rồi biến nó thành **một ablation** chạy được trong lab: giữ nguyên model (MockLLM), tool, seed, corpus và giá, chỉ thay đổi một biến.

| Câu | Nguồn (thư viện tham khảo, slide 68–69) | Câu hỏi gợi ý cho lab |
| --- | --- | --- |
| R1 · Scaling | Google Research 2026, *Towards a Science of Scaling Agent Systems* | Task claims chủ yếu tuần tự hay song song được? Dự đoán thêm investigator sẽ làm pass rate và cost/success thay đổi thế nào. |
| R2 · Failure taxonomy | MAST, NeurIPS 2025, *Why Do Multi-Agent LLM Systems Fail?* | Các trial fail của swarm (seed 55) thuộc nhóm nào: lỗi giao việc, lệch mục tiêu, hay lỗi kiểm chứng? |
| R3 · Architecture choices | AgentArch, AACL 2026 | Nếu đổi topology mà giữ nguyên mọi thứ khác, biến nào phải cố định để kết luận còn đúng? |
| R4 · Evaluation confounders | EMNLP 2026, *Rethinking Evaluation of MAS Efficiency* | Làm sao chứng minh chênh lệch giữa A/B/C/D là do topology, không phải do prompt, tool hay seed? |

## Phiếu của nhóm

Điền vào cột cuối. Không xóa hai cột đầu.

| Field | Hướng dẫn | Nhóm điền |
| --- | --- | --- |
| CÂU | R1 / R2 / R3 / R4 | R4 |
| SOURCE | Paper/blog, năm, URL, loại bằng chứng (benchmark, production report, blog kinh nghiệm) | Zhang, J., Zhang, L., Lu, P., Zhang, Q., Chuang, Y.-N., Li, Z., Xu, S., Chaudhary, V., & Chen, H. (2026), *"Rethinking the Evaluation of Efficiency Methods for Multi-Agent Systems"*, Proceedings of EMNLP 2026, pp. 18527–18562 · ACL Anthology: https://aclanthology.org/2026.emnlp-main.798/ · DOI: 10.18653/2026.emnlp-main.798 · arXiv: https://arxiv.org/abs/2609.05933 (loại bằng chứng: benchmark & ablation) |
| CLAIM | Một kết luận gốc của nguồn. Không viết rộng hơn phạm vi paper | Hiệu năng hoặc chi phí đo được của một hệ agent có thể đến từ cách thiết kế benchmark, quy tắc đếm bước hay các biến đồng biến (confounders) hơn là bản thân topology; cần đối chứng với baseline đơn giản trong cùng runtime, tool và tập test |
| BOUNDARY | Model / dataset / setup giới hạn kết luận đó | Trong lab này dùng `MockLLM` mô phỏng (`latency: unavailable`), `pricing.yaml` mô phỏng, `public_claims.jsonl` gồm 14 claim × 5 seed (`11,22,33,44,55`) nên không suy rộng thành hành vi model sản xuất |
| HYPOTHESIS | Nếu đổi shape A→B (hoặc bật/tắt một thành phần), metric X sẽ đổi theo hướng nào, khoảng bao nhiêu | Khi giữ cố định vòng ReAct (`max_steps=8`, `worker=True`), tập `READONLY_TOOLS`, host gate, corpus và seed: chuyển từ `single` (gọi `MockLLM` mỗi bước để parse/chọn thứ tự read tool/draft) sang `single_no_llm` (bộ chọn thứ tự cố định, 0 model call) giữ nguyên `pass_rate = 1.000` và `mean_tool_calls`, nhưng giảm `cost/success` (~6–7 VND) và giảm `mean_steps` (-1 trace event); khi đối chiếu 4 shape (`workflow`, `single`, `orchestrator`, `swarm`), các shape khóa quyết định bằng code đều đạt `pass_rate = 1.000` và chi phí tăng theo số tool/model call, trong khi lỗi `swarm` seed 55 đến từ việc ghi đè `delay_days` từ ticket |
| METHOD | Biến giữ cố định: model, tools, seed, corpus, giá, evaluator. Biến duy nhất được thay đổi: … | Cố định `data/public_claims.jsonl` (14 claim), `data/public_world_state.json`, `seeds=[11,22,33,44,55]`, `as_of=2026-11-15`, `MockLLM`, `config/pricing.yaml`, `durability.issue_refund`, `lab8.metrics`. Phép ablation kiểm soát 1 biến: bật/tắt `MockLLM` trong cùng vòng `run_react` (`single` vs `single_no_llm` trong `ablation_r4.json`); và đối chiếu đủ 4 shape (`workflow`, `single`, `orchestrator`, `swarm`) trong `benchmark.json` (lưu ý `swarm` khác cả quy tắc ghi đè ticket và mật độ ghi trace event) |
| FAILURE / METRIC | Một lỗi dự kiến và cách đo nó: pass rate, pass^5, variance, cost/success, leak, bypass | Đo `pass_rate`, `pass^5`, `seed_variance`, `cost_per_success_vnd`, `mean_model_calls`, `mean_tool_calls` và `mean_steps`; kiểm chứng giả thuyết confounder ở metric `mean_steps` (số trace event ≠ số tool/model call thực tế) và lỗi `status resolved != denied` của `swarm` trên `C-002` seed 55 |

## Kết quả ablation

- Lệnh đã chạy (copy nguyên văn):
  - Ablation 1 biến: `python -m lab8.benchmark --shapes single,single_no_llm,swarm --extra-shape single_no_llm=lab8.shapes.single:run_claim_no_llm --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out reports/ablation_r4.json`
  - Benchmark 4 shape: `python -m lab8.benchmark --shapes workflow,single,orchestrator,swarm --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out reports/benchmark.json`
- Run id / file report: `src/reports/ablation_r4.json` và `src/reports/benchmark.json` (ví dụ trial đối chứng: `R-workflow-C-001-s11`, `R-single-C-002-s55`, `R-single_no_llm-C-002-s55`, `R-orchestrator-C-001-s11`, `R-swarm-C-002-s55`)
- Kết quả so với hypothesis (đúng / sai / không kết luận được), kèm số liệu: **Đúng với giả thuyết đã thu hẹp phạm vi.** Trên 70 trial/shape (`14 claims × 5 seeds`):
  - `workflow` (`benchmark.json`): `pass_rate = 1.000` (70/70), `pass^5 = 1.000`, `seed_variance = 0.000000`, `cost/success = 28.89 VND` (tổng 2022.10 VND), `mean_steps = 3.79` (p95 = 4.0), `mean_model_calls = 1.00`, `mean_tool_calls = 2.79`.
  - `single` (`benchmark.json` & `ablation_r4.json`): `pass_rate = 1.000` (70/70), `pass^5 = 1.000`, `seed_variance = 0.000000`, `cost/success = 52.37 VND` (tổng 3665.78 VND), `mean_steps = 10.14` (p95 = 13.0), `mean_model_calls = 6.57`, `mean_tool_calls = 4.57`.
  - `single_no_llm` (`ablation_r4.json`): `pass_rate = 1.000` (70/70), `pass^5 = 1.000`, `seed_variance = 0.000000`, `cost/success = 45.71 VND` (tổng 3200.00 VND), `mean_steps = 9.14` (p95 = 12.0), `mean_model_calls = 0.00`, `mean_tool_calls = 4.57`.
  - `orchestrator` (`benchmark.json`): `pass_rate = 1.000` (70/70), `pass^5 = 1.000`, `seed_variance = 0.000000`, `cost/success = 57.18 VND` (tổng 4002.90 VND), `mean_steps = 4.71` (p95 = 5.0), `mean_model_calls = 2.00`, `mean_tool_calls = 5.57`.
  - `swarm` (`benchmark.json` & `ablation_r4.json`): `pass_rate = 0.986` (69/70, fail `C-002` ở seed 55: `status resolved != denied`), `pass^5 = 0.929`, `seed_variance = 0.000816` (min `0.929`, max `1.000`), `cost/success = 49.57 VND` (tổng 3420.12 VND), `mean_steps = 2.80` (p95 = 3.0), `mean_model_calls = 3.00`, `mean_tool_calls = 4.66`.
  - **Kết luận thu hẹp đúng theo dữ liệu:**
    1. Cặp `single ↔ single_no_llm` cô lập được **chi phí biên của việc dùng `MockLLM` trong vòng ReAct**: cùng `mean_tool_calls = 4.57` và cùng `pass_rate = 1.000`, việc gọi `MockLLM` ở từng bước ReAct làm tăng `mean_model_calls` từ `0` lên `6.57` và tăng `cost/success` từ `45.71` lên `52.37 VND` (+`6.66 VND`/lần thành công).
    2. Sau khi ghép đủ 3 shape khóa quyết định bằng code (`workflow`, `single`, `orchestrator`), cả 3 đều đạt `1.000 / 1.000` (`seed_variance = 0.000000`), trong đó chi phí tăng theo số lần gọi model & tool: `workflow` (`28.89 VND`) → `single` (`52.37 VND`) → `orchestrator` (`57.18 VND`). Trong khi đó `swarm` có `mean_steps = 2.80` thấp nhất dù gọi nhiều model/tool (`3.00` / `4.66`) hơn `workflow` (`1.00` / `2.79`), chứng minh `mean_steps` trong trace là confounder do mật độ ghi event khác nhau giữa các shape, đồng thời xác nhận lỗi `C-002` seed 55 của `swarm` bắt nguồn từ nhánh cho phép model ghi đè `delay_days` từ ticket.
- Giới hạn: MockLLM không phải model sản xuất, latency là `unavailable`, giá token tính theo `config/pricing.yaml` mô phỏng, và tập public chỉ gồm 14 claim (chưa có nhãn hidden 40 claim trên máy học viên).

Muốn đi xa hơn một ablation để lấy điểm cộng thì xem [docs/bonus_topics.md](../../docs/bonus_topics.md).
