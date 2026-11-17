# Decision record

Điền sau dấu `:` trên cùng dòng, không xóa nhãn. Giảng viên và `python -m lab8.check_submission` (chạy trong `src/`) đọc các dòng này bằng máy. Không đổi tên hay dời file này khỏi `report/team/`.
`Shape chọn` phải là đúng một trong: `workflow`, `single`, `orchestrator`, `swarm`. Đây là shape được chấm cổng hidden.

- Shape chọn: workflow
- Commit hash: 878ffa9
- Run id dẫn chứng: R-workflow-C-001-s11 (corpus 14 claim public x 5 seed 11,22,33,44,55 trong src/reports/benchmark.json)
- Pass rate / pass^5 / seed min-max / variance: 1.000 / 1.000 / 1.000–1.000 / 0.000000 (70/70 trials; src/reports/benchmark.json)
- Cost per success (mô phỏng, VND): 28.89 VND (28.887143 VND, tổng 2022.10 VND / 70 success, mean_steps 3.79, p95 4.0; MockLLM + pricing.yaml, latency: unavailable)
- Crash safety: 20/20 (src/reports/crash.json; bổ sung test 3 crash points cho workflow & orchestrator trong src/tests/test_workflow_orchestrator.py)
- Secret leak / approval bypass: 0 / 0 trên 70/70 trials public của workflow (không có CANARY_SECRET_* hay PII trong trace/RunResult; hidden pack do giảng viên chấm riêng)

Ví dụ một dòng đã điền: `- Shape chọn: workflow`, `- Crash safety: 20/20 (src/reports/crash.json)`.

## Vì sao shape này

So sánh trên cùng 14 claim public × 5 seed (`11, 22, 33, 44, 55`), cùng MockLLM và bảng giá mô phỏng (`src/reports/benchmark.json`), `workflow` đạt `pass_rate = 1.000` (70/70), `pass^5 = 1.000`, `seed_min = 1.000`, `seed_max = 1.000`, `seed_variance = 0.000000` với `cost_per_success = 28.89` VND (thấp nhất, trung bình `1.0` model call để soạn câu trả lời và `3.79` steps). Mọi quyết định điều kiện (`order_id`, `principal_id`, `compute_compensation`) giữ hoàn toàn trong Python dựa trên dữ liệu có cấu trúc (`orders`, `policies` `is_current=1`) và ghi tiền qua `durability.issue_refund` (truyền quote đầy đủ), nên không bị ảnh hưởng bởi ticket nói dối, prompt injection hay policy hết hiệu lực. Chọn `workflow` bám đúng nguyên tắc kiến trúc ít tự chủ nhất mà vẫn giải quyết trọn vẹn bài toán. `single` (Shape B, bounded ReAct) cũng đạt `1.000 / 1.000` nhưng tốn `52.37` VND/success, trung bình `6.57` model calls và `10.14` steps (p95 `13`), tức đắt gần gấp đôi `workflow` mà không thêm điểm pass nào.

## Có đáng đổi lấy multi-agent không

Không đáng cho bài toán LogiX-VN hiện tại. Trên cùng tập public và cùng 5 seed, `orchestrator` cũng đạt `1.000 / 1.000` (`seed_variance = 0.000000`) nhưng `cost_per_success = 57.18` VND (gần gấp đôi `workflow`, trung bình `2.0` model calls và `4.71` steps). Trong khi đó `swarm` tốn `49.57` VND/success (`3.0` model calls) nhưng `pass_rate` giảm còn `0.986`, `pass^5 = 0.929`, `seed_min = 0.929`, `seed_variance = 0.000816` do seed 55 tin số ngày trễ ghi trong ticket ở `C-002`. Quyết định chọn `workflow` sẽ đảo lại nếu phạm vi bài toán mở rộng sang dữ liệu phi cấu trúc thực sự (cần suy luận ngôn ngữ tự nhiên mới rút ra được sự kiện) hoặc có nhiều tác vụ đọc độc lập độ trễ cao cần chạy song song, khiến `workflow` không đạt ngưỡng hidden `>= 0.75` trong khi `orchestrator`/agent vượt ngưỡng rõ rệt và vẫn giữ `0` secret leak / `0` approval bypass.

## Trace và bằng chứng

Trace tuân theo `Trace contract v1` (`src/traces/<run_id>.json`): `workflow` chỉ ghi các event tối giản `claim` (`claim_id`, `has_order_id`), `lookup_order` (chỉ `ORDER_FIELDS` allowlist), `quote`, `host_refund` (`ok`, `reason`, `conflict`, `status`), `decision`, `crash`, `error`; `orchestrator` ghi thêm `plan`, `handoff` (`handoff.v1` đã qua `make_handoff`) và tóm tắt từ `investigator`. Cố ý **không** ghi: `parent_secret`, `raw_headers_json`, `ticket` thô, `phone`, `address`, `internal_note`, `item_name`, `approval_id` hay dòng DB thô của `claims`/`orders` vào trace hoặc stdout. Nếu trace bị ghi ra ngoài chỗ scanner kiểm tra (không trỏ đúng `RunResult.trace_path` hoặc đặt file phụ không theo prefix `<run_id>*`), `check_trace` sẽ fail-closed (`missing_trace` / `invalid_trace`); để chứng minh không rò rỉ secret, cần rà quét toàn bộ thư mục artifact sinh ra kết hợp kiểm tra tĩnh/test khẳng định allowlist tại mọi ranh giới đọc DB và handoff.

## Giới hạn

MockLLM không phải model sản xuất (deterministic theo seed, không phản ánh chất lượng suy luận thực); `latency` là `unavailable`; giá token tính theo `src/config/pricing.yaml` mang tính mô phỏng; số liệu trong `src/reports/benchmark.json` được chạy lại sau khi merge Shape B của TV2 (đủ 4 shape); tập hidden 40 claim × 5 seed chưa có nhãn ở môi trường học viên nên chưa đo được pass rate hidden trực tiếp. Không chỉnh sửa tay file JSON trong `src/reports/`.
