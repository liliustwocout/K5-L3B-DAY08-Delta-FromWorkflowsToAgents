# Bonus report: B7

> **Ghi chú nộp bài:** `python -m lab8.check_submission` báo 1 FAIL cho file này (đòi tiêu đề chỉ được là B1 đến B6) vì regex ở `src/lab8/check_submission.py:243` là `B[1-6]`; công cụ chưa được cập nhật khi đề bài thêm B7 (`docs/bonus_topics.md`). Nhóm giữ đúng tiêu đề B7 và không sửa `check_submission.py`. Ngoài dòng này, `check_submission` không còn FAIL nào khác.

- Topic + nguồn (tên, năm, slide): B7 · Kiểm toán grader — *Rethinking Evaluation of MAS Efficiency*, EMNLP 2026 (slide 44, 59).
- CLAIM của nguồn (1 câu): Kết luận về hiệu năng của hệ agent có thể đến từ cách đo; nếu thước đo sai thì mọi so sánh shape đều sai theo, kể cả khi shape đúng.
- BOUNDARY (model / dataset / setup): Nguồn nói về benchmark MAS dùng LLM thật; ở đây chỉ kiểm hàm tổng hợp `summarize` trên trial dựng sẵn (`grader_audit/fixtures/`, 1 shape, 6–8 claim, 2 seed) và hàm `lab8.compensation.quote`, không có model nào chạy.
- HYPOTHESIS trên LogiX: Ba quan hệ metamorphic trong `grader_audit/README.md` đủ để tách bản `summarize` đúng khỏi bản lệch mà không cần đáp án tuyệt đối; và có ít nhất một lớp lỗi lọt qua cả ba, cần quan hệ thứ tư.
- Biến cố định / biến thay đổi: cố định fixture, `lab8.metrics.summarize`, `lab8.compensation.quote` (không sửa file nào trong `grader_audit/` hay `lab8/`). Biến thay đổi: bản grader (`grader_a`, `grader_b`, `grader_c`, thêm `lab8.metrics` gốc và một grader đột biến do nhóm tự viết) và phép biến đổi input (thêm trial hạ tầng, nhân đôi, hoán vị).
- Lệnh tái lập (copy-paste được, chạy trong `src/`):
  - `python -m pytest -q tests/test_bonus_grader_audit.py -rxX`
  - `python -m bonus.grader_audit_report --out reports/bonus_grader_audit.json`
- File report + run id: `src/reports/bonus_grader_audit.json` (sinh bằng lệnh trên); code `src/bonus/grader_audit.py`, test `src/tests/test_bonus_grader_audit.py`. Topic không có biến thể shape nên không chạy `--extra-shape`.

## Kết quả

Bảng bản × quan hệ, số lấy từ `src/reports/bonus_grader_audit.json` (a = input gốc, b = input đã biến đổi):

| Bản | Infra không đổi pass rate | Nhân đôi: tỉ lệ giữ, tổng gấp đôi (trừ `pass_5`) | Nhân đôi: `pass_5` giữ | Hoán vị (mới) |
| --- | --- | --- | --- | --- |
| `grader_a` | đạt | **lệch**: `total_simulated_cost_vnd` 283.5 → 473.0 (phải 567.0); `cost_per_success_vnd` 31.5 → 26.28 | lệch 0.667 → 0 | **lệch**: đảo ngược list, tổng chi phí 283.5 → 285.0 |
| `grader_b` | đạt | đạt | lệch 0.667 → 0 | đạt |
| `grader_c` | **lệch**: `pass_rate` 0.75 → 0.5625, `graded_trials` 12 → 16, `pass_5` 0.667 → 0.5 | đạt | lệch 0.667 → 0 | đạt |
| `lab8.metrics` gốc | lệch (không biết `infra_error`, như `grader_c`) | đạt | lệch 0.667 → 0 | đạt |
| đột biến `mutant_first_seen` | đạt | đạt | lệch 0.667 → 0 | **lệch**: `pass_rate` 0.833 → 0.667 |

Quan hệ `delay_days` 2 so với 3 (qua `lab8.compensation.quote`, policy `POL-2026-11`): **đạt**. Cặp fixture chỉ khác `delay_days`; 2 ngày → `amount_vnd = 0` (`no_entitlement`), 3 ngày → `35000` = phí ship, clause `SHIP-LATE-03`, đúng luật `min_delay_days = 3` trong `docs/business_rules.md`.

Gọi tên lỗi bằng hành vi:

