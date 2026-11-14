# Báo cáo cá nhân — Day 06: Data Ingestion Engineering

**Học viên:** Nguyễn Thị Thùy Dung · **MSSV:** 2A202603552 · **Lớp:** L3A


## 1. Dữ liệu và pipeline

### Corpus và quyền sử dụng

Nguồn `SENSOR001` là bài giảng **Chương II: Xử lý dữ liệu cảm biến**, trên trang đầu ghi Đại học Kinh tế Quốc dân, Khoa Công nghệ thông tin. Theo xác nhận của học viên, tài liệu do giảng viên cung cấp và được phép sử dụng cho bài học. Ngày 13/11/2026, học viên xác nhận đã được cấp toàn quyền công khai tài liệu. PDF, benchmark, trace và bảng review được cung cấp cùng repo để người chấm đối chiếu. Chưa xác định URL tải gốc hay ngày nhận tài liệu; không tự suy đoán. Manifest: `data/manifest.json`.

PDF có **49 trang vật lý**. Chọn **31 trang** có nội dung chữ liên quan: trang 5, 14, 19–34 và 36–48, tổng **12.142 ký tự đã chuẩn hóa**. Không tính trang bìa, mục tiêu/mục lục, trang chủ yếu là hình không trích được nội dung chữ và trang thuật ngữ cuối. Các trang dạng liệt kê được tính khi chúng cung cấp phân loại, đặc trưng hoặc bước xử lý liên quan; học viên đã xác nhận theo bảng tổng hợp ngày 14/11/2026. Trang được đánh số vật lý từ 1. Đây là bài giảng dạng slide, nhiều trang ngắn.

### Parse, clean và metadata

PDF được đọc bằng `pypdf`; chuẩn hóa Unicode NFC, khoảng trắng và xuống dòng, bỏ soft hyphen. Mỗi trang được giữ tách biệt để truy nguồn. Các trang hình vẽ không trích xuất được chữ có ý nghĩa đã được loại khỏi corpus chữ; không có OCR. Một số dấu đầu dòng là ký tự đặc biệt và còn số trang trong văn bản, nên dữ liệu chưa hoàn toàn sạch.

Mỗi chunk giữ `document_id`, `source`, `page`, offset ký tự trong trang và `section`. Giá trị section được gán theo các nhóm trang của các mục 2.1–2.5 trong tài liệu; với trang không lặp tiêu đề, section dựa vào vị trí trong nhóm và đã được học viên xác nhận theo bảng tổng hợp. Trường `section` có ích khi người hỏi chỉ định phần, còn `page` và `source` hỗ trợ truy vết. Hạn chế là nhãn section theo phạm vi trang có thể sai nếu tài liệu được sắp xếp lại.

### Embedding và lưu trữ

- Model local: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, Sentence Transformers **6.3.0**, 384 chiều, chuẩn hóa vector. Lần chạy ghi model nhưng revision trong report là `null`; cache hiện tại trỏ tới `e8f8c211226b894fcb81acc59f3b34ba3efd5f42`. Mã cho lần chạy mới khóa revision cache này; không thể khẳng định đó là revision đã dùng trong lần chạy lịch sử.
- ChromaDB **1.5.9** với cosine distance, lưu bền vững tại `starter/storage/chroma/` trong lần chạy lịch sử (lần mới dùng `<output-dir>/chroma/`); A có collection riêng, B/C chung collection. Index HNSW là tìm kiếm xấp xỉ; cấu hình thực tế cần giữ khi chạy lại.
- Giới hạn **128 token** bao gồm token đặc biệt; trong lần chạy này A và B không có chunk vượt giới hạn.
- Chi phí dịch vụ embedding: **0**, chạy local; tiền điện và tài nguyên máy chưa đo.

## 2. Thiết kế thí nghiệm

| Cấu hình | Chia văn bản | Truy xuất |
|---|---|---|
| A | Tối đa 500 ký tự, overlap tối đa 50; rút ngắn để vừa 128 token | Top 3, không filter |
| B | Ưu tiên ranh giới đoạn/câu, tối đa 800 ký tự và 128 token | Top 3, không filter |
| C | Dùng chung chunk, vector và collection với B | Top 3, lọc `section` nếu câu hỏi chỉ rõ |

