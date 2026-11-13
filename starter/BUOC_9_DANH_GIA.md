# Bước 9 — đánh giá thử nghiệm (tạm thời)

Các kết quả dưới đây chỉ dùng cho bản thử kỹ thuật: corpus và giấy phép chưa được xác nhận. Không dùng làm số liệu cuối cho bài nộp. Người xem xét mẫu là trợ lý Codex, không độc lập với người xây pipeline; cần người học đọc lại và xác nhận. Tập test đã được truy vấn và xem kết quả trong lần thử này, nên không còn là tập test chưa từng xem cho bất kỳ lần điều chỉnh tiếp theo. Nếu thay corpus, model, cấu hình, tiêu chí hoặc điều chỉnh theo kết quả test, cần tạo tập test mới chưa dùng (nếu có thể) và báo cáo minh bạch.

## Chọn cấu hình trước khi xem kết quả test

Đối chiếu chính xác bằng chứng theo nguồn và trang trên dev: cả A/B/C đều đạt 10/15 ở top 1 và 13/15 ở top 3. Quy tắc lựa chọn đã lưu trước khi truy vấn test: ưu tiên Hit@3, sau đó Hit@1, sau đó ít chunk hơn; hòa tiếp thì theo thứ tự chữ cái. A được chọn vì có 267 chunk, so với 301 của B/C. Đây là lựa chọn tạm dựa trên phép khớp nguyên văn, không phải kết luận rằng A tốt hơn tổng thể.

## Retrieval: phép khớp nguyên văn bảo thủ

| Chiến lược | Dev top 1 | Dev top 3 | Test top 1 | Test top 3 |
|---|---:|---:|---:|---:|
| A | 10/15 | 13/15 | 2/5 | 2/5 |
| B | 10/15 | 13/15 | 3/5 | 4/5 |
| C | 10/15 | 13/15 | 3/5 | 4/5 |

Phép tính trên đòi hỏi toàn bộ đoạn gold nguyên văn (sau chuẩn hóa khoảng trắng) nằm trong một chunk đúng nguồn/trang. Đây là chỉ số bảo thủ, chưa thay thế việc chấm thủ công bằng chứng tương đương. Mỗi nhãn, chunk, vị trí và văn bản đều được lưu trong `results/evaluation/`. Nhãn âm tính cần người học kiểm tra trước khi coi là điểm chính thức. Ví dụ Q12, bằng chứng ở trang 19 bị cắt tại từ “service”; Q18 của A bị cắt trước các yếu tố xã hội. Q19 của A trả về nội dung tương tự trên trang 21, nhưng câu hỏi yêu cầu Table 1 và gold chỉ định trang 41: phép đo chính tính không trúng.

## Chấm mẫu và audit metadata

Chọn trước cùng 10 vị trí: offset 100 của đoạn được trích xuất đầu tiên ở các trang PDF 3–12, chọn chunk đầu tiên bao phủ vị trí; C dùng cùng chunk B. Điểm mạch lạc trung bình do Codex chấm (0–2): A 1,0/2; B 1,4/2; C 1,4/2. Nhiều chunk mở đầu giữa câu do trang PDF bị tách; mẫu nhỏ nên không thể khái quát. Điểm và lý do cho từng chunk trong `coherence_review.jsonl`.

Với 5 câu test cho mỗi cấu hình, grounding trung bình do Codex chấm: A 1,4/2 (0: 0 câu, 1: 3 câu, 2: 2 câu); B/C 1,6/2 (0: 1 câu, 1: 0 câu, 2: 4 câu). Grounding đo mức đủ bằng chứng của top 3, không đo đáp án LLM. Điểm và lý do trong `grounding_review.jsonl`.

Kiểm tra tự động từng kết quả top 3 so với đoạn nguồn đã trích xuất và offset: A/B/C đều khớp 15/15 bản ghi về source, trang, section và text. Đây chưa phải kiểm chứng độc lập đầy đủ với PDF gốc. Với C, 2/2 câu test có filter cho kết quả tuân thủ section; A/B không áp dụng filter nên N/A. Chi tiết trong `metadata_audit.jsonl`.

## Giới hạn và hai lỗi cụ thể

- Q16: A không truy xuất trang 23 chứa design probes/design games; B/C trả được bằng chứng ở top 1. Chunk A trên trang 15 chỉ nói chung về cách tiếp cận trực quan.
- Q18: A trả trang 24 ở top 2 nhưng chunk dừng trước điều kiện về các yếu tố xã hội; B/C trả đủ đoạn ở top 2. Ở C, filter không cải thiện thứ hạng so với B trong trường hợp này.
- C chỉ khác B ở filter; trong hai câu test có filter, kết quả đúng phạm vi nhưng chỉ với 5 câu test không thể suy rộng. Thời gian, kích thước và chi phí local xem `results/experiment_dev/summary.json`; tiền điện không đo.

Các file `dev_exact_review.jsonl` và `test_exact_review.jsonl` là phép so khớp tự động, không phải nhãn thủ công độc lập; `selection.json` lưu lựa chọn đã chốt trước truy vấn test. Các file coherence/grounding là nhận xét thủ công của trợ lý AI và cần người học kiểm tra lại.
