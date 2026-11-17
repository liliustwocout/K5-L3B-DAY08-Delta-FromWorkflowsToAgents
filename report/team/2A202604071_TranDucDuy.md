# Báo cáo cá nhân



## 1. Thông tin thành viên

- Họ tên: Trần Đức Duy
- MSSV: 2A202604071
- Email: tran85122@gmail.com
- GitHub: tran85122-afk
- Vai trò trong nhóm: Thành viên 1 (TV1), nhóm Delta, lớp L3B

## 2. Phần việc phụ trách

- Shape A — Deterministic Workflow: `src/lab8/shapes/workflow.py`.
- Shape C — Orchestrator + read-only investigators và handoff `handoff.v1`: `src/lab8/shapes/orchestrator.py`.
- Test cho workflow, orchestrator và handoff: `src/tests/test_workflow_orchestrator.py`.
- Chạy và tổng hợp `crash_test`, `benchmark` (4 shape × 14 claim × 5 seed), `check_submission`.
- Viết `TEAM.md`, `report/team/decision_adr.md`, phần Shape A/C, bảng kết quả và khó khăn 3–5 trong `report/team/group_report.md`.
- Tích hợp: merge nhánh của TV2 vào nhánh TV1, gộp conflict và chạy lại toàn bộ kiểm tra trên code đã gộp.

## 3. Đóng góp cụ thể

**Commit chính**

- `a559883` — `feat(shapes): implement workflow (Shape A) and orchestrator (Shape C)`: code 2 shape, file test, `benchmark.json`, `crash.json`, `TEAM.md`, `decision_adr.md`.
- `dfd4eda` — merge `main` (Shape B của TV2) vào `feat/tv1-workflow-orchestrator`: gộp conflict `TEAM.md`, chạy lại benchmark/crash, cập nhật số liệu `single` vào ADR. Merge vào `main` qua PR #2.

**Test đã thêm** (`src/tests/test_workflow_orchestrator.py`, mỗi test chạy cho cả workflow và orchestrator)

- Claim không tồn tại → `failed` + trace hợp lệ.
- T02 ở seed 55 (seed làm `swarm` fail) vẫn pass.
- 3 mốc crash `before_effect`, `after_effect_before_checkpoint`, `after_checkpoint`: crash lan ra ngoài, chạy lại chỉ có 1 refund `35.000` và 1 audit `refund_committed`.
- Ticket có lệnh injection / mã đơn homoglyph Cyrillic / đơn đã hủy: lần lượt `needs_info`, `escalated`, `denied`, trace không chứa secret hay PII.
- Mượn approval của claim khác → `denied`, ghi `policy_denied`, `proposal_amount` vẫn là quote đầy đủ.
- Trace orchestrator chỉ chứa handoff đã sanitize, không có write tool; `make_handoff` lọc key lạ và từ chối write tool / chuỗi canary.
- Workflow gọi model 1 lần, orchestrator 2 lần, workflow rẻ hơn.

**Quyết định kỹ thuật**

- Mọi quyết định tiền, quyền sở hữu, approval nằm trong code; model chỉ soạn câu trả lời (workflow) hoặc lập kế hoạch + soạn câu trả lời (orchestrator).
- Luôn truyền quote đầy đủ vào `issue_refund` vì host đã tự trừ phần đã hoàn trên cùng đơn; tự trừ ở shape sẽ thành trừ hai lần.
- `InjectedCrash`: ghi event `crash`, flush trace rồi `raise` lại thay vì bắt và trả kết quả.
- Handoff dùng allowlist (`make_handoff`, `facts={}`), không dùng LLM tóm tắt ngữ cảnh cha.
- Chọn `workflow` làm shape chấm hidden: pass `1.000` như `single`/`orchestrator` nhưng chi phí thấp nhất (`28.89` VND/success).

## 4. Bằng chứng

- `python -m pytest -q`: `90 passed, 248 deselected`.
- `python -m pytest -q -m student -o addopts=`: `248 passed` (workflow 62/62, orchestrator 62/62).
- `src/reports/benchmark.json`: `workflow` `1.000` / `pass^5 1.000` / variance `0.000000` / `28.89` VND/success / `3.79` steps; `orchestrator` `1.000` / `57.18` VND/success / `4.71` steps.
- `src/reports/crash.json`: `crash_safety = 20/20`.
- `python -m lab8.check_submission`: `0 FAIL, 0 WARN`.
- Run id dẫn chứng: `R-workflow-C-001-s11`.

## 5. Công cụ AI đã dùng

- **Antigravity**: hỗ trợ viết code `workflow.py`, `orchestrator.py`, file test và bản nháp `TEAM.md` / `decision_adr.md`.
- **Claude Code**: review lại bài làm, chạy test / benchmark / crash / `check_submission`, hỗ trợ merge nhánh và gộp conflict, soạn nháp phần báo cáo.
- **Cách tự kiểm tra**: Đọc lại từng nhánh rẽ trong code so với docstring đề bài, tự chạy `pytest -q` và bộ student cho workflow/orchestrator, đối chiếu số trong báo cáo với `src/reports/benchmark.json`, chạy thử một claim bằng `python -m lab8.run` có và không có `--crash-at`

## 6. Tự đánh giá

Phần code và test của mình đạt đủ yêu cầu (62/62 mỗi shape, crash 20/20); điều học được là ranh giới code/model và vì sao shape ít tự chủ nhất lại thắng khi dữ liệu có cấu trúc; điều cần cải thiện là workflow và orchestrator còn lặp code ở phần quote và gọi `issue_refund`, có thể tách hàm dùng chung.
