# Báo cáo cá nhân — Day 06: Data Ingestion Engineering

**Học viên:** Nguyễn Thị Thùy Dung · **MSSV:** 2A202603552 · **Lớp:** L3A

**Trạng thái:** Bản báo cáo theo chủ đề dữ liệu cảm biến, dựa trên lần chạy ngày 13/11/2026. Học viên cần kiểm tra các trang, bằng chứng và nhãn do Codex hỗ trợ; quyền chia sẻ công khai tài liệu và minh chứng chưa được xác nhận.

## 1. Dữ liệu và pipeline

### Corpus và quyền sử dụng

Nguồn `SENSOR001` là bài giảng **Chương II: Xử lý dữ liệu cảm biến**, trên trang đầu ghi Đại học Kinh tế Quốc dân, Khoa Công nghệ thông tin. Theo xác nhận của học viên, tài liệu do giảng viên cung cấp và được phép sử dụng cho bài học. Chưa có xác nhận cho phép đăng công khai hoặc tái phân phối; vì vậy PDF, benchmark và trace có trích văn bản được giữ trên máy. Chưa xác định URL tải gốc hay ngày nhận tài liệu; không tự suy đoán. Manifest: `data/manifest.json`.

PDF có **49 trang vật lý**. Chọn **31 trang** có nội dung chữ liên quan: trang 5, 14, 19–34 và 36–48, tổng **12.142 ký tự đã chuẩn hóa**. Không tính trang bìa, mục tiêu/mục lục, trang chủ yếu là hình không trích được nội dung chữ và trang thuật ngữ cuối. Các trang dạng liệt kê được tính khi chúng cung cấp phân loại, đặc trưng hoặc bước xử lý liên quan; cách chọn cần học viên đối chiếu PDF và xác nhận với giảng viên nếu cần. Trang được đánh số vật lý từ 1. Đây là một bài giảng dạng slide, nhiều trang ngắn; số trang đủ theo cách tính nêu trên nhưng độ sâu nội dung hạn chế.

### Parse, clean và metadata

PDF được đọc bằng `pypdf`; chuẩn hóa Unicode NFC, khoảng trắng và xuống dòng, bỏ soft hyphen. Mỗi trang được giữ tách biệt để truy nguồn. Các trang hình vẽ không trích xuất được chữ có ý nghĩa đã được loại khỏi corpus chữ; không có OCR. Một số dấu đầu dòng là ký tự đặc biệt và còn số trang trong văn bản, nên dữ liệu chưa hoàn toàn sạch.

Mỗi chunk giữ `document_id`, `source`, `page`, offset ký tự trong trang và `section`. Giá trị section được gán theo các nhóm trang của các mục 2.1–2.5 trong tài liệu; với trang không lặp tiêu đề, section dựa vào vị trí trong nhóm và cần được học viên đối chiếu. Trường `section` có ích khi người hỏi chỉ định phần, còn `page` và `source` hỗ trợ truy vết. Hạn chế là nhãn section theo phạm vi trang có thể sai nếu tài liệu được sắp xếp lại.

### Embedding và lưu trữ

- Model local: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, Sentence Transformers **6.3.0**, 384 chiều, chuẩn hóa vector. Lần chạy ghi model nhưng revision trong report là `null`; cache hiện tại trỏ tới `e8f8c211226b894fcb81acc59f3b34ba3efd5f42`. Cần khóa revision khi tái lập chính thức.
- ChromaDB **1.5.9** với cosine distance, lưu bền vững tại `starter/storage/chroma/`; A có collection riêng, B/C chung collection. Index HNSW là tìm kiếm xấp xỉ; cấu hình thực tế cần giữ khi chạy lại.
- Giới hạn **128 token** bao gồm token đặc biệt; trong lần chạy này A và B không có chunk vượt giới hạn.
- Chi phí dịch vụ embedding: **0**, chạy local; tiền điện và tài nguyên máy chưa đo.

## 2. Thiết kế thí nghiệm

| Cấu hình | Chia văn bản | Truy xuất |
|---|---|---|
| A | Tối đa 500 ký tự, overlap tối đa 50; rút ngắn để vừa 128 token | Top 3, không filter |
| B | Ưu tiên ranh giới đoạn/câu, tối đa 800 ký tự và 128 token | Top 3, không filter |
| C | Dùng chung chunk, vector và collection với B | Top 3, lọc `section` nếu câu hỏi chỉ rõ |

