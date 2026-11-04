# Wireframe M1–M8

Bản vẽ: https://claude.ai/artifact/QndsfoDxPfkD8YEqkD5LN8 (bấm Play để click qua thanh điều hướng).
Luồng chính: M2 Lô mới → M3 Kiểm tra → M4 Danh mục → M5 Chạy → M6 Kết quả. Thanh bên trái cố định.

| Mã | Màn hình | Thành phần | Hành động / quy tắc |
| --- | --- | --- | --- |
| M1 | Đăng nhập | Địa chỉ MPLIS, tài khoản, mật khẩu, "Nhớ mật khẩu" | Đăng nhập → M2. Có mã xác thực: để người dùng nhập trong cửa sổ Edge |
| M2 | Lô mới | Vùng kéo thả, thẻ file (số cột nhận diện, số dòng, cảnh báo cấu trúc), chọn sheet, dòng tiêu đề, chế độ gộp, bảng lô gần đây | "Kiểm tra dữ liệu →" |
| M3 | Kiểm tra dữ liệu | Băng cảnh báo cấu trúc (BR-08), 3 ô số Hợp lệ/Lỗi/Cảnh báo, bảng hồ sơ (STT, dòng, tờ/thửa, người nhận, CCCD↔năm sinh, kiểm tra), panel xem trước | Lỗi chặn > 0 thì không sang bước sau. "Tải lại file" |
| M4 | Ánh xạ danh mục | Bảng: trường, giá trị Excel, số hồ sơ, ô chọn giá trị MPLIS, trạng thái | Còn "Chưa ánh xạ" thì chặn chạy thật. Lưu vào `danh_muc.toml` của người dùng |
| M5 | Chạy | Chọn Chạy thử/Chạy thật, thanh tiến độ, bảng bước hiện tại từng hồ sơ, nhật ký, ảnh form | Chạy thật hỏi xác nhận. "Dừng sau hồ sơ này" |
| M6 | Kết quả | 4 ô số Thành công/Đã có sẵn/Cần kiểm tra/Lỗi, bảng có mã hồ sơ và ghi chú | Xuất Excel kết quả, mở thư mục log/trace, Ảnh, So sánh, Chạy lại |
| M7 | Lịch sử | Ô tìm (file, tờ/thửa, CCCD), bảng lô | Mở → M6, Chạy tiếp → M5 |
| M8 | Cài đặt | Kết nối (URL, timeout, làm chậm), Hồ sơ (gộp, cho chạy khi còn cảnh báo, tìm trùng), Trình duyệt (Edge ẩn, xóa mật khẩu, xóa phiên), Dữ liệu & phiên bản | Tự lưu |

Màu trạng thái: Thành công xanh lá, Đã có sẵn xanh dương, Cần kiểm tra cam, Lỗi đỏ, Chạy thử xanh dương nhạt;
luôn kèm chữ, không chỉ dựa vào màu.