Các cấu hình dùng cùng 31 trang, model và câu hỏi. A–B thay chiến lược chunking; B–C chỉ thay filter. Không đưa gold source hay đáp án vào truy vấn hoặc filter.

Benchmark `starter/benchmark/sensor_questions.json` có **20 câu**, gồm **15 dev và 5 test**; 4 câu có filter, trong đó 2 câu test. Câu hỏi, đáp án và gold evidence được tạo từ tài liệu cảm biến, và đoạn evidence đã kiểm tra xuất hiện tại trang được ghi sau chuẩn hóa khoảng trắng. Benchmark được tạo trước khi chạy experiment này.

Trước khi truy vấn test, lựa chọn được ghi tại `artifacts/sensor_selection.json`: ưu tiên tỷ lệ khớp gold Top 3 trên dev, sau đó Top 1, sau đó ít chunk hơn. **C được chọn tạm** vì đạt 13/15 Top 3 trên dev, so với 12/15 của A/B. Đây là quy tắc dựa trên khớp nguyên văn; chưa chứng minh C tốt nhất trong mọi tình huống.

## 3. Kết quả

### Retrieval và tài nguyên

Các điểm sau dựa trên **duyệt ngữ nghĩa** đối với 180 chunk: một chunk trúng nếu tự chứa đủ thông tin trả lời, kể cả diễn đạt tương đương, trong ngữ cảnh của nó. Không gộp nhiều chunk thành một hit; các nhãn, lý do và kết quả khớp nguyên văn cũ được lưu trong `review/retrieval_review.csv`. Các nhãn do AI hỗ trợ đề xuất, được học viên xác nhận theo bảng tổng hợp ngày 14/11/2026. Việc xác nhận theo bảng tổng hợp không tương đương chấm độc lập từng chunk.

| Cấu hình | Split | Top 1 (n/N) | Top 3 (n/N) | Chunk | Tạo chunk + embedding + lưu* | Chi phí API |
|---|---|---:|---:|---:|---:|---:|
| A | Dev | 10/15 | 12/15 | 43 | 3,607 giây | 0 |
| A | Test | 3/5 | 4/5 | 43 | dùng lại collection | 0 |
| B | Dev | 10/15 | 12/15 | 43 | 1,837 giây | 0 |
| B | Test | 3/5 | 4/5 | 43 | dùng lại collection | 0 |
| C | Dev | 10/15 | 13/15 | 43 | dùng chung B | 0 |
| C | Test | 3/5 | 5/5 | 43 | dùng chung B | 0 |

\* A: 0,578 + 2,448 + 0,581 giây; B: 0,150 + 1,387 + 0,300 giây. Không gồm tải model 40,912 giây hoặc tìm kiếm. Một lần đo local không đủ để kết luận hiệu năng tổng quát. Thời gian tạo vector cho 15 câu dev là 0,113 giây; tổng thời gian tìm dev của A/B/C là 0,099/0,096/0,089 giây.

A có độ dài 67–493 ký tự, trung bình 296,33; B có 90–463 ký tự, trung bình 282,37. Tổng ký tự A là 12.742, gồm phần lặp do overlap; B là 12.142. C dùng cùng chunk B. Số chunk của A và B bằng nhau trong corpus slide này, nhưng ranh giới văn bản không nhất thiết giống nhau.

### Coherence, metadata và grounding


| Cấu hình | Coherence trung bình /2 | Metadata khớp PDF và section được gán | Filter test tuân thủ | Grounding 0/1/2; trung bình /2 |
|---|---:|---:|---:|---|
| A | 1,7 (10 vị trí) | 15/15 | 0/2 | 1/0/4; 1,6 |
| B | 1,8 (10 vị trí) | 15/15 | 1/2 | 1/0/4; 1,6 |
| C | 1,8 (10 vị trí) | 15/15 | 2/2 câu có filter | 0/0/5; 2,0 |

Mẫu coherence chọn 10 trang nội dung đầu tiên theo thứ tự vật lý: 5, 14, 19–26; với mỗi trang lấy chunk đầu tiên chứa offset 0. C dùng chung chunk B. Học viên chấm A và B từng mẫu, sau đó xác nhận 10 mẫu C theo bảng vì nội dung chunk trùng B.

