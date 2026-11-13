# Audit trước chỉnh sửa — 13/11/2026

Đối chiếu README, GUIDE, BENCHMARK, RUBRIC, SUBMISSION, CHECKPOINTS và starter với [đề gốc](https://github.com/VinUni-AI20k/K5-L3-Day06-DataIngestionEngineering). Git ban đầu: `main`, working tree sạch.

| Requirement | Current implementation | Status | Issue | Proposed fix |
|---|---|---|---|---|
| ≥30 trang nội dung | 49 trang vật lý, 31 trang được chọn | PARTIAL | Slide ngắn; tính hợp lệ chưa được người học xác nhận | Kiểm kê từng trang, để chờ duyệt |
| Manifest, quyền, nguồn | Hash và đường dẫn PDF | PARTIAL | Ngày truy cập và quyền chia sẻ chưa rõ | Không suy đoán; ghi trạng thái |
| Parse, clean, 2 chunk | pypdf, fixed và paragraph/token | PARTIAL | Section theo khoảng trang chưa xác nhận | Đối chiếu heading và báo trạng thái |
| A/B/C và persistence | Chroma cosine, B/C dùng chung | PARTIAL | Revision chưa khóa; rerun ghi đè | Bảo vệ lịch sử, ghi giới hạn |
| Benchmark 15/5 và filter | 20 câu, 4 filter, 2 test | PARTIAL | Gold và điều kiện filter cần người học đối chiếu | Kiểm tra cơ học và giữ chờ duyệt |
| Hit@1, Hit@3 và trace | Có trace và exact match | PARTIAL | Exact match không tương đương semantic; thiếu rank tường minh | Ghi rõ proxy và rank |
| Coherence, metadata, grounding | Nhận xét Codex và kiểm tra tự động | PARTIAL | Chưa phải nhãn người học; section chưa xác nhận | Đánh dấu PENDING_MANUAL_REVIEW, không tạo nhãn |
| Data strategy, dev/test | Chọn C theo dev, đã xem test | PARTIAL | Không xác minh độc lập lịch sử trước lần chạy; test không còn mới | Nêu giới hạn và giữ nguyên artifacts |
| Tái lập, nộp bài | README, report, artifacts | PARTIAL | PDF/benchmark/trace bị ignore; quyền truy cập cần phối hợp | Hướng dẫn cung cấp riêng |
| Starter pgvector | Mã starter gốc tách biệt với Chroma | OPTIONAL | Không thuộc pipeline cảm biến | Giữ làm tham khảo, ghi rõ |