Các cấu hình dùng cùng 31 trang, model và câu hỏi. A–B thay chiến lược chunking; B–C chỉ thay filter. Không đưa gold source hay đáp án vào truy vấn hoặc filter.

Benchmark `starter/benchmark/sensor_questions.json` có **20 câu**, gồm **15 dev và 5 test**; 4 câu có filter, trong đó 2 câu test. Câu hỏi, đáp án và gold evidence được tạo từ tài liệu cảm biến, và đoạn evidence đã kiểm tra xuất hiện tại trang được ghi sau chuẩn hóa khoảng trắng. Benchmark được tạo trước khi chạy experiment này. Bộ câu hỏi và kết quả của thí nghiệm y tế trước đây không được sử dụng để tính kết quả bên dưới.

Trước khi truy vấn test, lựa chọn được ghi tại `starter/results/sensor_run/evaluation/selection.json`: ưu tiên tỷ lệ khớp gold Top 3 trên dev, sau đó Top 1, sau đó ít chunk hơn. **C được chọn tạm** vì đạt 13/15 Top 3 trên dev, so với 12/15 của A/B. Đây là quy tắc dựa trên khớp nguyên văn; chưa chứng minh C tốt nhất trong mọi tình huống.

## 3. Kết quả

### Retrieval và tài nguyên

Các điểm sau là **khớp gold nguyên văn bảo thủ**, không phải nhãn semantic đã được người học xác nhận: một chunk được tính trúng nếu ở đúng nguồn/trang và chứa nguyên văn gold sau chuẩn hóa khoảng trắng. Bằng chứng diễn đạt khác hoặc bị chia giữa nhiều chunk có thể bị bỏ sót.

| Cấu hình | Split | Top 1 (n/N) | Top 3 (n/N) | Chunk | Tạo chunk + embedding + lưu* | Chi phí API |
|---|---|---:|---:|---:|---:|---:|
| A | Dev | 10/15 | 12/15 | 43 | 3,607 giây | 0 |
| A | Test | 3/5 | 3/5 | 43 | dùng lại collection | 0 |
| B | Dev | 10/15 | 12/15 | 43 | 1,837 giây | 0 |
| B | Test | 3/5 | 4/5 | 43 | dùng lại collection | 0 |
| C | Dev | 10/15 | 13/15 | 43 | dùng chung B | 0 |
| C | Test | 3/5 | 5/5 | 43 | dùng chung B | 0 |

\* A: 0,578 + 2,448 + 0,581 giây; B: 0,150 + 1,387 + 0,300 giây. Không gồm tải model 40,912 giây hoặc tìm kiếm. Một lần đo local không đủ để kết luận hiệu năng tổng quát. Thời gian tạo vector cho 15 câu dev là 0,113 giây; tổng thời gian tìm dev của A/B/C là 0,099/0,096/0,089 giây.

A có độ dài 67–493 ký tự, trung bình 296,33; B có 90–463 ký tự, trung bình 282,37. Tổng ký tự A là 12.742, gồm phần lặp do overlap; B là 12.142. C dùng cùng chunk B. Số chunk của A và B bằng nhau trong corpus slide này, nhưng ranh giới văn bản không nhất thiết giống nhau.

### Coherence, metadata và grounding

| Cấu hình | Coherence trung bình /2 | Metadata khớp PDF và section được gán | Filter test tuân thủ | Grounding 0/1/2; trung bình /2 |
|---|---:|---:|---:|---|
| A | 1,9 (10 vị trí) | 15/15 | N/A | 1/1/3; 1,4 |
| B | 2,0 (10 vị trí) | 15/15 | N/A | 1/0/4; 1,6 |
| C | 2,0 (10 vị trí) | 15/15 | 2/2 câu có filter | 0/0/5; 2,0 |

Mẫu coherence chọn 10 trang nội dung đầu tiên theo thứ tự vật lý: 5, 14, 19–26; với mỗi trang lấy chunk đầu tiên chứa offset 0. C dùng chung chunk B. Trợ lý Codex nhận xét thang 0–2, có lý do từng chunk; học viên cần đọc lại vì đây không phải người chấm độc lập và mẫu có thiên lệch về các slide đầu.

