# Day 06 · Data Ingestion Engineering

**Lab cá nhân** · **4 giờ** · **Dữ liệu tự chọn**

Biến tài liệu thành kho tri thức có thể truy xuất cho AI agent, rồi đo xem cách chuẩn bị dữ liệu nào hiệu quả nhất.

## Bài làm cá nhân: trạng thái và cách chạy

Kiểm tra cục bộ, không xuất văn bản nguồn: `.\starter\.venv\Scripts\python.exe -m starter.src.verify_sensor`. Báo cáo tại `starter/results/sensor_verification.json` ghi số ký tự và lựa chọn cũ cho từng trang; so khớp nguyên văn gold không chứng minh đáp án hay filter đúng. [Audit](AUDIT.md) ghi đối chiếu và các điểm còn thiếu.

**Trạng thái: đã có bản duyệt do Codex hỗ trợ; cần học viên hiểu và kiểm tra độc lập trước khi nộp.** PDF có 49 trang vật lý và 31 trang được chọn, đã đối chiếu nội dung chữ và ranh giới section; trang 19 ngắn và trang 44 là sơ đồ. Học viên xác nhận đã được cấp toàn quyền công khai tài liệu. Benchmark và trace được cung cấp trong repo; học viên cần kiểm tra các nhãn do Codex hỗ trợ. Bộ test đã được xem; nếu điều chỉnh theo test, cần chuẩn bị test mới chưa dùng để đánh giá độc lập.

Mã hiện dùng ChromaDB và model `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`. Tại PowerShell từ thư mục gốc, dùng Python tương thích và chạy:

```powershell
py -m venv starter\.venv
.\starter\.venv\Scripts\python.exe -m pip install -r starter\requirements.txt
$env:HF_HOME = Join-Path (Get-Location) 'starter\.cache\huggingface'
```

Đặt bài giảng cảm biến 49 trang tại `starter/data/documents.pdf` và benchmark đã kiểm chứng tại `starter/benchmark/sensor_questions.json`. PDF, benchmark, chunk, trace và các bảng review được cung cấp trong repo theo xác nhận quyền công khai của học viên. [Manifest](data/manifest.json) ghi trang được chọn và thông tin sử dụng. Người chấm cần được cung cấp quyền truy cập phù hợp để kiểm chứng. Sau khi có dữ liệu, chạy:

```powershell
.\starter\.venv\Scripts\python.exe -m starter.src.sensor_prepare
.\starter\.venv\Scripts\python.exe -m starter.src.sensor_experiment retrieve-dev
```

Model cần được tải lần đầu. Lịch sử kết quả hiện có được bảo vệ khỏi ghi đè; để chạy thí nghiệm mới cần cấu hình thư mục kết quả, log và collection version mới, cùng test chưa dùng. Sau `retrieve-dev`, chạy lần lượt `python -m starter.src.sensor_experiment select-dev` và `python -m starter.src.sensor_experiment retrieve-test` bằng cùng Python trong môi trường trên; các lệnh dừng nếu kết quả tương ứng đã tồn tại. Lần chạy mới khóa revision model `e8f8c211226b894fcb81acc59f3b34ba3efd5f42`; revision của lần chạy lịch sử không được ghi và không thể xác nhận từ cache. Lệnh thí nghiệm dùng collection riêng của corpus cảm biến và không chạy khi trace test của lần này đã tồn tại; không sử dụng test đã xem để điều chỉnh rồi coi là độc lập. Xem [báo cáo cá nhân](report/individual/2A202603552_NguyenThiThuyDung.md) để hiểu cấu hình, kết quả và giới hạn. Repo cung cấp dữ liệu và benchmark; kết quả số có thể khác do revision model của lần chạy cũ không được ghi.

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

## Minh chứng và việc cần người học xác nhận

- `starter/results/sensor_verification.json` là báo cáo cục bộ: 49 dòng trang, số ký tự, lựa chọn cũ và `NEEDS_VERIFICATION`; không coi text ngắn hoặc có chữ là tự động hợp lệ. Đối chiếu từng slide, nhất là trang 19 và 44, với quy tắc nội dung của GUIDE.
- Section 2.2, 2.3, 2.4 và 2.5 bắt đầu tại các trang 32, 36, 40 và 47; các trang 14, 19–31 và 44–46 không tự ghi số section nên mapping dựa vào vị trí. Bốn filter được đối chiếu với phần nêu trong câu hỏi. Mapping thí nghiệm cũ được giữ nguyên.
- Người học kiểm tra đáp án, đủ evidence và các nhãn coherence (10 vị trí), metadata (5 câu × top-3 mỗi cấu hình) và grounding (5 câu mỗi cấu hình), kèm lý do. Nhận xét của Codex là `PENDING_MANUAL_REVIEW`, không phải nhãn do người học chấm.
- PDF, benchmark, parsed pages, trace và bảng review được cung cấp trong repo; môi trường ảo, cache và cơ sở dữ liệu cục bộ vẫn bị ignore.
- Model revision của lần cũ là null; revision cache được báo cáo không chứng minh revision đã dùng. Tái lập chính xác bị hạn chế. Test đã được xem; không dùng nó để điều chỉnh rồi tuyên bố độc lập. Cần test mới chưa sử dụng nếu điều chỉnh.
- Chạy mới cần phiên bản riêng của output, log và Chroma collection (các hằng `OUT`, `LOG_PATH`, `COLLECTION_PREFIX`, `EVAL` trong các module tương ứng); không ghi đè dữ liệu cũ. `sensor_prepare` cũng từ chối ghi đè corpus đã parse. Giữ cùng cấu hình A/B/C, model và revision đã xác nhận, lưu hash corpus/benchmark và version dependencies.
- PostgreSQL/pgvector, Docker, `store.py` và `check_setup.py` là starter tham khảo của đề, không được pipeline cảm biến gọi; giữ lại để đối chiếu. Không xóa dữ liệu hoặc lịch sử cũ.

## Minh chứng và giới hạn kiểm chứng

PDF: `starter/data/documents.pdf`; câu hỏi: `starter/benchmark/sensor_questions.json`; trace và chunk: `starter/results/sensor_run/`; các bảng duyệt: `review/*.csv`. Các dòng retrieval là phép so khớp nguyên văn tự động, không phải nhãn semantic; coherence và grounding là nhận xét sơ bộ của Codex, metadata là kiểm tra tự động. 31 trang được Codex kiểm tra từ văn bản trích xuất, không phải xác nhận độc lập của người học hay giảng viên; trang 44 là sơ đồ và có thể thiếu thông tin hình ảnh. Test đã được xem và không còn là holdout độc lập. PostgreSQL và dotenv chỉ dùng trong starter tham khảo, không cần cho pipeline cảm biến; chúng vẫn được giữ trong requirements cho starter đó.
