# Luồng thao tác trên MPLIS

Đã chạy thật ngày 08/11/2026 với tài khoản có quyền bước Thụ lý, trường hợp vợ chồng, quy trình 1.012787 loại "từ 30 hồ sơ trở lên" (`_2`). Selector nằm trong `config/locators.toml`. Tài liệu này không chứa dữ liệu cá nhân.

| # | Màn | Thao tác | Lệnh chính |
|---|---|---|---|
| 1 | Tra cứu hồ sơ tiếp nhận | Chọn xã, tìm theo số thửa + tờ, tự so người nộp (MPLIS bỏ qua lọc giấy tờ) | `DangKyAjax/AdvancedSearchHoSoTiepNhan` |
| 2 | `/dc/TiepNhanHoSo` | Chọn xã, quy trình `_2` | `GetGiayToMauByMaQuyTrinh`, `GetNgayHenTra` |
| 3 | Tìm thửa đất | Tìm số thửa + tờ, tick dòng, Chọn | `TaiSanAjax/AdvancedSearchThuaDat`, `KiemTraNganChanThua` |
| 4 | Hộp "Cập nhật địa chỉ tài sản" | Chọn Không rồi ghi địa chỉ theo Excel | |
| 5 | Tìm người nộp | Tìm theo số giấy tờ; nhiều bản ghi thì chọn bản khớp họ tên và năm sinh | `ChuSoHuuAjax/AdvancedSearchCaNhan` |
| 6 | Form | Tick Một cửa, Lưu hồ sơ, xác nhận | `DangKyAjax/TiepNhanHoSo` |
| 7 | Popup GCN cũ | Chọn dòng, Chọn; popup tự đóng | `KiemTraNganChanThanhPhan…`, `AddGiayChungNhanVaoThanhPhanHoSo` |
| 8 | Quy trình xử lý | Tick "Đã xử lý", Chuyển phân công, chọn người ở bước 3 Thụ lý, Thực thi | `UpdateTacVuDaXuLy`, `WorkflowAjax/executeCommand` |
| 9 | Bước 1 wizard | Thêm → Cá nhân hoặc Vợ chồng, nhập người, Lưu | `CheckCaNhanIsExist`, `CheckExistVoChong`, `…TronGiayBuoc1` |
| 10 | Bước 2 | Hệ thống tự điền, Bước sau | `…TronGiayBuoc2` |
| 11 | Bước 3 | Sửa thửa: Thời hạn SD = Lâu dài | `CheckExistThuaDat` |
| 12 | Bước 3 | Thêm → Nhà riêng lẻ: loại, cấp, kết cấu, số nhà, diện tích, địa chỉ chính | |
| 13 | Bước 3 | Tick quyền sử dụng và sở hữu, Lưu thông tin đăng ký | `ValidateThongTinDangKyJson` |
| 14 | Bước 3, tab GCN | Thêm: VPĐK cấp, số phát hành, người ký, tick cả cây, Lưu | `CheckExistThongTinGiayChungNhan`, `AddTinhTrangSoPhatHanh`, `…Buoc3` |
| 15 | Bước 4 | Hoàn tất | `…Buoc4`, `UpdateTacVuDaXuLy` |
| 16 | Quy trình xử lý | Dự thảo giấy chứng nhận → chọn GCN → xem | |

## Điểm cần nhớ
- Quy trình `_1` không cho tài khoản `ltmung.nnmt` nhận bước Thụ lý; `_2` thì có, và bảng mới hiện đủ 7 tác vụ.
- Ô số (số thửa, năm sinh, diện tích sử dụng) không nhận `fill()` ổn định: đặt giá trị bằng script hoặc gõ từng phím, rồi kiểm tra lại.
- Ô số phát hành tự viết hoa. Số đã cấp sẽ bị từ chối: "đã được cấp phát cho giấy chứng nhận khác".
- Chữ trên MPLIS viết "từ 30 hồ sở trở lên".
