# Báo cáo nhóm — Lab 8 LogiX-VN

Tối đa 5 trang ngoài phụ lục. Số liệu lấy từ file trong `src/reports/`, không chép tay từ terminal.

## 1. Thông tin nhóm

- Tên nhóm: Delta (Lớp L3B)
- Thành viên: xem `TEAM.md`
- Commit chốt (trùng `report/team/decision_adr.md`): `c4b09db`

## 2. Mục tiêu và cách tiếp cận

Bài lab xử lý bài toán bồi thường/hoàn phí vận chuyển giả lập của LogiX-VN trên cùng một hợp đồng dữ liệu (`RunResult`, `trace.v1`, SQLite ledger) nhưng triển khai qua bốn kiến trúc với mức tự chủ tăng dần: `workflow` (A), `single` (B), `orchestrator` (C) và `swarm` (D, có sẵn làm đối chứng). Nguyên tắc thiết kế cốt lõi là tách bạch ranh giới **code quyết định tiền, quyền sở hữu, approval và idempotency**, còn model chỉ đọc/soạn chữ; mọi nội dung trong `ticket` là dữ liệu người dùng không đáng tin.

Nhóm 2 người chia việc song song theo hai nhánh độc lập để tránh xung đột file:
- Thành viên 1 phụ trách `workflow.py`, `orchestrator.py`, test cho `workflow`/`orchestrator`/`handoff`, chạy `crash_test` + `benchmark` tổng hợp, viết `TEAM.md` và `decision_adr.md`.
- Thành viên 2 (Lê Phạm Thành Đạt) phụ trách `single.py` (bounded ReAct `max_steps=8`), bộ test edge-case kiểu hidden (`src/tests/test_tv2_hidden_edge_cases.py`), thí nghiệm ablation & `research_card.md`, và tổng hợp phân tích phần `single` trong báo cáo nhóm.

## 3. Giải pháp

### Shape A — Deterministic Workflow (`src/lab8/shapes/workflow.py`)
- **Luồng cố định, không vòng lặp:** mở SQLite qua `lab8.db.connect(store_path)` (đóng trong `finally`), đọc claim qua `get_claim_view` (đã bỏ `parent_secret`, `raw_headers_json`). Không thấy claim → `failed` (`unknown_claim`).
- **Rẽ nhánh bằng Python trên dữ liệu có cấu trúc:** không có `order_id` → `needs_info`; `lookup_order(conn, order_id, principal_id)` không visible (khác chủ đơn, mã đơn homoglyph, không tồn tại) → `escalated`; quote từ `compute_compensation(conn, order)` trên dòng `orders` + policy hiện hành, **bỏ qua số ngày trễ ghi trong ticket**; quote `0` (đơn hủy, chưa đủ ngày trễ) → `denied`, không gọi `issue_refund`.
- **Cổng ghi tiền:** quote `> 0` → `durability.issue_refund(conn, claim_id, <quote đầy đủ>, crash_at=crash_at)`. Không tự trừ phần đã hoàn của claim khác vì host đã trừ (T13, T14). Kết quả host: `ok` → `resolved`; `amount_conflict` → `failed`; lỗi approval/đã hoàn → `denied` (host ghi `policy_denied`), `proposal_amount` vẫn là quote đầy đủ.
- **Model chỉ soạn chữ:** đúng 1 lần `MockLLM.complete(purpose="draft")` ở mỗi nhánh kết thúc; model không chọn số tiền, không commit refund.
- **Crash & trace:** `InjectedCrash` được ghi event `crash`, flush trace rồi `raise` lại (không nuốt), chạy lại trên cùng DB thì host trả kết quả idempotent (1 ledger row, 1 audit `refund_committed`). Trace v1 chỉ ghi `claim` (`claim_id`, `has_order_id`), `lookup_order` (allowlist `ORDER_FIELDS`), `quote`, `host_refund`, `decision`; mọi nhánh return đều qua `lab8.shapes.common.finish()`.

