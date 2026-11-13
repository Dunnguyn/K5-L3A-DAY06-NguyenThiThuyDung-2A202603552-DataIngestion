# Hướng dẫn học viên kiểm chứng — Day 06

Các bảng CSV lưu bằng UTF-8 có BOM để mở bằng Excel. Chọn Data → From Text/CSV nếu tiếng Việt hiển thị sai. Bật Wrap Text để đọc chunk nhiều dòng. Trang được đánh số theo **trang vật lý PDF, bắt đầu từ 1**. Các bảng đã được điền bởi Codex hoặc phép kiểm tra tự động, với người duyệt và phương pháp được ghi trong từng dòng; không phải xác nhận của học viên. `NEEDS_VERIFICATION` và `PENDING_MANUAL_REVIEW` không phải kết luận đạt. Lưu bản sao trước khi chỉnh sửa.

Các CSV chứa văn bản tài liệu, đáp án và trace và được cung cấp trong repo theo xác nhận của học viên về quyền công khai tài liệu. PDF nguồn: `starter/data/documents.pdf`; benchmark: `starter/benchmark/sensor_questions.json`; trace: `starter/results/sensor_run/dev/traces_dev.jsonl` và `starter/results/sensor_run/evaluation/traces_test.jsonl`. Nếu thiếu một file, trạng thái **BLOCKED**: xin đúng file từ học viên, không thay PDF hoặc tự tạo evidence. PDF được đối chiếu với SHA-256 trong `data/manifest.json` khi lập bảng.

## 1. Trang và section — page_review.csv

Mở PDF tại từng trang trong 31 trang được chọn trước đây. `noi_dung_tom_tat_trich_dau_trang` là hai dòng đầu trích từ PDF để định vị, không phải kết luận về nội dung cả trang. Đọc cả slide, hình và ngữ cảnh xung quanh; quyết định trang có nội dung hữu ích liên quan theo GUIDE hay chỉ là bìa, mục lục, trang trống hoặc tài liệu tham khảo. Đặc biệt xem các slide ngắn, sơ đồ, trang 19 và 44. Điền `xac_nhan_trang_hop_le`, `ly_do_hoc_vien` và người/ngày; không mặc định số ký tự khác 0 là hợp lệ. Đếm lại số trang được xác nhận; nếu dưới 30 thì yêu cầu corpus chưa đạt.

So sánh `section_da_gan` với tiêu đề và ngữ cảnh tài liệu; các trang không lặp tiêu đề cần kiểm tra ranh giới các mục. Điền `xac_nhan_section` và lý do. Section trong bảng là mapping đã dùng, chưa xác minh. Kiểm tra riêng nguồn, ngày tiếp cận, quyền sử dụng và quyền chia sẻ với người cung cấp; không suy đoán hoặc xem chữ trong manifest là giấy phép công khai.

## 2. Gold — gold_review.csv

Với mỗi câu, mở đúng nguồn/trang, đọc toàn bộ ngữ cảnh và kiểm tra đáp án có đúng, đoạn trích có thực sự nằm ở trang, có **đủ** hỗ trợ đáp án, kể cả điều kiện và ngoại lệ. Điền các cột xác nhận, lý do; nếu có nguồn tương đương hợp lệ, ghi nguồn/trang và đoạn liên quan. Với câu có filter, kiểm tra giá trị được câu hỏi hoặc ngữ cảnh cung cấp trước truy xuất và phù hợp section trong PDF; ghi N/A nếu không áp dụng. Nếu có sai sót, ghi lại vấn đề; không âm thầm thay benchmark cũ. Giữ nguyên phân chia 15 dev/5 test và lịch sử.

## 3. Retrieval — retrieval_review.csv

