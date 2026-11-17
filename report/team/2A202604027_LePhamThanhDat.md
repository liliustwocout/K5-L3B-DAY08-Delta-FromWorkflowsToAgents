# Báo cáo cá nhân — 2A202604027_LePhamThanhDat

## 1. Thông tin thành viên

- Họ tên: Lê Phạm Thành Đạt
- MSSV: 2A202604027
- Email: datpltn205@gmail.com
- GitHub: liliustwocout

## 2. Phần việc phụ trách

- Thiết lập môi trường Python `.venv` tại `src/`, kiểm tra baseline `lab8.smoke` và cổng host `pytest -q`.
- Triển khai hoàn chỉnh Shape B — Bounded Single ReAct Agent tại `src/lab8/shapes/single.py` (kèm biến thể ablation `run_claim_no_llm` để thử nghiệm R4).
- Xây dựng bộ test phòng thủ edge-case kiểu hidden tại `src/tests/test_tv2_hidden_edge_cases.py`.
- Thiết kế và chạy thực nghiệm ablation R4, hoàn thiện `report/team/research_card.md` (trích dẫn đầy đủ Zhang et al., EMNLP 2026) và đồng viết các mục liên quan trong `report/team/group_report.md`.

## 3. Đóng góp cụ thể

- **`src/lab8/shapes/single.py`:**
  - Cài đặt `run_claim(claim_id, *, seed, store_path, crash_at=None) -> RunResult` dùng `lab8.runtime.run_react(..., max_steps=8, worker=True)`.
  - Đưa toàn bộ lời gọi `MockLLM.complete` (`parse`, `react_step`, `draft`) vào **bên trong** `decide(obs)` của vòng ReAct: ở mỗi bước, model nhận trạng thái an toàn và danh sách read-only `candidates`, trả về chỉ thị (`tool=...`/`final=...`) hoặc digest để chọn thứ tự gọi `lookup_policy`, `lookup_refund_history`, `get_clause` (khi ticket trích dẫn điều khoản), rồi `compute_compensation`.
  - Thiết kế closure `state` để tích lũy `order_view`, `policy_loaded`, `refund_history`, `checked_clause` và `quote` qua các bước của `run_react`.
  - Bắt `ToolRejected` từ `run_react(..., worker=True)` khi model chọn write tool và xử lý `step_cap` (`max_steps=8`) trả về `status="failed"` với 0 refund; truyền **quote đầy đủ** vào `durability.issue_refund`, re-raise `InjectedCrash` sau khi flush trace `crash`, đóng SQLite connection trong `finally`, và trả `RunResult` qua `lab8.shapes.common.finish()`.
- **`src/tests/test_tv2_hidden_edge_cases.py`:**
  - Viết mới 19 test cases kiểm tra: ticket khai gian kết hợp Unicode tổ hợp (`tre\u0303`) & prompt injection trên cả 5 seed; đơn `cancelled`/`in_transit`; thiếu `order_id` nhưng ticket có nhắc mã đơn; policy hết hiệu lực (`POL-2025-01`) & policy tương lai (`POL-2027-03`); stacking rule (`max`); approval của claim khác / `revoked` / hết hạn / `NULL`; `unknown_claim` và chống rò PII/canary khi `escalated`; cả 3 mốc crash (`before_effect`, `after_effect_before_checkpoint`, `after_checkpoint`); `amount_conflict`; kiểm thử `step_cap=8` và chặn `issue_refund` (`worker=True`) **trực tiếp qua `single.run_claim`** xác nhận 0 refund; kiểm tra `MockLLM` thực sự làm biến đổi thứ tự chọn read tool theo seed; trần hoàn tiền nối tiếp & partial approval; và ablation `single_no_llm`.
- **Thực nghiệm ablation R4 (`report/team/research_card.md`):**
  - Chạy benchmark đối chứng `single`, `single_no_llm` và `swarm` trên 14 public claim × 5 seed (`11, 22, 33, 44, 55`), lưu kết quả máy sinh tại `src/reports/ablation_r4.json`, đồng thời đối chiếu với `src/reports/benchmark.json` (4 shape sau merge) và thu hẹp kết luận R4 đúng với phạm vi cô lập biến của dữ liệu.

## 4. Bằng chứng