### Shape B — Bounded Single ReAct Agent (`src/lab8/shapes/single.py`)
- **Đọc dữ liệu có kiểm soát:** Mở SQLite qua `lab8.db.connect(store_path)` (đảm bảo `conn.close()` trong `finally`), đọc claim qua `get_claim_view` (loại bỏ `parent_secret` và `raw_headers_json`). Nếu không tìm thấy claim → trả `failed` (`unknown_claim`).
- **Model chọn tool thực sự bên trong vòng ReAct (`max_steps=8`, `worker=True`):** Dùng `lab8.runtime.run_react`. Ở mỗi bước bên trong `decide(obs)`:
  1. Bước đầu tiên gọi `MockLLM.complete(..., purpose="parse")` để đọc nội dung ticket và ghi `react_thought` (không dùng số ngày parse được để ghi đè DB).
  2. Xây dựng prompt tóm tắt trạng thái an toàn (không secret/PII) kèm danh sách các read-only tool hợp lệ còn lại (`candidates`), gọi `MockLLM.complete(..., purpose="react_step")` để model chọn hành động: hỗ trợ cả chỉ thị tường minh (`tool=...` / `final=...`) lẫn lựa chọn trong `candidates` theo digest của `MockLLM` (làm thay đổi thứ tự gọi giữa `lookup_policy`, `lookup_refund_history`, và `get_clause` khi ticket có trích dẫn điều khoản như `SHIP-LATE-OLD`).
  3. Vì `run_react` chỉ giữ `last_tool`, `last_result`, `claim` trong `observation` của bước tiếp theo, `decide` dùng closure `state` để tích lũy `order_view`, `policy_loaded`, `refund_history`, `checked_clause` và `quote`.
  4. Do `worker=True`, mọi nỗ lực chọn write tool (`issue_refund`, `append_audit`) đều bị `dispatch` chặn bằng `ToolRejected` (bắt gọn về `status="failed"`, `error_reason="tool_rejected"`, không ghi refund); nếu lặp quá `max_steps=8` sẽ dừng ở `step_cap` (`status="failed"`, `error_reason="step_cap"`, 0 refund).
- **Cổng ghi Host & Trace v1:** Khi `proposal > 0`, shape truyền **quote đầy đủ** vào `durability.issue_refund(conn, claim_id, proposal, crash_at=crash_at)` để host kiểm tra approval gắn đúng `claim_id`, trừ phần đã hoàn trước đó trên cùng đơn, và ghi `refund_ledger` + `refund_committed` trong cùng một transaction. `InjectedCrash` được ghi sự kiện `crash` vào trace, flush file và `raise` lại nguyên trạng. Mọi nhánh return đều đi qua `lab8.shapes.common.finish()`.

### Shape C — Orchestrator & Read-Only Investigators (`src/lab8/shapes/orchestrator.py`)
- **Phần đầu giống workflow:** `get_claim_view` → `unknown_claim`/`needs_info`, cộng 1 lần `MockLLM.complete(purpose="plan")` để lập kế hoạch (ghi event `plan` chỉ có `claim_id`, `has_order_id`).
- **Handoff qua allowlist, không qua LLM:** tạo gói bằng `lab8.handoff.make_handoff(request_id, claim_id, task, facts={}, allowed_tools=["lookup_order", "lookup_policy", "lookup_refund_history"])`. `make_handoff`/`sanitize` chỉ giữ field trong `ALLOWED_FIELDS`, lọc key lạ trong `facts`, từ chối write tool (`issue_refund`, `append_audit`) và chuỗi `CANARY_SECRET_*` (`HandoffError`). Không đưa `parent_secret`, `raw_headers`, ticket thô hay cả dòng claim vào handoff. Trace ghi **bản handoff đã sanitize** (`handoff.v1`), không ghi ngữ cảnh cha.
- **Investigator chỉ đọc:** `lab8.runtime.run_readonly_investigators(conn, budget, handoff, principal_id=...)` chạy 3 tool đọc; investigator không có write registry. Event `investigator` chỉ ghi order view đã allowlist, lịch sử hoàn và số policy.
- **Orchestrator giữ quyền ghi:** quote từ order view của investigator bằng `compute_compensation`, rồi gọi `durability.issue_refund` với quote đầy đủ và `crash_at`, map kết quả và xử lý `InjectedCrash` giống workflow. Tổng `2` model calls (plan + draft).

## 4. Kết quả

Chạy trên 14 public claims × 5 seeds (`11, 22, 33, 44, 55`, 70 trial/shape). Số liệu 4 shape lấy từ `src/reports/benchmark.json` (chạy lại sau khi merge cả hai nhánh, cùng corpus và seed); dòng ablation `single_no_llm` lấy từ `src/reports/ablation_r4.json`. Crash suite: `crash_safety = 20/20` (`src/reports/crash.json`):

