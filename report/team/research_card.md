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
| SOURCE | Paper/blog, năm, URL, loại bằng chứng (benchmark, production report, blog kinh nghiệm) | Zhang et al., EMNLP 2026, *Rethinking Evaluation of MAS Efficiency* (https://aclanthology.org/2026.emnlp-main.798/, slide 44, 59, 68–69; loại bằng chứng: benchmark & ablation) |
| CLAIM | Một kết luận gốc của nguồn. Không viết rộng hơn phạm vi paper | Hiệu năng hoặc chi phí đo được của một hệ agent có thể đến từ cách thiết kế benchmark, quy tắc đếm bước hay các biến đồng biến (confounders) hơn là bản thân topology; cần đối chứng với baseline đơn giản trong cùng runtime, tool và tập test |
| BOUNDARY | Model / dataset / setup giới hạn kết luận đó | Trong lab này dùng `MockLLM` mô phỏng (`latency: unavailable`), `pricing.yaml` mô phỏng, `public_claims.jsonl` gồm 14 claim × 5 seed (`11,22,33,44,55`) nên không suy rộng thành hành vi model sản xuất |
| HYPOTHESIS | Nếu đổi shape A→B (hoặc bật/tắt một thành phần), metric X sẽ đổi theo hướng nào, khoảng bao nhiêu | Khi giữ cố định vòng ReAct (`max_steps=8`, `worker=True`), tập `READONLY_TOOLS`, host gate, corpus và seed: chuyển từ `single` (gọi `MockLLM` mỗi bước để parse/chọn thứ tự read tool/draft) sang `single_no_llm` (bộ chọn thứ tự cố định, 0 model call) giữ nguyên `pass_rate = 1.000` và `mean_tool_calls`, nhưng giảm `cost/success` (~6–7 VND) và giảm `mean_steps` (-1 trace event); so `single` với `swarm` giúp xác định lỗi seed 55 đến từ việc ghi đè `delay_days` từ ticket chứ chưa cô lập thuần túy topology |
| METHOD | Biến giữ cố định: model, tools, seed, corpus, giá, evaluator. Biến duy nhất được thay đổi: … | Cố định `data/public_claims.jsonl` (14 claim), `data/public_world_state.json`, `seeds=[11,22,33,44,55]`, `as_of=2026-11-15`, `MockLLM`, `config/pricing.yaml`, `durability.issue_refund`, `lab8.metrics`. Phép ablation kiểm soát 1 biến: bật/tắt `MockLLM` trong cùng vòng `run_react` (`single` vs `single_no_llm`); và đối chiếu tham khảo với `swarm` (lưu ý `single ↔ swarm` khác đồng thời nhiều biến: topology, chuỗi tool, số model call và quy tắc dùng ticket) |
| FAILURE / METRIC | Một lỗi dự kiến và cách đo nó: pass rate, pass^5, variance, cost/success, leak, bypass | Đo `pass_rate`, `pass^5`, `seed_variance`, `cost_per_success_vnd`, `mean_model_calls`, `mean_tool_calls` và `mean_steps`; kiểm chứng giả thuyết confounder ở metric `mean_steps` (số trace event ≠ số tool/model call thực tế) và lỗi `status resolved != denied` của `swarm` trên `C-002` seed 55 |

## Kết quả ablation

- Lệnh đã chạy (copy nguyên văn): `python -m lab8.benchmark --shapes single,single_no_llm,swarm --extra-shape single_no_llm=lab8.shapes.single:run_claim_no_llm --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out reports/ablation_r4.json`
- Run id / file report: `src/reports/ablation_r4.json` (ví dụ trial đối chứng: `R-single-C-002-s55`, `R-single_no_llm-C-002-s55`, `R-swarm-C-002-s55`)
- Kết quả so với hypothesis (đúng / sai / không kết luận được), kèm số liệu: **Đúng với giả thuyết đã thu hẹp phạm vi.** Trên 70 trial/shape (`14 claims × 5 seeds`):
  - `single`: `pass_rate = 1.000` (70/70), `pass^5 = 1.000`, `seed_variance = 0.000000`, `cost/success = 52.37 VND` (tổng 3665.78 VND), `mean_steps = 10.14` (p95 = 13.0), `mean_model_calls = 6.57`, `mean_tool_calls = 4.57`.
  - `single_no_llm`: `pass_rate = 1.000` (70/70), `pass^5 = 1.000`, `seed_variance = 0.000000`, `cost/success = 45.71 VND` (tổng 3200.00 VND), `mean_steps = 9.14` (p95 = 12.0), `mean_model_calls = 0.00`, `mean_tool_calls = 4.57`.
  - `swarm`: `pass_rate = 0.986` (69/70, fail `C-002` ở seed 55: `status resolved != denied`), `pass^5 = 0.929`, `seed_variance = 0.000816` (min `0.929`, max `1.000`), `cost/success = 49.57 VND` (tổng 3420.12 VND), `mean_steps = 2.80` (p95 = 3.0), `mean_model_calls = 3.00`, `mean_tool_calls = 4.66`.
  - **Kết luận thu hẹp đúng theo dữ liệu:**
    1. Cặp `single ↔ single_no_llm` cô lập được **chi phí biên của việc dùng `MockLLM` trong vòng ReAct**: cùng `mean_tool_calls = 4.57` và cùng `pass_rate = 1.000`, việc gọi `MockLLM` ở từng bước ReAct làm tăng `mean_model_calls` từ `0` lên `6.57` và tăng `cost/success` từ `45.71` lên `52.37 VND` (+`6.66 VND`/lần thành công).
    2. Cặp `single ↔ swarm` **không cô lập được tác động thuần túy của topology** vì hai triển khai khác đồng thời topology, chuỗi tool, tần suất gọi model (khiến `single` đắt hơn `swarm`: `52.37` vs `49.57 VND`) và quy tắc xử lý ticket. Tuy vậy, dữ liệu xác nhận lỗi `C-002` seed 55 của `swarm` bắt nguồn từ nhánh cho phép model ghi đè `delay_days` từ ticket, đồng thời chứng minh `mean_steps` trong trace là confounder (`swarm` 2.80 vs `single` 10.14 dù `swarm` gọi nhiều `tool_calls` hơn: 4.66 vs 4.57). Muốn kết luận riêng về topology (A/B/C/D) cần ghép đủ `workflow` và `orchestrator` trên cùng quy ước trace.
- Giới hạn: MockLLM không phải model sản xuất, latency là `unavailable`, tập public chỉ gồm 14 claim nên cần đối chiếu thêm khi ghép đủ 4 shape (`workflow`, `single`, `orchestrator`, `swarm`) trên bộ đầy đủ và hidden 40 claim.

Muốn đi xa hơn một ablation để lấy điểm cộng thì xem [docs/bonus_topics.md](../../docs/bonus_topics.md).
