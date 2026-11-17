# Team

## Thông tin nhóm

- Tên nhóm: Delta
- Lớp: L3B
- Repo nhóm: `K5-L3B-DAY08-Delta-FromWorkflowsToAgents` (xem [SUBMISSION.md](SUBMISSION.md))
- URL repo, nhánh nộp, commit chốt: `https://github.com/liliustwocout/K5-L3B-DAY08-Delta-FromWorkflowsToAgents` · nhánh `main` · commit `[cập nhật khi chốt submit]`

## Thành viên

| STT | Họ tên | MSSV | Email | GitHub | Vai trò |
| --: | ------ | ---- | ----- | ------ | ------- |
|   1 | [Thành viên 1 điền] | [MSSV] | [Email] | [GitHub] | Workflow (`workflow.py`), Orchestrator & Handoff (`orchestrator.py`), Crash/Benchmark tổng hợp, ADR |
|   2 | Lê Phạm Thành Đạt | 2A202604027 | datpltn205@gmail.com | liliustwocout | Single ReAct (`single.py`), Hidden Edge-Case Tests, Ablation & Research Card |

Gợi ý chia vai:

- Nhóm 6 người: integration; workflow; single agent; orchestrator; ledger/policy/crash; eval/report.
- Nhóm 4 người: workflow + integration; single; orchestrator + handoff; ledger + evaluation.

## Bảng đóng góp

`python -m lab8.check_submission` đọc bảng này bằng máy: giữ nguyên tiêu đề `## Bảng đóng góp` và các cột. Mỗi người một dòng: commit có nội dung và ít nhất một test đã thêm hoặc sửa.

| Người | Vai | Commit | Test đã thêm hoặc sửa |
| --- | --- | --- | --- |
| [Thành viên 1 điền] | Workflow, Orchestrator, Infra & ADR | `[điền commit hash trên main]` | `[điền tên file test của TV1]` |
| Lê Phạm Thành Đạt | Single ReAct (`single.py`), Hidden Edge Cases & Research Card | `d2aca14` | `src/tests/test_tv2_hidden_edge_cases.py` (19 test cases) |

## Cá nhân

Mỗi thành viên đồng thời tạo một báo cáo riêng trong `report/` theo dạng:

```text
report/team/MSSV_HoTen.md
```

Ví dụ: `report/team/20241234_NguyenVanAn.md`.

Sao chép mục dưới đây cho từng thành viên.

## [Thành viên 1: MSSV_HoTen]

### Phần việc phụ trách

- `[Thành viên 1 điền]`

### Đóng góp cụ thể

- `[Thành viên 1 điền]`

### Bằng chứng

- `[Thành viên 1 điền]`

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

- `python -m pytest -q`: `73 passed, 248 deselected` (gồm 19 test mới).
- `python -m pytest -q -m student -o addopts= -k "single and not workflow and not orchestrator and not swarm"`: `62 passed`.
- `src/reports/ablation_r4.json`: `single` đạt `pass_rate = 1.000` (70/70), `pass^5 = 1.000`, `seed_variance = 0.000000`, `cost/success = 52.37 VND` (`mean_model_calls = 6.57`, `mean_tool_calls = 4.57`).