| Shape | Pass rate | Pass^5 | Seed min–max | Seed variance | Cost/success (VND mô phỏng) | Mean / p95 steps | Ghi chú |
| --- | ---: | ---: | --- | ---: | ---: | --- | --- |
| `workflow` | `1.000` (70/70) | `1.000` | `1.000`–`1.000` | `0.000000` | `28.89` | `3.79` / `4.0` | `mean_model_calls=1.00`, `mean_tool_calls=2.79`; shape được chọn |
| `single` | `1.000` (70/70) | `1.000` | `1.000`–`1.000` | `0.000000` | `52.37` | `10.14` / `13.0` | `mean_model_calls=6.57`, `mean_tool_calls=4.57` |
| `single_no_llm` *(ablation)* | `1.000` (70/70) | `1.000` | `1.000`–`1.000` | `0.000000` | `45.71` | `9.14` / `12.0` | `mean_model_calls=0.00`, `mean_tool_calls=4.57` |
| `orchestrator` | `1.000` (70/70) | `1.000` | `1.000`–`1.000` | `0.000000` | `57.18` | `4.71` / `5.0` | `mean_model_calls=2.00`, `mean_tool_calls=5.57` |
| `swarm` *(đối chứng)* | `0.986` (69/70) | `0.929` | `0.929`–`1.000` | `0.000816` | `49.57` | `2.80` / `3.0` | Fail `C-002` seed 55 (`status resolved != denied`) |

Quyết định kiến trúc và lý do: xem `report/team/decision_adr.md`. Phiếu nghiên cứu và ablation: xem `report/team/research_card.md`. Kết quả kiểm toán grader (Bonus B7): xem `report/team/bonus_report.md` và `src/reports/bonus_grader_audit.json`.

### Tự kiểm trên `student_drop/` (`src/reports/hidden_selfcheck.json`)
Sau khi nhận bộ 40 hidden claim không nhãn (`C-H01`–`C-H40`) từ lab coach, nhóm chạy lại benchmark 4 shape × 5 seed (`200` trial/shape, `student_drop/` bị `.gitignore` chặn nên không commit):
- `workflow`, `single`, `orchestrator` đều đạt **`error_trials = 0`**, **`leak_suspect_trials = 0`**, `trace.v1` hợp lệ `200/200` và đồng thuận 100% `status` trên mọi cặp `(claim, seed)` (`90` `resolved`, `95` `denied`, `10` `escalated`, `5` `needs_info`), với tổng chi phí mô phỏng 200 trial lần lượt là `6,006.20 VND` (`workflow`), `10,907.54 VND` (`single`) và `11,944.20 VND` (`orchestrator`).
- `swarm` (`10,182.38 VND`) lệch ở `seed = 55` trên **6 hidden claim**: `C-H01`, `C-H02`, `C-H04`, `C-H13`, `C-H20` (tin ticket nói quá nên trả `resolved` thay vì `denied`) và `C-H40` (tin ticket nói giảm `1 ngày` nên trả `denied` thay vì `resolved`).

## 5. Khó khăn và cách xử lý

1. **Cơ chế truyền ngữ cảnh trong `run_react` (`src/lab8/runtime.py`):** Ở mỗi vòng lặp, `run_react` ghi đè `seen = {"last_tool": name, "last_result": result, "claim": observation.get("claim")}`, không giữ lịch sử các tool đã gọi trước đó. Ban đầu dễ bị mất `order_view` khi chuyển sang bước `compute_compensation`. **Cách xử lý:** dùng closure `state` trong `single.py` để lưu `order_view`, `policy_count`, `refund_history` và `quote` qua từng bước, kết hợp kiểm tra bằng bộ test ReAct.
2. **Thiết kế test `amount_conflict` và test nối tiếp trên cùng SQLite (`src/tests/test_tv2_hidden_edge_cases.py`):**
   - Khi thử kích hoạt `amount_conflict` trên `C-001` bằng cách bật `damage_verified = 1` (quote tăng lên `150.000`), `policy.authorize` vẫn chặn số tiền được duyệt ở mức `approved_vnd = 35.000` nên không sinh conflict. Đổi kịch bản test sang thay đổi `shipping_fee_vnd = 20.000 <= approved_vnd` thì host bắt đúng `amount_conflict` và giữ nguyên `35.000` trong ledger.
   - Khi chạy nhiều claim nối tiếp trên cùng file SQLite, `trial_pass` dùng `unexpected_ledger_rows` (chỉ tính `prior_refund_rows` được seed từ đầu) nên báo lỗi nếu chấm từng claim giữa chuỗi. Nhóm xử lý bằng cách kiểm tra trực tiếp `refund_ledger`, `audit_events` (`policy_denied`) và `check_trace` cho kịch bản đa claim nối tiếp, đồng thời giữ `trial_pass` cho bài test một claim/DB.
