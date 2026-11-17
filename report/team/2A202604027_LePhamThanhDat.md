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
  - Chạy benchmark đối chứng `single`, `single_no_llm` và `swarm` trên 14 public claim × 5 seed (`11, 22, 33, 44, 55`), lưu kết quả máy sinh tại `src/reports/ablation_r4.json`, đồng thời thu hẹp kết luận R4 đúng với phạm vi cô lập biến của dữ liệu.

## 4. Bằng chứng

- **Branch & Commit:** nhánh `feat/tv2-single-eval`, commit chính `d2aca14` (sẽ cập nhật thêm commit chốt trên `main` sau khi merge phần Thành viên 1).
- **Kết quả kiểm thử tại `src/`:**
  - `python -m lab8.smoke` → `lab8.smoke pass` (`python 3.11.9 | Windows AMD64`).
  - `python -m pytest -q` → `73 passed, 248 deselected` (gồm 54 host test gốc + 19 test mới trong `tests/test_tv2_hidden_edge_cases.py`).
  - `python -m pytest -q -m student -o addopts= -k "single and not workflow and not orchestrator and not swarm"` → `62 passed, 259 deselected`.
- **Kết quả ablation (`src/reports/ablation_r4.json`):**
  - Lệnh: `python -m lab8.benchmark --shapes single,single_no_llm,swarm --extra-shape single_no_llm=lab8.shapes.single:run_claim_no_llm --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out reports/ablation_r4.json`
  - `single`: `pass_rate = 1.000` (70/70), `pass^5 = 1.000`, `seed_variance = 0.000000`, `cost/success = 52.37 VND` (tổng `3665.78 VND`), `mean_steps = 10.14` (p95 = `13.0`), `mean_model_calls = 6.57`, `mean_tool_calls = 4.57`.
  - `single_no_llm`: `pass_rate = 1.000` (70/70), `pass^5 = 1.000`, `seed_variance = 0.000000`, `cost/success = 45.71 VND` (tổng `3200.00 VND`), `mean_steps = 9.14` (p95 = `12.0`), `mean_model_calls = 0.00`, `mean_tool_calls = 4.57`.
  - `swarm`: `pass_rate = 0.986` (69/70, fail `C-002` seed 55: `R-swarm-C-002-s55`), `pass^5 = 0.929`, `seed_variance = 0.000816`, `cost/success = 49.57 VND` (tổng `3420.12 VND`), `mean_steps = 2.80` (p95 = `3.0`), `mean_model_calls = 3.00`, `mean_tool_calls = 4.66`.

## 5. Công cụ AI đã dùng

- **Công cụ:** Antigravity AI coding assistant.
- **Mục đích sử dụng:** Rà soát kiến trúc `src/lab8/`, refactor `single.py` để `MockLLM` trực tiếp điều khiển lựa chọn read-only tool trong `decide()`, viết test kiểm tra `step_cap`/`worker=True` qua chính `single.run_claim`, và chỉnh sửa báo cáo R4 theo nhận xét phản biện.
- **Cách tự kiểm tra:** Đọc trực tiếp mã nguồn `runtime.py`, `mock_llm.py`, `durability.py`, `policy.py`, `metrics.py`, `check_submission.py`; chạy lại toàn bộ `pytest -q`, `pytest -q -m student -o addopts=`, `lab8.benchmark`, `lab8.check_submission` sau lần sửa cuối cùng để xác nhận số liệu từ `src/reports/ablation_r4.json`.

## 6. Tự đánh giá

- Đã khắc phục triệt để 3 điểm yếu từ phản biện: (1) đưa lựa chọn read-only tool của `MockLLM` vào bên trong `decide()` của vòng ReAct; (2) thu hẹp kết luận R4 đúng với phạm vi cô lập biến và bổ sung đầy đủ URL `Zhang et al., EMNLP 2026`; (3) kiểm thử `step_cap=8` và `worker=True` trực tiếp qua `single.run_claim` với khẳng định 0 refund.
- Đang chờ ghép phần `workflow.py` và `orchestrator.py` từ Thành viên 1 để chạy `reports/benchmark.json` 4 shape, `reports/crash.json` 20/20 và `python -m lab8.check_submission` đạt `0 FAIL`.