- **Branch & Commit:** nhánh `feat/tv2-single-eval`, commit chính `d2aca14` (implementation + 19 test + ablation R4) và `1eec41a`, đã merge vào `main` qua PR #1 (`e98e9de`) và đồng bộ cùng phần Thành viên 1 qua PR #2 (`9b2d6d5`).
- **Kết quả kiểm thử trên `main` (chạy trong `src/`):**
  - `python -m lab8.smoke` → `lab8.smoke pass` (`python 3.11.9 | Windows AMD64`).
  - `python -m pytest -q` → **`90 passed, 248 deselected`** (gồm 54 host test gốc + 19 test mới của TV2 trong `tests/test_tv2_hidden_edge_cases.py` + 17 test mới của TV1 trong `tests/test_workflow_orchestrator.py`).
  - `python -m pytest -q -m student -o addopts=` → **`248 passed, 90 deselected`** (cả 3 shape nhóm viết gồm `workflow`, `single`, `orchestrator` đều đạt `62/62`; riêng `single` đạt `62/62` trên T01–T14).
  - `python -m lab8.check_submission` → **`0 FAIL, 0 WARN`**.
- **Kết quả đo hiệu năng (`src/reports/ablation_r4.json` và `src/reports/benchmark.json`):**
  - Lệnh ablation: `python -m lab8.benchmark --shapes single,single_no_llm,swarm --extra-shape single_no_llm=lab8.shapes.single:run_claim_no_llm --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out reports/ablation_r4.json`
  - `single`: `pass_rate = 1.000` (70/70), `pass^5 = 1.000`, `seed_variance = 0.000000`, `cost/success = 52.37 VND` (tổng `3665.78 VND`), `mean_steps = 10.14` (p95 = `13.0`), `mean_model_calls = 6.57`, `mean_tool_calls = 4.57`.
  - `single_no_llm`: `pass_rate = 1.000` (70/70), `pass^5 = 1.000`, `seed_variance = 0.000000`, `cost/success = 45.71 VND` (tổng `3200.00 VND`), `mean_steps = 9.14` (p95 = `12.0`), `mean_model_calls = 0.00`, `mean_tool_calls = 4.57`.
  - `workflow` (từ `src/reports/benchmark.json`): `pass_rate = 1.000`, `pass^5 = 1.000`, `cost/success = 28.89 VND`, `mean_steps = 3.79`; `orchestrator`: `pass_rate = 1.000`, `cost/success = 57.18 VND`, `mean_steps = 4.71`; `swarm`: `pass_rate = 0.986` (69/70, fail `C-002` seed 55: `R-swarm-C-002-s55`), `pass^5 = 0.929`, `seed_variance = 0.000816`, `cost/success = 49.57 VND`, `mean_steps = 2.80`.

## 5. Công cụ AI đã dùng

- **Công cụ:** Antigravity AI coding assistant.
- **Mục đích sử dụng:** Rà soát kiến trúc `src/lab8/`, refactor `single.py` để `MockLLM` trực tiếp điều khiển lựa chọn read-only tool trong `decide()`, viết test kiểm tra `step_cap`/`worker=True` qua chính `single.run_claim`, và chỉnh sửa báo cáo R4 theo nhận xét phản biện.
- **Cách tự kiểm tra:** Đọc trực tiếp mã nguồn `runtime.py`, `mock_llm.py`, `durability.py`, `policy.py`, `metrics.py`, `check_submission.py`; chạy lại toàn bộ `pytest -q`, `pytest -q -m student -o addopts=`, `lab8.benchmark`, `lab8.check_submission` trên `main` sau khi đã ghép đầy đủ code của cả hai thành viên để đối chiếu số liệu từ `src/reports/ablation_r4.json` và `src/reports/benchmark.json`.

## 6. Tự đánh giá

- Đã hoàn thiện trọn vẹn phần Shape B (`single.py`), 19 test edge-case kiểu hidden, thí nghiệm ablation R4 và tài liệu nghiên cứu; đồng thời đã ghép đồng bộ với phần `workflow.py`, `orchestrator.py`, `benchmark.json` (4 shape) và `crash.json` (`20/20`) của Thành viên 1 trên `main`.
- Tất cả cổng kiểm tra sau tích hợp đều xanh (`90 passed` host/team tests, `248 passed` student matrix, `check_submission` `0 FAIL`), đảm bảo bài nộp sẵn sàng cho chấm điểm tự động và bảo vệ.
