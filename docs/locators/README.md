# Lấy locator MPLIS

Locator nằm **duy nhất** trong `config/locators.toml`. Hiện toàn bộ là `TODO`. Bạn ghi lại thao tác thật,
Claude Code đọc bản ghi rồi điền file đó (plan.md, task 1.1).

## 1. Ghi 4 luồng bằng codegen

```powershell
uv run playwright codegen --channel msedge https://hye.mplis.gov.vn
```

Mỗi luồng ghi một file, chép nội dung khung bên phải của Playwright Inspector vào `docs/locators/raw/`:

| File | Làm tay trong Edge | Phủ các mục |
| --- | --- | --- |
| `01_dang_nhap.py` | Đăng xuất (nếu cần) → đăng nhập | `[login]` |
| `02_them_moi_nhanh.py` | Từ trang chủ mở form Thêm mới nhanh → click và gõ vào TỪNG ô cần điền (dùng dữ liệu giả) → thêm 1 người nhận → bấm Hủy. **Không bấm Lưu.** | `[them_moi_nhanh]`, `.truong`, `.nguoi` |
| `03_tra_cuu.py` | Mở màn tra cứu → tìm theo tờ + thửa (+ CCCD nếu có ô) → mở chi tiết một hồ sơ | `[tra_cuu]`, `.chi_tiet` |
| `04_luu.py` *(tùy chọn, 🔒)* | Chỉ khi được phép tạo thử 1 hồ sơ: bấm Lưu, chụp thông báo có mã hồ sơ | `nut_luu`, `thong_bao_ok`, `ma_ho_so_moi`, `mau_ma_ho_so` |

Mẹo: bật **Pick locator** trong Inspector rồi trỏ vào ô/nút để lấy locator mà không thao tác.

## 2. Xóa thông tin nhạy cảm trước khi lưu
- Xóa dòng `fill(...)` chứa mật khẩu; thay tài khoản bằng `"<tai_khoan>"`.
- Không dùng họ tên/CCCD thật khi gõ thử.

## 3. Ghi danh mục thật vào `docs/locators/danh_muc_options.md`
Với mỗi ô chọn (Loại nhà, Cấp nhà, Kết cấu, Thời hạn, Giới tính…), mở DevTools (F12) → Console:
```js
[...document.querySelector('<selector ô chọn>').options].map(o => o.text).join('\n')
```
Combobox không phải `<select>`: mở danh sách, chụp màn hình hoặc chép tay.

## 4. Bản ghi codegen → TOML (tham khảo cho Claude Code)

| Dòng codegen | `config/locators.toml` |
| --- | --- |
| `page.get_by_role("button", name="Lưu")` | `{ by = "role", role = "button", name = "Lưu" }` |
| `page.get_by_label("Số tờ")` | `{ by = "label", text = "Số tờ" }` |
| `page.get_by_placeholder("Nhập số thửa")` | `{ by = "placeholder", text = "Nhập số thửa" }` |
| `page.get_by_text("Đăng xuất")` | `{ by = "text", text = "Đăng xuất" }` |
| `page.locator("#txtSoTo")` | `{ by = "css", value = "#txtSoTo" }` |
| `….nth(1)` | thêm `nth = 1` |
| `page.frame_locator("#ifr")…` | ghi chú lại; cần sửa `BasePage` để vào iframe |

Kiểm tra từng màn hình:
```powershell
uv run tiep-nhan locator-todo
uv run tiep-nhan kiem-locator --section login
uv run tiep-nhan kiem-locator --section them_moi_nhanh.truong    # mở tới form trước khi Enter
```
