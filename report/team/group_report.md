# Báo cáo nhóm — Lab 8 LogiX-VN

Tối đa 5 trang ngoài phụ lục. Số liệu lấy từ file trong `src/reports/`, không chép tay từ terminal.

## 1. Thông tin nhóm

- Tên nhóm: Delta (Lớp L3B)
- Thành viên: xem `TEAM.md`
- Commit chốt (trùng `report/team/decision_adr.md`): `[Thành viên 1 cập nhật sau khi merge và chốt commit trên main]`

## 2. Mục tiêu và cách tiếp cận

Bài lab xử lý bài toán bồi thường/hoàn phí vận chuyển giả lập của LogiX-VN trên cùng một hợp đồng dữ liệu (`RunResult`, `trace.v1`, SQLite ledger) nhưng triển khai qua bốn kiến trúc với mức tự chủ tăng dần: `workflow` (A), `single` (B), `orchestrator` (C) và `swarm` (D, có sẵn làm đối chứng). Nguyên tắc thiết kế cốt lõi là tách bạch ranh giới **code quyết định tiền, quyền sở hữu, approval và idempotency**, còn model chỉ đọc/soạn chữ; mọi nội dung trong `ticket` là dữ liệu người dùng không đáng tin.

Nhóm 2 người chia việc song song theo hai nhánh độc lập để tránh xung đột file:
- Thành viên 1 phụ trách `workflow.py`, `orchestrator.py`, test cho `workflow`/`orchestrator`/`handoff`, chạy `crash_test` + `benchmark` tổng hợp, viết `TEAM.md` và `decision_adr.md`.
- Thành viên 2 (Lê Phạm Thành Đạt) phụ trách `single.py` (bounded ReAct `max_steps=8`), bộ test edge-case kiểu hidden (`src/tests/test_tv2_hidden_edge_cases.py`), thí nghiệm ablation & `research_card.md`, và tổng hợp phân tích phần `single` trong báo cáo nhóm.

## 3. Giải pháp

### Shape A — Deterministic Workflow (`src/lab8/shapes/workflow.py`)
`[Thành viên 1 điền chi tiết triển khai workflow sau khi merge]`

### Shape B — Bounded Single ReAct Agent (`src/lab8/shapes/single.py`)
- **Đọc dữ liệu có kiểm soát:** Mở SQLite qua `lab8.db.connect(store_path)` (đảm bảo `conn.close()` trong `finally`), đọc claim qua `get_claim_view` (loại bỏ `parent_secret` và `raw_headers_json`). Nếu không tìm thấy claim → trả `failed` (`unknown_claim`).
- **Model chọn tool thực sự bên trong vòng ReAct (`max_steps=8`, `worker=True`):** Dùng `lab8.runtime.run_react`. Ở mỗi bước bên trong `decide(obs)`:
  1. Bước đầu tiên gọi `MockLLM.complete(..., purpose="parse")` để đọc nội dung ticket và ghi `react_thought` (không dùng số ngày parse được để ghi đè DB).
  2. Xây dựng prompt tóm tắt trạng thái an toàn (không secret/PII) kèm danh sách các read-only tool hợp lệ còn lại (`candidates`), gọi `MockLLM.complete(..., purpose="react_step")` để model chọn hành động: hỗ trợ cả chỉ thị tường minh (`tool=...` / `final=...`) lẫn lựa chọn trong `candidates` theo digest của `MockLLM` (làm thay đổi thứ tự gọi giữa `lookup_policy`, `lookup_refund_history`, và `get_clause` khi ticket có trích dẫn điều khoản như `SHIP-LATE-OLD`).
  3. Vì `run_react` chỉ giữ `last_tool`, `last_result`, `claim` trong `observation` của bước tiếp theo, `decide` dùng closure `state` để tích lũy `order_view`, `policy_loaded`, `refund_history`, `checked_clause` và `quote`.
  4. Do `worker=True`, mọi nỗ lực chọn write tool (`issue_refund`, `append_audit`) đều bị `dispatch` chặn bằng `ToolRejected` (bắt gọn về `status="failed"`, `error_reason="tool_rejected"`, không ghi refund); nếu lặp quá `max_steps=8` sẽ dừng ở `step_cap` (`status="failed"`, `error_reason="step_cap"`, 0 refund).
- **Cổng ghi Host & Trace v1:** Khi `proposal > 0`, shape truyền **quote đầy đủ** vào `durability.issue_refund(conn, claim_id, proposal, crash_at=crash_at)` để host kiểm tra approval gắn đúng `claim_id`, trừ phần đã hoàn trước đó trên cùng đơn, và ghi `refund_ledger` + `refund_committed` trong cùng một transaction. `InjectedCrash` được ghi sự kiện `crash` vào trace, flush file và `raise` lại nguyên trạng. Mọi nhánh return đều đi qua `lab8.shapes.common.finish()`.

### Shape C — Orchestrator & Read-Only Investigators (`src/lab8/shapes/orchestrator.py`)
`[Thành viên 1 điền chi tiết triển khai orchestrator và cơ chế sanitize handoff.v1 sau khi merge]`

## 4. Kết quả

Số liệu sơ bộ từ `src/reports/ablation_r4.json` cho phần `single` (đã hoàn thành) và đối chứng `swarm` trên 14 public claims × 5 seeds (`11, 22, 33, 44, 55`, 70 trial/shape). `[Thành viên 1 bổ sung đầy đủ 4 shape workflow, single, orchestrator, swarm từ src/reports/benchmark.json và crash_safety từ src/reports/crash.json sau khi merge]`:

