# Team

## Thông tin nhóm

- Tên nhóm: Delta
- Lớp: L3B
- Repo nhóm: `K5-L3B-DAY08-Delta-FromWorkflowsToAgents` (xem [SUBMISSION.md](SUBMISSION.md))
- URL repo, nhánh nộp, commit chốt: `https://github.com/liliustwocout/K5-L3B-DAY08-Delta-FromWorkflowsToAgents` · nhánh `main` · commit `95a45fa`

## Thành viên

| STT | Họ tên | MSSV | Email | GitHub | Vai trò |
| --: | ------ | ---- | ----- | ------ | ------- |
|   1 | Trần Đức Duy | 2A202604071 | tran85122@gmail.com | tran85122-afk | Shape A (`workflow.py`), Shape C (`orchestrator.py`) & Handoff, test workflow/orchestrator/handoff, `crash_test` + `benchmark` + `check_submission`, `TEAM.md` & `decision_adr.md` |
|   2 | Lê Phạm Thành Đạt | 2A202604027 | datpltn205@gmail.com | liliustwocout | Single ReAct (`single.py`), Hidden Edge-Case Tests, Ablation & Research Card |

Gợi ý chia vai:

- Nhóm 6 người: integration; workflow; single agent; orchestrator; ledger/policy/crash; eval/report.
- Nhóm 4 người: workflow + integration; single; orchestrator + handoff; ledger + evaluation.

## Bảng đóng góp

`python -m lab8.check_submission` đọc bảng này bằng máy: giữ nguyên tiêu đề `## Bảng đóng góp` và các cột. Mỗi người một dòng: commit có nội dung và ít nhất một test đã thêm hoặc sửa.

| Người | Vai | Commit | Test đã thêm hoặc sửa |
| --- | --- | --- | --- |
| Trần Đức Duy | Shape A (`workflow.py`), Shape C (`orchestrator.py`), benchmark/crash/check_submission, `TEAM.md` & `decision_adr.md` | `a559883` | `src/tests/test_workflow_orchestrator.py` |
| Lê Phạm Thành Đạt | Single ReAct (`single.py`), Hidden Edge Cases & Research Card | `d2aca14` | `src/tests/test_tv2_hidden_edge_cases.py` (19 test cases) |

## Cá nhân

Mỗi thành viên đồng thời tạo một báo cáo riêng trong `report/` theo dạng:

```text
report/team/MSSV_HoTen.md
```

Ví dụ: `report/team/20241234_NguyenVanAn.md`.

Sao chép mục dưới đây cho từng thành viên.

## 2A202604071_TranDucDuy

### Phần việc phụ trách

- Shape A — Deterministic Workflow (`src/lab8/shapes/workflow.py`).
- Shape C — Orchestrator + read-only investigators và handoff `handoff.v1` (`src/lab8/shapes/orchestrator.py`).
- Bộ test cho workflow / orchestrator / handoff (`src/tests/test_workflow_orchestrator.py`).
- Chạy `crash_test`, `benchmark` 4 shape × 5 seed, `check_submission`; viết `TEAM.md`, `report/team/decision_adr.md`, phần Shape A/C trong `report/team/group_report.md`.

### Đóng góp cụ thể

- `workflow.py`: luồng cố định `needs_info` / `escalated` / `denied` / `resolved` / `failed`, tiền tính bằng `compute_compensation` trên dòng `orders` (bỏ qua số ngày trễ trong ticket), truyền quote đầy đủ vào `durability.issue_refund`, `InjectedCrash` được ghi trace rồi `raise` lại; model chỉ soạn chữ (1 call).
- `orchestrator.py`: handoff tạo bằng `make_handoff` với `facts={}` và 3 read-only tool, `run_readonly_investigators` đọc dữ liệu, orchestrator tự quote và gọi `issue_refund`; trace ghi bản handoff đã sanitize.
- Test: claim không tồn tại, T02 seed 55, 3 mốc crash × 2 shape, homoglyph / đơn hủy, mượn approval của claim khác, handoff lọc key lạ + từ chối write tool / canary, so sánh cost workflow < orchestrator.
- Merge nhánh TV2 vào nhánh TV1, gộp conflict `TEAM.md`, chạy lại benchmark/crash trên code đã gộp và cập nhật số liệu `single` vào ADR.

### Bằng chứng

- Commit `a559883` (Shape A + C, test, report), commit merge `dfd4eda`, PR #2 vào `main`.
- `python -m pytest -q`: `90 passed`; `python -m pytest -q -m student -o addopts=`: `248 passed` (workflow 62/62, orchestrator 62/62).
- `src/reports/benchmark.json`: `workflow` `1.000` / `pass^5 1.000` / `28.89` VND/success; `orchestrator` `1.000` / `57.18` VND/success. `src/reports/crash.json`: `20/20`.
- `python -m lab8.check_submission`: `0 FAIL, 0 WARN`.

## 2A202604027_LePhamThanhDat

### Phần việc phụ trách

- Dựng môi trường `.venv` trong `src/` và kiểm tra cổng host ban đầu (`lab8.smoke`, `pytest -q`).
- Triển khai Shape B — Bounded Single ReAct (`src/lab8/shapes/single.py`) và biến thể ablation `run_claim_no_llm`.
- Viết bộ test phòng thủ hidden edge-case (`src/tests/test_tv2_hidden_edge_cases.py`).
- Thiết kế, chạy thực nghiệm ablation R4 (`src/reports/ablation_r4.json`) và điền `report/team/research_card.md`.

### Đóng góp cụ thể

- Hoàn thiện `src/lab8/shapes/single.py` dùng `run_react(..., max_steps=8, worker=True)` với `MockLLM` tham gia chọn read-only tool bên trong `decide()` và closure `state`, giữ ranh giới code/model, truyền quote đầy đủ vào `durability.issue_refund`, truyền `crash_at` và giữ trace `trace.v1` sạch secret/PII.
- Bổ sung 19 test cases trong `src/tests/test_tv2_hidden_edge_cases.py` phủ homoglyph/injection, policy cũ/tương lai, stacking `max`, approval lỗi, 3 mốc crash, `amount_conflict`, `step_cap=8` và `worker=True` qua chính `single.run_claim`, biến thiên chọn tool theo seed, trần hoàn tiền tuần tự theo đơn, và ablation `single_no_llm`.
- Soạn mục Shape B, kết quả sơ bộ, khó khăn/cách xử lý và hạn chế trong `report/team/group_report.md`; hoàn thiện `report/team/2A202604027_LePhamThanhDat.md`.

### Bằng chứng

- Commit `d2aca14`, `1eec41a`, PR #1 (`e98e9de`) vào `main`.
- `python -m pytest -q`: `90 passed, 248 deselected` trên `main` (gồm 19 test mới của TV2 trong `src/tests/test_tv2_hidden_edge_cases.py`).
- `python -m pytest -q -m student -o addopts=`: `248 passed, 90 deselected` (riêng `single` đạt `62/62`).
- `src/reports/ablation_r4.json` & `src/reports/benchmark.json`: `single` đạt `pass_rate = 1.000` (70/70), `pass^5 = 1.000`, `seed_variance = 0.000000`, `cost/success = 52.37 VND` (`mean_model_calls = 6.57`, `mean_tool_calls = 4.57`).
