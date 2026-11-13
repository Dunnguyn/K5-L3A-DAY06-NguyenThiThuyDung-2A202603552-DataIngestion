# Day 06 · Data Ingestion Engineering

**Lab cá nhân** · **4 giờ** · **Dữ liệu tự chọn**

Biến tài liệu thành kho tri thức có thể truy xuất cho AI agent, rồi đo xem cách chuẩn bị dữ liệu nào hiệu quả nhất.

## Bài làm cá nhân: trạng thái và cách chạy

**Trạng thái: bản thử, chưa sẵn sàng nộp.** Cần xác nhận tối thiểu 30 trang hữu ích, quyền sử dụng/chia sẻ nguồn, hoàn thiện manifest và người học kiểm tra lại các nhãn. Bộ test của lần thử đã được xem; nếu điều chỉnh theo test, cần chuẩn bị test mới chưa dùng nếu có thể. Kết quả trong báo cáo không phải số liệu cuối.

Mã hiện dùng ChromaDB và model `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`. Tại PowerShell từ thư mục gốc, dùng Python tương thích và chạy:

```powershell
py -m venv starter\.venv
.\starter\.venv\Scripts\python.exe -m pip install -r starter\requirements.txt
$env:HF_HOME = Join-Path (Get-Location) 'starter\.cache\huggingface'
```

Đặt tài liệu có quyền sử dụng tại `starter/data/documents.pdf` và bộ câu hỏi đã kiểm chứng tại `starter/benchmark/questions.json`. Các file này và các trace/chunk chứa văn bản nguồn được giữ ở máy, chưa đưa lên Git vì quyền chia sẻ chưa xác nhận. DOI trong [manifest tạm](data/manifest.json) nhận diện bài báo, không tự đảm bảo URL tải PDF hoặc quyền tái phân phối. Sau khi cung cấp dữ liệu hợp lệ, chạy:

```powershell
.\starter\.venv\Scripts\python.exe -m starter.src.ingestion starter/data/documents.pdf --output starter/data/parsed_pages.jsonl
.\starter\.venv\Scripts\python.exe -m starter.src.run
```

Model cần được tải lần đầu. Lệnh thí nghiệm tạo lại dữ liệu, đồng bộ collection A/B và ghi đè log/trace dev; test cần lựa chọn đã khóa và không được điều chỉnh theo kết quả test. Xem [báo cáo cá nhân](report/individual/2A202603552_NguyenThiThuyDung.md), [bước 8](starter/BUOC_8_THI_NGHIEM.md) và [bước 9](starter/BUOC_9_DANH_GIA.md) để hiểu đầu vào, giới hạn và cách đánh giá. Để nộp, cần cung cấp benchmark và minh chứng có quyền chia sẻ hoặc cách người chấm được phép truy cập; các file bỏ qua hiện khiến repo chưa tái lập đầy đủ nếu thiếu dữ liệu này.

| 📄 Dữ liệu | 🧩 Chiến lược | 🎯 Benchmark |
|---|---|---|
| Tối thiểu **30 trang nội dung** | Tối thiểu **3 cấu hình** | Tối thiểu **20 câu hỏi** |

## Bắt đầu nhanh

Dùng [starter PostgreSQL + pgvector](starter/README.md) để dựng database và hoàn thiện các hàm TODO, hoặc tự chọn vector store tương đương. Starter chỉ là khung: **bạn tự hiện thực pipeline và benchmark**.

## 1. Xây pipeline

![Đọc tài liệu, chuẩn hóa, chia chunk, tạo vector, lưu và kiểm tra](assets/ingestion-pipeline.svg)

Chọn tài liệu được phép sử dụng; giữ **ID tài liệu, nguồn, trang/vị trí** và metadata phù hợp. Dùng embedding model thật qua API hoặc chạy local; lưu và truy xuất bằng pgvector, Qdrant, Chroma hoặc một store tương đương.

## 2. So sánh và đánh giá

![Ba chiến lược được đánh giá trên cùng corpus và benchmark dev/test](assets/benchmark-workflow.svg)

Dùng cùng dữ liệu, model và câu hỏi cho cả ba cấu hình. Tách **15 câu dev / 5 câu test** trước khi chạy; chọn cấu hình trên dev, rồi đánh giá test sau khi cố định. Mỗi câu hỏi cần có đoạn bằng chứng và trang nguồn; thiết kế bộ câu hỏi và đánh giá theo [BENCHMARK.md](BENCHMARK.md).

Đánh giá theo năm khía cạnh: **độ chính xác truy xuất**, **tính mạch lạc của chunk**, **tính hữu dụng của metadata**, **chất lượng grounding** và **tác động của chiến lược dữ liệu**. Giải thích lựa chọn bằng kết quả, ví dụ lỗi và các đánh đổi.

## 3. Chuẩn bị bài nộp

1. Chạy pipeline và lưu cấu hình, kết quả top-3, trace cùng nhãn đánh giá thủ công.
2. Điền [thông tin học viên](STUDENT.md), [nhật ký thí nghiệm](artifacts/experiment_log.csv) và bản sao [mẫu báo cáo cá nhân](report/individual/MSSV_HoTen.md).
3. Kiểm tra mã nguồn, cách chạy, manifest dữ liệu và checklist trong [SUBMISSION.md](SUBMISSION.md).

## Tài liệu hướng dẫn

| Bạn cần tìm | Tài liệu |
|---|---|
| Setup baseline PostgreSQL + pgvector | [starter/README.md](starter/README.md) |
| Các bước làm và cách tính chỉ số | [GUIDE.md](GUIDE.md) |
| Tiến độ trong 4 giờ | [CHECKPOINTS.md](CHECKPOINTS.md) |
| Năm tiêu chí benchmark và bộ câu hỏi | [BENCHMARK.md](BENCHMARK.md) |
| Tiêu chí chấm điểm | [RUBRIC.md](RUBRIC.md) |
| Quy tắc sử dụng dữ liệu, AI và API | [RULES.md](RULES.md) |
| Cách nộp bài | [SUBMISSION.md](SUBMISSION.md) |

[data/format-example.json](data/format-example.json) chỉ minh họa định dạng, không phải corpus đủ điều kiện. Phần xử lý và benchmark do bạn tự hiện thực; không bắt buộc xây chatbot.