| Shape | Pass rate | Pass^5 | Seed min–max | Seed variance | Cost/success (VND mô phỏng) | Mean / p95 steps | Ghi chú |
| --- | ---: | ---: | --- | ---: | ---: | --- | --- |
| `workflow` | `[Chờ TV1]` | `[Chờ TV1]` | `[Chờ TV1]` | `[Chờ TV1]` | `[Chờ TV1]` | `[Chờ TV1]` | |
| `single` | `1.000` (70/70) | `1.000` | `1.000`–`1.000` | `0.000000` | `52.37` | `10.14` / `13.0` | `mean_model_calls=6.57`, `mean_tool_calls=4.57` |
| `single_no_llm` *(ablation)* | `1.000` (70/70) | `1.000` | `1.000`–`1.000` | `0.000000` | `45.71` | `9.14` / `12.0` | `mean_model_calls=0.00`, `mean_tool_calls=4.57` |
| `orchestrator` | `[Chờ TV1]` | `[Chờ TV1]` | `[Chờ TV1]` | `[Chờ TV1]` | `[Chờ TV1]` | `[Chờ TV1]` | |
| `swarm` *(đối chứng)* | `0.986` (69/70) | `0.929` | `0.929`–`1.000` | `0.000816` | `49.57` | `2.80` / `3.0` | Fail `C-002` seed 55 (`status resolved != denied`) |

Quyết định kiến trúc và lý do: xem `report/team/decision_adr.md`. Phiếu nghiên cứu và ablation: xem `report/team/research_card.md`.

## 5. Khó khăn và cách xử lý

1. **Cơ chế truyền ngữ cảnh trong `run_react` (`src/lab8/runtime.py`):** Ở mỗi vòng lặp, `run_react` ghi đè `seen = {"last_tool": name, "last_result": result, "claim": observation.get("claim")}`, không giữ lịch sử các tool đã gọi trước đó. Ban đầu dễ bị mất `order_view` khi chuyển sang bước `compute_compensation`. **Cách xử lý:** dùng closure `state` trong `single.py` để lưu `order_view`, `policy_count`, `refund_history` và `quote` qua từng bước, kết hợp kiểm tra bằng bộ test ReAct.
2. **Thiết kế test `amount_conflict` và test nối tiếp trên cùng SQLite (`src/tests/test_tv2_hidden_edge_cases.py`):**
   - Khi thử kích hoạt `amount_conflict` trên `C-001` bằng cách bật `damage_verified = 1` (quote tăng lên `150.000`), `policy.authorize` vẫn chặn số tiền được duyệt ở mức `approved_vnd = 35.000` nên không sinh conflict. Đổi kịch bản test sang thay đổi `shipping_fee_vnd = 20.000 <= approved_vnd` thì host bắt đúng `amount_conflict` và giữ nguyên `35.000` trong ledger.
   - Khi chạy nhiều claim nối tiếp trên cùng file SQLite, `trial_pass` dùng `unexpected_ledger_rows` (chỉ tính `prior_refund_rows` được seed từ đầu) nên báo lỗi nếu chấm từng claim giữa chuỗi. Nhóm xử lý bằng cách kiểm tra trực tiếp `refund_ledger`, `audit_events` (`policy_denied`) và `check_trace` cho kịch bản đa claim nối tiếp, đồng thời giữ `trial_pass` cho bài test một claim/DB.
3. `[Thành viên 1 bổ sung thêm khó khăn gặp phải nếu có]`

## 6. Tổng hợp đóng góp

Chi tiết đóng góp của từng thành viên nằm trong `TEAM.md` (bảng đóng góp) và báo cáo cá nhân `report/team/MSSV_HoTen.md` (của Thành viên 2 là `report/team/2A202604027_LePhamThanhDat.md`).

## 7. Hạn chế và hướng cải thiện

- **Giới hạn của môi trường mô phỏng:** `MockLLM` không phải model ngôn ngữ thật và sinh câu chữ dựa trên SHA-256 hash theo `seed`, vì vậy không phản ánh hết rủi ro hallucination tự nhiên hoặc lỗi phân tích ngữ nghĩa phức tạp ngoài mẫu câu `tre <N> ngay`. Giá token tính bằng VND mô phỏng theo `config/pricing.yaml` (không phải hóa đơn API thật) và `latency` để `unavailable`.
- **Giới hạn quy mô dữ liệu & đo bước:** Bộ public chỉ có 14 claim. Ngoài ra, chỉ số `mean_steps` phụ thuộc vào số event do shape chủ động ghi vào trace JSON (ví dụ `swarm` ghi ít event trace hơn nên `mean_steps = 2.8` dù gọi nhiều `model_calls` và `tool_calls` hơn `single` với `mean_steps = 10.0`).
- **Hướng cải thiện khi đưa ra production:** Cần thay `MockLLM` bằng model thật kèm đánh giá latency đầu-cuối, bổ sung bộ test ngữ nghĩa tự nhiên cho việc rút trích thông tin hỗ trợ (vẫn khóa mọi tính toán tiền tệ, quyền sở hữu, approval và ledger idempotency ở tầng code deterministic), và giữ cơ chế outbox/reconciliation nếu kết nối cổng thanh toán ngoài.

## 8. Tài liệu tham khảo

...