Mỗi dòng là một chunk trong top-3 của một câu và cấu hình, tổng 180 dòng. Xem cả ba rank cho từng câu, so sánh chunk với gold và PDF. Điền `nhan_evidence_du` (có/không), lý do và người/ngày; một chunk chỉ được coi là hit nếu đúng nguồn/trang và chứa **đủ** bằng chứng, hoặc là bằng chứng tương đương được xác nhận. Nếu bằng chứng bị chia nhiều chunk, ghi rõ và không coi là hit đơn chunk. `cosine_distance` thấp hơn là gần hơn; không phải điểm đúng. Thứ tự rank được lấy từ danh sách trace cũ. Giữ lại nhãn và lý do; exact match trước đây chỉ là gợi ý máy, không thay nhận xét này.

Tính Hit@1 = số câu có rank 1 đủ evidence / số câu; Evidence Hit@3 = số câu có ít nhất một chunk đủ evidence trong ba rank / số câu. Báo tử số và mẫu riêng cho A/B/C và dev/test. Khi dùng nguồn tương đương, nêu cơ sở xác nhận. Không sửa điểm để tăng kết quả.

## 4. Chấm thủ công — manual_scoring_review.csv

Lọc theo cột `nhom`. Mỗi mẫu cùng cấu hình có thông tin chunk/nguồn để đối chiếu; không dùng các nhận xét Codex trước đây như nhãn của học viên.

- **coherence**: 30 dòng = 10 vị trí đầu (offset 0 trên 10 trang được chọn đầu tiên) × A/B/C. Đọc trang và chunk; chấm `diem_0_1_2`: 0 bị cắt giữa ý hoặc thiếu chủ thể làm không hiểu; 1 hiểu một phần nhưng thiếu ngữ cảnh; 2 tự hiểu được và giữ trọn ý. Ghi lý do từng dòng, tính trung bình /2 theo cấu hình. B/C dùng cùng chunk nhưng vẫn có dòng riêng để đối chiếu.
- **metadata**: 45 dòng = 5 câu test × 3 rank × 3 cấu hình. So sánh `nguon`, `trang_pdf`, `section` với PDF và thông tin gốc; kiểm tra `document_id` và offset trong bảng retrieval tương ứng. Điền `metadata_du_va_dung`, lý do từng dòng; báo số bản ghi đủ **và đúng** / tổng bản ghi cho từng cấu hình. Với C có filter, điền `filter_tuan_thu` cho từng chunk, sau đó báo số câu có cả top-3 tuân thủ / số câu có filter. Không có filter thì N/A, không ghi 100%.
- **grounding**: 15 dòng = 5 câu test × A/B/C; mỗi ô chứa cả top-3 kèm nguồn/trang. Chấm `diem_0_1_2`: 0 không có bằng chứng; 1 có nhưng thiếu điều kiện hoặc ngữ cảnh cần thiết; 2 đủ để trả lời và truy nguồn. Ghi lý do; báo số lượng từng mức và điểm trung bình /2. Đây là chất lượng bằng chứng truy xuất, không phải độ chính xác câu trả lời LLM.

Sau khi duyệt, so sánh A–B về chunking và B–C về filter, cùng số chunk, thời gian, chi phí, ví dụ lỗi và đánh đổi từ artifacts. Nêu mẫu nhỏ, khả năng thiên lệch vì tác giả tự chấm và độ tin cậy section. Bộ test này đã được xem; không dùng để tinh chỉnh rồi gọi là holdout độc lập. Nếu điều chỉnh, cần test mới chưa dùng và phiên bản thí nghiệm riêng.

## 5. Trước khi nộp

Kiểm tra mọi hàng đã có quyết định và lý do phù hợp, kể cả các dòng không áp dụng. Đối chiếu lại các tổng và báo cáo năm khía cạnh theo GUIDE/BENCHMARK. Xác nhận quyền dùng và cách giảng viên truy cập các bảng, benchmark, PDF và trace. Không sửa artifacts hoặc báo cáo số chưa được chứng minh; học viên cần tự hiểu và kiểm tra kết quả trước khi nộp.
