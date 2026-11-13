# Day 06 · Truy xuất bài giảng xử lý dữ liệu cảm biến

Nguyễn Thị Thùy Dung · 2A202603552 · L3A. Bài thực nghiệm đo ảnh hưởng của cách chia đoạn và lọc theo mục bài giảng lên khả năng tìm được bằng chứng trong ba kết quả đầu.

## Corpus và pipeline

PDF do giảng viên cung cấp, quyền công khai theo xác nhận của học viên. [Manifest](data/manifest.json) ghi SHA-256, đường dẫn, số ký tự và mục của từng trang. Trong 49 trang vật lý, corpus dùng trang 5, 14, 19–34 và 36–48 (31 trang, 12.142 ký tự). [Bảng đối chiếu](review/page_review.csv) ghi lý do tính các trang ngắn và sơ đồ. Ngày truy cập gốc chưa được ghi nhận.

Python và pypdf trích chữ theo trang, chuẩn hóa NFC rồi chia chunk trong giới hạn 128 token. Sentence Transformers dùng cùng model đa ngữ paraphrase-multilingual-MiniLM-L12-v2 cho query và tài liệu, vector chuẩn hóa 384 chiều. ChromaDB lưu trên đĩa và tìm theo cosine distance. Mỗi chunk giữ nguồn, ID tài liệu, trang, section và offset.

| Cấu hình | Chia chunk | Truy xuất |
|---|---|---|
| A | Cửa sổ tối đa 500 ký tự, overlap tối đa 50 | Không lọc |
| B | Theo đoạn/câu, tối đa 800 ký tự | Không lọc |
| C | Dùng chung chunk, vector và collection B | Lọc section khi câu hỏi chỉ định |

## Cài đặt và chạy

Ví dụ PowerShell, từ thư mục gốc, dùng Python 3.14.3 (môi trường đã kiểm thử). Lần chạy đầu cần Internet để tải model. Thay tên thư mục ở biến $out cho mỗi lần chạy mới.

~~~powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r starter/requirements.txt
$python = '.\.venv\Scripts\python.exe'
$out = 'starter/storage/run-01'
& $python -m starter.src.sensor_experiment prepare --output-dir $out
& $python -m starter.src.sensor_experiment retrieve-dev --output-dir $out
& $python -m starter.src.sensor_experiment select-dev --output-dir $out
& $python -m starter.src.sensor_experiment retrieve-test --output-dir $out
~~~

Prepare yêu cầu thư mục mới. Dev tạo hai collection và trace, sau đó chọn theo Hit@3, Hit@1, số chunk ít hơn rồi thứ tự A/B/C. Test kiểm tra checksum của dữ liệu, benchmark và trace dev trước khi truy xuất. Đọc dev/traces_dev.jsonl, evaluation/selection.json, evaluation/traces_test.jsonl và evaluation/*_exact_metrics.json trong thư mục vừa chạy.

## Benchmark và kết quả lịch sử

[Bộ câu hỏi](starter/benchmark/sensor_questions.json) gồm 15 dev và 5 test, có 4 câu chỉ định section (2 câu test). Hit@1 tính câu có bằng chứng ở hạng đầu, Hit@3 tính câu có ít nhất một chunk đủ bằng chứng trong ba hạng đầu. Proxy tự động yêu cầu đúng nguồn, trang và đoạn trích sau chuẩn hóa.

| Cấu hình | Dev Hit@1 | Dev Hit@3 | Test Hit@1 | Test Hit@3 |
|---|---:|---:|---:|---:|
| A | 10/15 (66,7%) | 12/15 (80%) | 3/5 (60%) | 3/5 (60%) |
| B | 10/15 (66,7%) | 12/15 (80%) | 3/5 (60%) | 4/5 (80%) |
| C | 10/15 (66,7%) | 13/15 (86,7%) | 3/5 (60%) | 5/5 (100%) |

Dev chọn C. Với SQ17, nhãn ngữ nghĩa do AI đề xuất tính thêm một hit cho A, đưa Hit@3 test lên 4/5. Học viên chưa xác nhận các nhãn. Test đã được xem, và lần chạy lịch sử không ghi revision model. Lần mới khóa revision e8f8c211226b894fcb81acc59f3b34ba3efd5f42.

[Báo cáo cá nhân](report/individual/2A202603552_NguyenThiThuyDung.md) trình bày năm khía cạnh đánh giá, chi phí, lỗi và đánh đổi. Xem [nhật ký thí nghiệm](artifacts/experiment_log.csv), [trace dev đã gắn nhãn](starter/results/sensor_run/evaluation/dev_exact_review.jsonl), [trace test](starter/results/sensor_run/evaluation/traces_test.jsonl) và [bảng đánh giá](review/manual_scoring_review.csv).

Để tính lại metric lịch sử và kiểm tra 180 kết quả theo trang, offset và nhãn đã lưu, chạy `python -m starter.src.verify_sensor` bằng môi trường trên.
