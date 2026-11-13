# Bước 8: chạy ba cấu hình trên tập dev

Chạy từ thư mục gốc dự án:

```powershell
$env:HF_HOME = Join-Path (Get-Location) 'starter\.cache\huggingface'
$env:HF_HUB_OFFLINE = '1'
.\starter\.venv\Scripts\python.exe -m starter.src.run
```

Model phải được tải về trước. Chạy lại sẽ ghi đè các file trong `starter/results/experiment_dev/` và `artifacts/experiment_log.csv`, đồng thời đồng bộ lại hai collection `day06_experiment_a` và `day06_experiment_b`. Không đặt dữ liệu khác cần giữ vào hai collection đó. Các cột điểm được để trống vì chưa chấm evidence.

- A: cửa sổ cố định tối đa 500 ký tự, chồng lấn tối đa 50 ký tự; rút ngắn nếu vượt giới hạn token.
- B: ưu tiên đoạn/câu, tối đa 800 ký tự và 128 token.
- C: cùng chunk, vector và collection với B; chỉ thêm filter section khi câu hỏi cung cấp.

Chương trình dùng cùng corpus, model và 15 câu dev cho ba cấu hình. Kết quả trong `traces_dev.jsonl` gồm câu hỏi, gold, filter đã áp dụng và top 3 có ID, văn bản, metadata và cosine distance. `summary.json` ghi thống kê chunk, thời gian, phiên bản và chi phí chạy local. Chưa chấm Hit@1/Hit@3 hoặc chất lượng evidence; việc đó thuộc bước 9. Các câu test chưa được truy vấn; cần chốt tiêu chí chọn và cấu hình trước khi chạy test.

Kết quả hiện là bản thử kỹ thuật: corpus vẫn gồm cả bìa, tài liệu tham khảo và phần phản biện, chưa xác nhận đủ 30 trang hợp lệ hoặc quyền sử dụng. Sau khi kiểm tra và chốt corpus, tạo lại dữ liệu và chạy lại thí nghiệm. Không dùng kết quả tạm này làm số liệu cuối cùng.