Audit metadata đối chiếu 5 câu test × Top 3 cho từng cấu hình với văn bản trích xuất trực tiếp từ PDF, số trang, offset và section được gán theo nhóm trang. 15/15 là số bản ghi khớp trong phép kiểm tra này, không chứng minh tuyệt đối section luôn đúng ngữ nghĩa. Mẫu số đối chiếu phạm vi là hai câu test có yêu cầu section (SQ17, SQ20) cho cả ba cấu hình. A khớp 0/2, B khớp 1/2 dù không áp dụng bộ lọc. Với C, cả 2 câu test có filter đều trả các chunk đúng giá trị section. Grounding nhận xét 0–2 cho từng câu theo độ đủ bằng chứng trong Top 3; sau duyệt ngữ nghĩa, SQ17/A tăng từ 1 lên 2 vì chunk trang 36 đủ suy ra chiều ADC. Grounding đánh giá bằng chứng truy xuất, được học viên chấm từng câu và cấu hình. Tổng mới ở `artifacts/sensor_review_summary_semantic.json`; các file review lịch sử được giữ nguyên.

Trace dev kèm nhãn nguyên văn và trace test ở `starter/results/sensor_run/evaluation/dev_exact_review.jsonl` và `traces_test.jsonl` trong cùng thư mục. Bảng đối chiếu trang, gold, 180 kết quả retrieval và 90 dòng chấm coherence/grounding/metadata nằm trong `review/`. Các tỷ lệ ngữ nghĩa được tổng hợp trong `artifacts/sensor_semantic_metrics.json` và `artifacts/sensor_review_summary_semantic.json`.

## 4. Phân tích và kết luận

**A–B:** hai phương pháp đều tạo 43 chunk, cùng Hit@3 ngữ nghĩa 12/15 dev và 4/5 test. Với SQ17, A có đoạn trang 36 ở Top 3 tuy câu gold bị cắt nhưng vẫn nêu tín hiệu analog chuyển sang số và mở rộng ADC là Analog-to-Digital Converter; B có đoạn định nghĩa trực tiếp ở Top 2. Phép khớp nguyên văn lịch sử cho A 3/5 test, thấp hơn đánh giá ngữ nghĩa 4/5. Mẫu năm câu không đủ để suy rộng.

**B–C:** C chỉ khác B ở filter section. SQ20 yêu cầu phần giải thuật xử lý dữ liệu, gold ở trang 47; B trả các trang 40, 45, 46 và không khớp gold, còn C giới hạn đúng section và tìm được đoạn chuẩn hóa ở Top 2. Trên test, C tuân thủ filter 2/2 câu và đạt Hit@3 ngữ nghĩa 5/5, so với 4/5 của B. Kết quả phụ thuộc phạm vi section được gán đúng và người hỏi cung cấp điều kiện trước truy xuất.

**Các lỗi khác:** SQ02, gold trang 14, không xuất hiện trong Top 3 dev của A/B/C; SQ04, gold trang 20, cũng không xuất hiện trong Top 3. Cần xem query, các đoạn cạnh tranh và chất lượng embedding tiếng Việt; không thể khẳng định nguyên nhân chỉ từ thứ hạng. Phép khớp nguyên văn cũng có thể bỏ sót bằng chứng tương đương.

**Lựa chọn:** C đã được chọn tạm từ dev trước test. Kết quả test phù hợp với giả thuyết filter hữu ích ở ví dụ SQ20, nhưng test nhỏ và chỉ 2 câu có filter; không kết luận C luôn tốt hơn. Hướng cải thiện: mở rộng bộ câu hỏi, kiểm tra độc lập từng nhãn và ghi revision model cho các lần chạy mới.

## 5. Tái lập và sử dụng AI

Lệnh cài đặt, chạy bốn giai đoạn và đọc kết quả nằm trong [README](../../README.md). Test lịch sử đã được xem. Nếu tinh chỉnh tiếp, cần một tập mới để đo độc lập.

Đã xác nhận 31 trang, 20 gold và các nhãn evidence theo bảng tổng hợp. Grounding được chấm từng câu, coherence A và B được chấm từng mẫu, coherence C được xác nhận theo các mẫu B tương ứng. Metadata được xác nhận theo phép đối chiếu tự động. 
