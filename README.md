# Day 06 · Data Ingestion Engineering

**Lab cá nhân** · **4 giờ** · **Dữ liệu tự chọn**

Biến tài liệu thành kho tri thức có thể truy xuất cho AI agent, rồi đo xem cách chuẩn bị dữ liệu nào hiệu quả nhất.

## Bài làm cá nhân: trạng thái và cách chạy

**Trạng thái:** corpus bài giảng cảm biến đã chọn 31 trang nội dung; học viên xác nhận tài liệu do giảng viên cung cấp và được phép sử dụng. Cần học viên kiểm tra nhãn và xác nhận cách chia sẻ minh chứng với người chấm; chưa xác nhận quyền chia sẻ công khai. Bộ test đã được xem; nếu điều chỉnh theo test, cần chuẩn bị test mới chưa dùng nếu có thể.

Mã hiện dùng ChromaDB và model `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`. Tại PowerShell từ thư mục gốc, dùng Python tương thích và chạy:

```powershell
py -m venv starter\.venv
.\starter\.venv\Scripts\python.exe -m pip install -r starter\requirements.txt
$env:HF_HOME = Join-Path (Get-Location) 'starter\.cache\huggingface'
```

Đặt bài giảng cảm biến 49 trang tại `starter/data/documents.pdf` và benchmark đã kiểm chứng tại `starter/benchmark/sensor_questions.json`. Các file này và trace/chunk chứa văn bản nguồn được giữ ở máy vì quyền chia sẻ công khai chưa xác nhận. [Manifest](data/manifest.json) ghi trang được chọn và thông tin sử dụng. Người chấm cần được cung cấp quyền truy cập phù hợp để kiểm chứng. Sau khi có dữ liệu, chạy:

```powershell
.\starter\.venv\Scripts\python.exe -m starter.src.sensor_prepare
.\starter\.venv\Scripts\python.exe -m starter.src.sensor_experiment retrieve-dev
```

Model cần được tải lần đầu. Lệnh thí nghiệm dùng collection riêng của corpus cảm biến và không chạy khi trace test của lần này đã tồn tại; không sử dụng test đã xem để điều chỉnh rồi coi là độc lập. Xem [báo cáo cá nhân](report/individual/2A202603552_NguyenThiThuyDung.md) để hiểu cấu hình, kết quả và giới hạn. Các file bỏ qua hiện khiến repo chưa tái lập đầy đủ nếu người chấm chưa có dữ liệu và benchmark.

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
2. Điền [thông tin học viên](STUDENT.md), [nhật ký thí nghiệm](artifacts/experiment_log.csv) và [báo cáo cá nhân](report/individual/2A202603552_NguyenThiThuyDung.md); mẫu chung nằm ở [REPORT_TEMPLATE.md](REPORT_TEMPLATE.md).
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

[Manifest cảm biến](data/manifest.json) mô tả nguồn và các trang được chọn. Phần xử lý và benchmark do người học kiểm tra; không bắt buộc xây chatbot.