- **`grader_a` — đếm chi phí hai lần:** với mỗi claim, cộng thêm `cost_estimate` của trial đầu tiên gặp được vào tổng (189.5 → 283.5 trên fixture `a`). Quan hệ nhân đôi bắt được vì phần cộng thêm tính theo claim duy nhất nên không gấp đôi; quan hệ hoán vị bắt được vì "trial đầu tiên" đổi theo thứ tự. Pass rate không sai, nên lỗi này chỉ làm `cost_per_success` phình lên, đúng kiểu lỗi làm lệch kết luận về chi phí mà không test pass/fail nào kêu.
- **`grader_c` — đếm trial hạ tầng vào mẫu số như quyết định sai:** gán `passed=False` cho trial `infra_error`, nên 4 trial timeout kéo `pass_rate` từ 0.75 xuống 0.5625. Một shape đúng có thể bị đánh trượt ngưỡng 0.75 chỉ vì hạ tầng.
- **`grader_b` — đúng** trên cả bốn quan hệ, trừ `pass_5` khi nhân đôi (xem dưới). Đây là bản nên dùng.
- **Lỗi chung nằm ở `lab8.metrics.summarize`:** `pass^5` chỉ tính claim có `len(rows) == len(seeds)`, nên khi một cặp (claim, seed) xuất hiện hai lần thì mọi claim bị loại và `pass_5` về 0. Cả ba bản đều kế thừa lỗi này. Nhóm không sửa được (`metrics.py` là file thước đo), nên ghi nhận bằng test `xfail(strict=True)`.

Quan hệ mới — **bất biến hoán vị:** đảo ngược hoặc xáo trộn (theo seed cố định) danh sách trial thì mọi thống kê phải giữ nguyên. Lỗi nó bắt được mà ba quan hệ cũ bỏ sót là **gộp phụ thuộc thứ tự** ("dedupe theo claim, giữ dòng đầu"). Nhóm chứng minh bằng `mutant_first_seen`: grader này tính `pass_rate` chỉ từ trial đầu tiên của mỗi claim. Nhân đôi giữ dòng đầu ở vị trí đầu, thêm trial hạ tầng chỉ nối vào cuối, nên nó qua cả hai quan hệ cũ, nhưng hoán vị làm `pass_rate` đổi 0.833 → 0.667 (test `test_new_relation_catches_bug_the_readme_relations_miss`).

## Kết luận

**Ủng hộ hypothesis.** Không cần biết số tiền hay pass rate "đúng" là bao nhiêu, ba quan hệ của README đã tách được `grader_b` (đúng) khỏi `grader_a` (đếm chi phí hai lần) và `grader_c` (phạt trial hạ tầng), và còn lộ ra một lỗi `pass_5` nằm ngay trong thước đo gốc. Quan hệ hoán vị bắt thêm lớp lỗi phụ thuộc thứ tự. Quan hệ metamorphic hữu ích vì nó chỉ cần biết input đổi thế nào thì output phải đổi thế nào, nên dùng được ngay cả khi không có nhãn tuyệt đối.

Một lỗi thước đo **vẫn có thể lọt qua cả bốn quan hệ**: ví dụ grader nhân mọi `cost_estimate` với cùng một hệ số k. Nhân đôi, thêm trial hạ tầng hay hoán vị đều giữ nguyên tỉ lệ giữa a và b, nên không quan hệ tương đối nào thấy. Muốn bắt cần một quan hệ có neo tuyệt đối, chẳng hạn "list một trial thì tổng chi phí bằng đúng `cost_estimate` của trial đó", hoặc bất biến bảo toàn `total_simulated_cost_vnd = Σ cost_estimate của trial được chấm`.

Kết luận đảo lại nếu: (1) quy ước của lab coi chi phí của trial hạ tầng là chi phí thật phải tính (khi đó `grader_b` cũng bỏ sót chi phí); (2) fixture có một cặp (claim, seed) trùng hợp lệ, ví dụ retry được ghi thành hai trial, thì "nhân đôi giữ `pass_5`" không còn là yêu cầu đúng; (3) grader được viết để luôn sắp trial trước khi gộp, khi đó hoán vị không còn bắt được lỗi "giữ dòng đầu".

## Giới hạn

- Không có MockLLM hay model nào chạy trong topic này. Mọi số liệu là trên trial dựng sẵn, không phải trên `benchmark.json` hay bộ hidden, nên không nói gì về chất lượng của shape.
- Fixture nhỏ (1 shape, tối đa 8 claim, 2 seed). Lỗi chỉ lộ khi chi phí giữa các seed khác nhau hoặc pass/fail giữa các seed khác nhau; fixture đồng đều có thể che lỗi của `grader_a` dưới phép hoán vị.
- Grader đột biến do nhóm tự viết để minh họa lớp lỗi, không phải lỗi quan sát được trong ba bản của giảng viên.
- Quan hệ `delay_days` chỉ kiểm một ngưỡng (2/3 ngày, clause `SHIP-LATE-03`), chưa kiểm hỏng hàng hay policy hết hiệu lực.
