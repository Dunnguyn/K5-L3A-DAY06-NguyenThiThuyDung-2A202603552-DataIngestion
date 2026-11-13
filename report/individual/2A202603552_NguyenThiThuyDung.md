# Báo cáo cá nhân — Day 06: Data Ingestion Engineering

**Học viên:** Nguyễn Thị Thùy Dung

**MSSV:** 2A202603552

**Lớp:** L3A

**Trạng thái:** Bản nháp dựa trên lần chạy thử ngày 13/11/2026, chưa đủ điều kiện nộp chính thức.

> **Việc cần hoàn tất:** xác nhận corpus có ít nhất 30 trang nội dung hợp lệ và quyền sử dụng/chia sẻ; hoàn thiện manifest; người học kiểm tra lại các nhãn và phân tích; chạy lại trên corpus đã chốt. Tập test của lần thử này đã được xem kết quả, nên cần tập test mới chưa dùng nếu thay đổi hoặc điều chỉnh dựa trên kết quả đó.

## 1. Dữ liệu và pipeline

### Nguồn, quyền và phạm vi

Corpus thử gồm một PDF, mã nguồn `DOC001`: Patrício và cộng sự, *Leveraging Service Design for Healthcare Transformation: Toward People-Centered, Integrated, and Technology-Enabled Healthcare Systems*, Journal of Service Management (2020), DOI [10.1108/JOSM-11-2019-0332](https://doi.org/10.1108/JOSM-11-2019-0332). Tên, thông tin xuất bản và DOI được đối chiếu với trang đầu của PDF. File dùng trong lần chạy là `starter/data/documents.pdf`.

Trang đầu PDF ghi bản tài liệu được bảo vệ bản quyền, cho phép sao chép cho mục đích nghiên cứu hoặc giáo dục theo điều kiện nêu trong tài liệu; các mục đích khác cần xin phép. **Chưa xác minh đầy đủ quyền tái phân phối PDF hoặc các file trace có chứa trích đoạn.** Không mặc định tài liệu công khai là được phép đưa lên GitHub. File mô tả nguồn hiện tại `starter/data/format-example.json` còn thiếu giấy phép đã kiểm chứng và danh sách trang hợp lệ; đây chưa phải manifest hoàn chỉnh. Cần xác nhận nguồn tải, quyền chia sẻ và cách cung cấp bằng chứng được phép trước khi nộp.

PDF có **54 trang vật lý**, tính từ trang đầu trong trình đọc PDF. Chương trình trích xuất được văn bản ở **53 trang** và ghi cảnh báo trang 54 chỉ còn chân trang/số dòng sau làm sạch. Đây **không phải** số trang nội dung hợp lệ. Dữ liệu thử còn bao gồm bìa, tài liệu tham khảo, hình/bảng và phần trả lời phản biện. Theo đề, phải loại trang bìa, trang trống, mục lục và trang chỉ có tài liệu tham khảo; cần kiểm tra phần còn lại có liên quan và lập danh sách trang được tính. Hiện **chưa chứng minh đạt tối thiểu 30 trang hữu ích**.

### Parse, clean và metadata

Sử dụng `pypdf` để trích xuất theo trang vật lý; chuẩn hóa Unicode NFC, khoảng trắng, xuống dòng và bỏ soft hyphen. Với PDF này, mã còn loại một số header/footer và số dòng nhận diện được. Một trang chứa ranh giới section được tách thành nhiều đoạn, nhưng các đoạn vẫn mang số trang gốc. Cảnh báo được lưu tại `starter/data/parsed_pages.log`.

Mỗi chunk giữ `document_id`, `source`, `page`, vị trí `start_char`/`end_char` trong đoạn đã trích xuất và `section` khi xác định được. `section` được lấy từ các tiêu đề hoặc vị trí hình/bảng đã xác định riêng trong tài liệu; cần kiểm tra lại với PDF gốc, nhất là trang có ranh giới. Trường `section` giúp giới hạn phạm vi tìm kiếm theo yêu cầu câu hỏi. Hạn chế: PDF có thể xuống dòng giữa từ hoặc bắt đầu trang giữa câu; không phải mọi ranh giới đoạn văn đều khôi phục được và một số đoạn không có section.

### Embedding, lưu trữ và cách chạy

- Model local: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`; thư viện Sentence Transformers **6.3.0**; vector **384 chiều**, chuẩn hóa. Lần chạy lưu tên model nhưng chưa ghi được mã revision cụ thể (`model_revision: null`), nên cần bổ sung trước khi tái lập chính thức.
- Bộ lưu: ChromaDB **1.5.9**, lưu bền vững tại `starter/storage/chroma/`; metric cosine distance. A có collection riêng; B và C dùng chung collection. Chưa xác nhận loại tìm kiếm exact/approximate trong bản báo cáo này.
- Giới hạn model: **128 token** gồm token đặc biệt. Các chunk A và B được kiểm tra không vượt giới hạn; C dùng cùng chunk B.
- Chạy local, không dùng dịch vụ embedding trả phí: chi phí API **0**; tiền điện và chi phí máy chưa đo.

Từ thư mục gốc dự án, sau khi cài `starter/requirements.txt` và có model trong cache:

```powershell
$env:HF_HOME = Join-Path (Get-Location) 'starter\.cache\huggingface'
$env:HF_HUB_OFFLINE = '1'
.\starter\.venv\Scripts\python.exe -m starter.src.run
```

Lệnh trên tạo lại thí nghiệm **dev**, đồng bộ hai collection A/B và ghi đè log, trace dev. Không chạy lại để thay đổi quyết định sau khi đã xem test mà vẫn coi bộ test cũ là độc lập. Hướng dẫn chi tiết ở `starter/BUOC_8_THI_NGHIEM.md` và `starter/BUOC_9_DANH_GIA.md`.

## 2. Cấu hình và benchmark

| Cấu hình | Chunking | Retrieval |
|---|---|---|
| A | Cửa sổ tối đa 500 ký tự, chồng lấn tối đa 50; rút ngắn khi vượt 128 token | Top 3, không filter |
| B | Ưu tiên đoạn/câu, tối đa 800 ký tự và 128 token; không overlap | Top 3, không filter |
| C | Cùng chunk, embedding và collection với B | Top 3, filter `section` khi câu hỏi cung cấp |

So sánh A–B khảo sát thay đổi chunking; B–C chỉ thay việc dùng filter. Cả ba dùng cùng dữ liệu đầu vào, embedding model và benchmark. Filter chỉ lấy từ yêu cầu phạm vi trong câu hỏi; không đưa gold source hay đáp án vào truy vấn.

Bộ câu hỏi `starter/benchmark/questions.json` có **20 câu**, chia trước **15 dev và 5 test**. Có 4 câu có filter, gồm 2 dev và 2 test. Mỗi câu có ID, đáp án dự kiến, mã nguồn, số trang PDF, trích đoạn evidence và filter nếu cần. Các đoạn gold đã được đối chiếu với PDF/trích xuất ở đúng trang; các trường hợp trả về bằng chứng tương đương vẫn cần người học xem lại.

Trước khi truy vấn test trong lần thử này, quy tắc chọn tạm thời được lưu tại `starter/results/evaluation/selection.json`: ưu tiên tỷ lệ trúng bằng chứng nguyên văn ở Top 3 trên dev, sau đó Top 1, sau đó ít chunk hơn, cuối cùng theo thứ tự chữ cái. Cả ba hòa về hai chỉ số dev; **A được chọn tạm** vì có 267 chunk, so với 301 của B/C. Quy tắc dựa trên phép khớp nguyên văn và số chunk; không kết luận A tốt hơn tổng thể.

## 3. Kết quả lần chạy thử

### Retrieval và tài nguyên

Bảng dưới đây là **số lần khớp nguyên văn bảo thủ**, chưa phải kết quả semantic đã được người chấm độc lập xác nhận. Một chunk được tính trúng nếu chứa toàn bộ gold quote sau chuẩn hóa khoảng trắng và đúng nguồn/trang. Bằng chứng tương đương không nguyên văn có thể bị bỏ sót; nếu bằng chứng bị chia qua nhiều chunk thì không tính là một hit đơn theo định nghĩa chính.

| Chiến lược | Split | Top 1 (n/N) | Top 3 (n/N) | Số chunk | Thời gian tạo chunk + embedding + lưu* | Chi phí API |
|---|---|---:|---:|---:|---:|---:|
| A | Dev | 10/15 | 13/15 | 267 | 13,92 giây | 0 |
| A | Test | 2/5 | 2/5 | 267 | dùng lại collection | 0 |
| B | Dev | 10/15 | 13/15 | 301 | 13,25 giây | 0 |
| B | Test | 3/5 | 4/5 | 301 | dùng lại collection | 0 |
| C | Dev | 10/15 | 13/15 | 301 | dùng chung B | 0 |
| C | Test | 3/5 | 4/5 | 301 | dùng chung B | 0 |

\* Tổng các thời gian đã làm tròn trong `summary.json`: A = 3,170 + 10,053 + 0,698; B = 2,019 + 10,448 + 0,778 giây. Không gồm tải model 26,723 giây hoặc thời gian truy vấn; đây là một lần đo trên máy hiện tại, không phải benchmark hiệu năng tổng quát. Tổng thời gian tìm 15 câu dev tương ứng A/B/C là 0,127/0,126/0,138 giây; thời gian tạo vector cho 15 câu là 0,181 giây dùng chung. C không tạo lại embedding riêng.

Phân bố chunk: A dài 52–500 ký tự, trung bình 436,02; B dài 15–688 ký tự, trung bình 352,05. Tổng ký tự của A là 116.417, gồm nội dung lặp do overlap; B là 105.967. C dùng cùng thống kê B. Cả hai có tối đa 128 token/chunk, không có chunk vượt giới hạn.

### Coherence, metadata và grounding

| Chiến lược | Coherence trung bình /2 | Metadata khớp dữ liệu đã trích xuất | Filter tuân thủ | Grounding 0/1/2; trung bình /2 |
|---|---:|---:|---:|---|
| A | 1,0 (10 vị trí) | 15/15 | N/A | 0/3/2; **1,4** |
| B | 1,4 (10 vị trí) | 15/15 | N/A | 1/0/4; **1,6** |
| C | 1,4 (10 vị trí) | 15/15 | 2/2 câu test có filter | 1/0/4; **1,6** |

Mẫu coherence chọn cùng 10 vị trí: offset 100 trong đoạn trích xuất đầu tiên của các trang vật lý 3–12, sau đó lấy chunk đầu tiên bao phủ vị trí. Thang: 0 không hiểu do thiếu ngữ cảnh; 1 hiểu một phần/thiếu ngữ cảnh; 2 tự hiểu và giữ trọn ý. Điểm do **trợ lý Codex nhận xét**, chưa được người chấm độc lập xác nhận. C dùng cùng chunk B nên cùng điểm coherence.

Audit metadata tự động đối chiếu 5 câu test × Top 3 cho mỗi cấu hình với `source`, trang, section, text và offset trong dữ liệu đã trích xuất; 15/15 không có nghĩa đã kiểm tra độc lập đầy đủ với PDF gốc. Filter được tính tuân thủ nếu tất cả kết quả Top 3 của câu có filter nằm trong section yêu cầu; A/B không dùng filter nên N/A. Grounding do Codex chấm thủ công 0–2 cho mỗi câu test: đo mức đủ và khả năng truy nguồn của Top 3, **không** đo độ chính xác câu trả lời LLM.

Minh chứng: `starter/results/experiment_dev/traces_dev.jsonl`, `starter/results/evaluation/traces_test.jsonl`, `dev_exact_review.jsonl`, `test_exact_review.jsonl`, `coherence_review.jsonl`, `metadata_audit.jsonl`, `grounding_review.jsonl` và `manual_review_summary.json` trong `starter/results/evaluation/`. Các file `*_exact_review.jsonl` là nhãn so khớp tự động; các nhãn coherence/grounding là nhận xét của Codex, không phải đánh giá độc lập của học viên.

## 4. Phân tích và kết luận

### A–B: tác động của chunking

Trên dev, cả hai có cùng số lần khớp nguyên văn Top 1/Top 3, nhưng mẫu coherence của B cao hơn và B tạo nhiều hơn 34 chunk. Trên test thử, B có 4/5 lần khớp Top 3 so với 2/5 của A; mẫu 5 câu quá nhỏ để kết luận tổng quát.

- **Q16 — gold trang 23:** A trả trang 15 ở Top 1, chỉ nêu cách tiếp cận trực quan nói chung, không nêu đủ design probes và design games; B trả nguyên bằng chứng ở Top 1.
- **Q18 — gold trang 24:** A tìm đúng trang ở Top 2 nhưng chunk bị cắt trước thông tin về social determinants; B trả đủ các nguồn dữ liệu ở Top 2. Đây là ví dụ ranh giới chunk có thể làm mất bằng chứng cần thiết.
- **Q12 — dev, gold trang 19:** đoạn B/C tìm được bị cắt gần cuối evidence, nên phép khớp nguyên văn không tính trúng; cần người học kiểm tra liệu nội dung còn lại đã đủ đáp án theo tiêu chí chấm hay chưa.

### B–C: tác động của metadata filter

C dùng đúng chunk và vector của B, chỉ lọc khi có `section`. Trong hai câu test có filter, kết quả C tuân thủ phạm vi 2/2; số lần khớp evidence của B và C bằng nhau trên cả dev lẫn test. Ở Q18, filter không đổi thứ hạng đoạn đủ bằng chứng. Với dữ liệu ít câu và chỉ hai điều kiện filter ở test, không thể kết luận filter luôn cải thiện retrieval.

Q19 yêu cầu Table 1 ở trang 41: A trả nội dung tương tự trên trang 21 nhưng không trả bảng được chỉ định. Theo gold hiện có, phép đo nguyên văn tính là không trúng; nhận xét grounding tạm cho A là 1/2 vì có thông tin gần đúng nhưng thiếu bảng cần truy nguồn. Cần kiểm tra trường hợp này khi chấm thủ công.

### Lựa chọn và hướng cải thiện

A là lựa chọn **đã khóa tạm thời trước test** theo quy tắc đã nêu, không thay đổi quyết định chỉ vì thấy B/C có điểm test thử cao hơn. Nếu chọn cho ứng dụng thật, cần xem thêm coherence, grounding, khả năng lọc và yêu cầu truy nguồn; số chunk ít không tự chứng minh chất lượng tốt hơn.

Các giới hạn chính: corpus và quyền chưa chốt; PDF có lỗi tách dòng/trang; số trang hữu ích chưa chứng minh; nhãn retrieval chủ yếu là khớp nguyên văn, còn coherence/grounding do AI nhận xét; audit metadata mới đối chiếu dữ liệu trích xuất; test chỉ có 5 câu và đã được xem; thời gian là một lần đo, chi phí điện chưa tính. Bước tiếp theo là kiểm tra nguồn và quyền, chọn đủ corpus hợp lệ, cải thiện phân đoạn theo token và ngữ cảnh, kiểm tra nhãn bằng người học, chuẩn bị test mới chưa dùng nếu điều chỉnh, rồi chạy lại và cập nhật báo cáo.

## 5. Khai báo sử dụng AI

Sử dụng Codex để hỗ trợ viết và giải thích pipeline, xây benchmark, chạy kiểm tra, phân tích kết quả và soạn báo cáo; Codex cũng đưa ra các nhãn coherence/grounding tạm. Các số trong báo cáo được lấy từ file kết quả đã chạy, không tự giả định. Người học cần tự đọc tài liệu nguồn, kiểm tra quyền, kiểm chứng nhãn và hiểu cách làm trước khi nộp; không xem nhận xét AI là đánh giá độc lập.