Audit metadata đối chiếu 5 câu test × Top 3 cho từng cấu hình với văn bản trích xuất trực tiếp từ PDF, số trang, offset và section được gán theo nhóm trang. 15/15 là số bản ghi khớp trong phép kiểm tra này, không chứng minh tuyệt đối section luôn đúng ngữ nghĩa. Với C, cả 2 câu test có filter đều trả các chunk đúng giá trị section. Grounding do Codex nhận xét 0–2 cho từng câu theo độ đủ bằng chứng trong Top 3; không phải đánh giá độ chính xác câu trả lời LLM và cần học viên xác nhận.

Minh chứng local: `starter/results/sensor_run/dev/traces_dev.jsonl`, `evaluation/traces_test.jsonl`, `dev_exact_review.jsonl`, `test_exact_review.jsonl`, `coherence_review.jsonl`, `metadata_audit.jsonl`, `grounding_review.jsonl` và `review_summary.json` dưới `starter/results/sensor_run/`. Các nhãn `*_exact_review` là so khớp tự động; coherence/grounding là nhận xét của Codex. Do chưa rõ quyền tái phân phối, các file có nội dung trích dẫn chưa được đưa lên Git; cần thống nhất cách người chấm được phép truy cập.

## 4. Phân tích và kết luận

**A–B:** hai phương pháp đều tạo 43 chunk và cùng kết quả khớp nguyên văn trên dev. Trên test, B tìm được đủ gold trong Top 3 ở 4/5 câu so với 3/5 của A. SQ17, gold trang 36, là ví dụ: chunk A ở Top 3 bị cắt giữa câu mô tả ADC, còn B có một chunk đầy đủ ở Top 2. Đây là phép so sánh trên 5 câu, không đủ để suy rộng.

**B–C:** C chỉ khác B ở filter section. SQ20 yêu cầu phần giải thuật xử lý dữ liệu, gold ở trang 47; B trả các trang 40, 45, 46 và không khớp gold, còn C giới hạn đúng section và tìm được đoạn chuẩn hóa ở Top 2. Trên test, C tuân thủ filter 2/2 câu và khớp gold Top 3 là 5/5, so với 4/5 của B. Kết quả phụ thuộc phạm vi section được gán đúng và người hỏi cung cấp điều kiện trước truy xuất.

**Các lỗi khác:** SQ02, gold trang 14, không xuất hiện trong Top 3 dev của A/B/C; SQ04, gold trang 20, cũng không xuất hiện trong Top 3. Cần xem query, các đoạn cạnh tranh và chất lượng embedding tiếng Việt; không thể khẳng định nguyên nhân chỉ từ thứ hạng. Phép khớp nguyên văn cũng có thể bỏ sót bằng chứng tương đương.

**Lựa chọn:** C đã được chọn tạm từ dev trước test. Kết quả test phù hợp với giả thuyết filter hữu ích ở ví dụ SQ20, nhưng test nhỏ và chỉ 2 câu có filter; không kết luận C luôn tốt hơn. Hướng cải thiện: xác nhận quyền chia sẻ và 31 trang, nhờ người học chấm lại gold/coherence/grounding và audit section, tăng số câu hỏi đa dạng, kiểm tra những trang chứa sơ đồ, và ghi revision model chính xác.

## 5. Cách chạy và khai báo AI

Từ thư mục gốc dự án, sau khi cài `starter/requirements.txt`, đặt PDF của giảng viên đúng vị trí và có benchmark được phép truy cập:

```powershell
$env:HF_HOME = Join-Path (Get-Location) 'starter\.cache\huggingface'
$env:HF_HUB_OFFLINE = '1'
.\starter\.venv\Scripts\python.exe -m starter.src.sensor_prepare
.\starter\.venv\Scripts\python.exe -m starter.src.sensor_experiment retrieve-dev
```

Model cần tải trước nếu cache chưa có. Bộ test của lần chạy này đã được xem; không dùng lại để điều chỉnh rồi coi là đánh giá độc lập. Muốn chạy thử nghiệm mới sau điều chỉnh, tạo tập test mới chưa dùng và một thư mục kết quả mới. Chương trình có cơ chế ngăn ghi đè lựa chọn dev khi trace test đã tồn tại.