3. **Không trừ tiền hai lần (Shape A/C):** dễ muốn tự trừ phần đã hoàn của claim khác trên cùng đơn trước khi gọi `issue_refund`. Docstring và `durability.issue_refund` cho thấy host đã tự trừ (`order_refunded_vnd`), nên shape luôn truyền **quote đầy đủ**; test `test_approval_mismatch_records_policy_denied_with_full_proposal` khóa hành vi `proposal_amount` = quote đầy đủ khi host từ chối.
4. **Crash phải lan ra ngoài nhưng trace vẫn hợp lệ:** nếu bắt `InjectedCrash` rồi trả `RunResult` thì crash suite fail; nếu không ghi trace thì mất bằng chứng. Cách xử lý: bắt, ghi event `crash`, `trace.write()` rồi `raise` lại; test 3 mốc crash × 2 shape kiểm tra chạy lại chỉ có 1 refund và 1 audit.
5. **Tích hợp hai nhánh:** repo nhóm là fork nên GitHub Desktop mặc định mở PR sang repo đề bài; nhóm đổi *Fork behavior* sang "For my own purposes" và tạo PR vào `main` của repo nhóm. Khi merge, `TEAM.md` bị conflict giữa hai nhánh; nhóm gộp tay (giữ thông tin cả hai thành viên) rồi chạy lại `pytest`, benchmark, crash suite và `check_submission` trên code đã gộp.
6. **Bug regex `B[1-6]` trong `check_submission.py` khi làm Bonus B7:** `src/lab8/check_submission.py:243` kiểm tiêu đề `report/team/bonus_report.md` bằng regex `r"Bonus report:\s*B[1-6]\b"`, chưa cập nhật cho topic `B7` mới thêm trong `docs/bonus_topics.md`. Nhóm giữ nguyên file `check_submission.py` (không sửa công cụ chấm) và giữ đúng tiêu đề `# Bonus report: B7`, đồng thời ghi chú rõ tình trạng `1 FAIL` duy nhất ở dòng này.

## 6. Tổng hợp đóng góp

Chi tiết đóng góp của từng thành viên nằm trong `TEAM.md` (bảng đóng góp) và báo cáo cá nhân theo mẫu `report/team/MSSV_HoTen.md`: Thành viên 1 là `report/team/2A202604071_TranDucDuy.md` (kèm Bonus B7 ở `src/bonus/` và `report/team/bonus_report.md`), Thành viên 2 là `report/team/2A202604027_LePhamThanhDat.md`.

## 7. Hạn chế và hướng cải thiện

- **Giới hạn của môi trường mô phỏng:** `MockLLM` không phải model ngôn ngữ thật và sinh câu chữ dựa trên SHA-256 hash theo `seed`, vì vậy không phản ánh hết rủi ro hallucination tự nhiên hoặc lỗi phân tích ngữ nghĩa phức tạp ngoài mẫu câu `tre <N> ngay`. Giá token tính bằng VND mô phỏng theo `config/pricing.yaml` (không phải hóa đơn API thật) và `latency` để `unavailable`.
- **Giới hạn quy mô dữ liệu & đo bước:** Bộ public chỉ có 14 claim. Ngoài ra, chỉ số `mean_steps` phụ thuộc vào số event do shape chủ động ghi vào trace JSON (ví dụ `swarm` ghi ít event trace hơn nên `mean_steps = 2.8` dù gọi nhiều `model_calls` và `tool_calls` hơn `single` với `mean_steps = 10.14`).
- **Hướng cải thiện khi đưa ra production:** Cần thay `MockLLM` bằng model thật kèm đánh giá latency đầu-cuối, bổ sung bộ test ngữ nghĩa tự nhiên cho việc rút trích thông tin hỗ trợ (vẫn khóa mọi tính toán tiền tệ, quyền sở hữu, approval và ledger idempotency ở tầng code deterministic), và giữ cơ chế outbox/reconciliation nếu kết nối cổng thanh toán ngoài.

## 8. Tài liệu tham khảo

- Tài liệu lab: `docs/architecture.md`, `docs/contracts.md` (RunResult, Trace contract v1, `handoff.v1`), `docs/business_rules.md`, `docs/metrics.md`, `RUBRIC.md`.
- Docstring đề bài trong `src/lab8/shapes/workflow.py`, `single.py`, `orchestrator.py` và cổng host `src/lab8/durability.py`.
- Nguồn cho phiếu nghiên cứu R4 (xem `report/team/research_card.md`): Zhang, J., Zhang, L., Lu, P., Zhang, Q., Chuang, Y.-N., Li, Z., Xu, S., Chaudhary, V., & Chen, H. (2026), *"Rethinking the Evaluation of Efficiency Methods for Multi-Agent Systems"*, EMNLP 2026, pp. 18527–18562 (https://aclanthology.org/2026.emnlp-main.798/, arXiv:2609.05933).
- Slide buổi lý thuyết Day 8 *From Workflows to Agents* (thư viện tham khảo, slide 68–69).
