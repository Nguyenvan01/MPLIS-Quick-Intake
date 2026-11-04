# plan.md — kế hoạch triển khai

Mục tiêu: cán bộ chọn file phiếu chuyển → xem lỗi → chạy thử → chạy thật → nhận file kết quả có mã hồ sơ,
không bao giờ tạo trùng hồ sơ trên MPLIS. Tài liệu gốc: `docs/`. Tính năng F01–F16: `docs/tinh-nang.md`.

Ký hiệu: `[x]` xong · `[ ]` chưa · **👤** cần người dùng làm/cung cấp · **🔒** cần người dùng cho phép.

---

## Giai đoạn 0 — Khung repo (ĐÃ XONG trong bản khởi tạo)
- [x] Cấu trúc 5 lớp `app/ core/ domain/ mplis/ infra/` theo `docs/kien-truc.md`
- [x] Đọc Excel theo tên cột, cảnh báo ô gộp lấn dữ liệu và dòng lạc (`infra/excel_in.py`)
- [x] Model pydantic + BR-01…BR-08 (`domain/models.py`, `domain/rules.py`)
- [x] Gom hồ sơ 2 chế độ (`domain/gom_ho_so.py`), ánh xạ danh mục (`domain/danh_muc.py`)
- [x] StateStore SQLite + máy trạng thái 6 trạng thái (`core/state.py`)
- [x] Runner: tìm trùng → điền → Lưu → tra cứu lại; chạy thử; xử lý bị ngắt (`core/runner.py`)
- [x] `MplisPort` + `FakeMplis` + 25 test (`tests/`)
- [x] Khung Page Object + bộ đọc `config/locators.toml` (toàn bộ locator đang `TODO`)
- [x] CLI `kiem-tra`, `locator-todo`, `kiem-locator`, `chay-thu`; khung GUI; build PyInstaller + Inno Setup + CI
- [ ] `uv lock` rồi commit `uv.lock` (CI release dùng `--locked`)
- [ ] `uv run pytest -q` xanh trên máy Windows

## Giai đoạn 1 — 👤 Lấy locator và danh mục (người dùng)
Làm theo `docs/locators/README.md`. Kết quả cần có trong repo:
- [ ] 👤 `docs/locators/raw/*.py` — bản ghi codegen 4 luồng (đã xóa mật khẩu)
- [ ] 👤 `docs/locators/danh_muc_options.md` — danh sách option thật của các ô chọn
- [ ] 👤 Trả lời các câu hỏi mở bên dưới

**Task cho Claude Code sau khi có bản ghi:**
- [ ] 1.1 Điền `config/locators.toml` từ `docs/locators/raw/` (không đoán; ô nào bản ghi không có → hỏi)
- [ ] 1.2 Điền `config/danh_muc.toml` từ `danh_muc_options.md`
- [ ] 1.3 Sửa thứ tự thao tác trong `mplis/pages/*.py` cho khớp bản ghi (bỏ các comment `TODO(locators)`)
- [ ] 1.4 Nếu ô chọn là combobox tự viết (không phải `<select>`): sửa `BasePage.dien_o` kind=`select`
- Xong khi: `uv run tiep-nhan locator-todo` báo 0 (hoặc chỉ còn mục người dùng xác nhận là không dùng),
  `kiem-locator --section login` toàn ✓.

## Giai đoạn 2 — Nối với MPLIS thật, chỉ chạy thử
- [ ] 2.1 `kiem-locator` cho từng section: `login`, `them_moi_nhanh`, `them_moi_nhanh.truong`,
      `them_moi_nhanh.nguoi`, `tra_cuu`, `tra_cuu.chi_tiet` — toàn ✓
- [ ] 2.2 `chay-thu tests/data/phieu_mau_an_danh.xlsx` → 3 hồ sơ "Chạy thử", có ảnh form trong `%APPDATA%\NhapPhieuMPLIS\screenshots`
- [ ] 2.3 Tìm trùng (`TraCuuPage.tim`) trả `None` với hồ sơ chưa có, trả mã với hồ sơ đã có (👤 cho 1 mã hồ sơ thật để thử)
- [ ] 2.4 `TraCuuPage.doc` đọc đủ các khóa của `gia_tri_so_khop()`; so khớp hồ sơ có sẵn ra 0 lệch
- [ ] 2.5 Ghi lỗi có trace: cố ý làm sai một locator → dòng Lỗi + file trace mở được bằng `playwright show-trace`
- Xong khi: chạy thử cả file không lỗi, không có hồ sơ nào được lưu trên MPLIS.

## Giai đoạn 3 — 🔒 Chạy thật có kiểm soát
- [ ] 3.1 🔒 Tạo thật 1 hồ sơ (trên môi trường/tài khoản người dùng chỉ định) → Thành công + mã hồ sơ
- [ ] 3.2 🔒 Chạy lại cùng file → hồ sơ đó "Bỏ qua", số lần Lưu không tăng
- [ ] 3.3 🔒 Xóa file trạng thái rồi chạy lại → "Đã có sẵn" (tìm trùng trên web hoạt động)
- [ ] 3.4 `infra/excel_out.py` nối vào luồng: xuất `<file>_ket_qua.xlsx` (F10) + test
- [ ] 3.5 Đo thời gian/hồ sơ, ghi vào `docs/do-hieu-nang.md`; bỏ mọi chờ thừa

## Giai đoạn 4 — Giao diện M1–M8 (`docs/wireframe.md`)
- [ ] 4.1 M1 Đăng nhập (F01) — keyring, giữ phiên Edge
- [ ] 4.2 M2 Lô mới (F02, F14) — kéo thả file, chọn sheet, chế độ gộp
- [ ] 4.3 M3 Kiểm tra dữ liệu (F03, F05) — bảng hồ sơ, panel xem trước, nhóm lỗi theo BR
- [ ] 4.4 M4 Ánh xạ danh mục (F04) — sửa và lưu `%APPDATA%\…\danh_muc.toml`; chặn chạy thật khi còn BR-05
- [ ] 4.5 M5 Chạy (F06–F09) — Worker QThread, tiến độ, Dừng sau hồ sơ hiện tại, nhật ký, ảnh form
- [ ] 4.6 M6 Kết quả (F10–F12) — xuất Excel, mở trace/ảnh, Chạy lại dòng chọn (`StateStore.reset`)
- [ ] 4.7 M7 Lịch sử (F13) — cần bảng `lo` trong SQLite (thêm vào `core/state.py` + test)
- [ ] 4.8 M8 Cài đặt (F14) — các trường của `infra/config.py::Settings`
- [ ] 4.9 Test UI cơ bản bằng pytest-qt (mở cửa sổ, chuyển màn hình, nạp file mẫu)

## Giai đoạn 5 — Đóng gói và phát hành
- [ ] 5.1 `build.ps1` chạy được trên Windows sạch (chỉ có Edge), app mở và chạy thử được
- [ ] 5.2 Bộ cài không cần quyền admin; gỡ cài đặt giữ `%APPDATA%\NhapPhieuMPLIS`
- [ ] 5.3 Gắn tag `v0.1.0` → GitHub Actions đính Setup.exe vào Release

## Sau (không làm khi chưa được yêu cầu)
- F15 tự khai báo cột khi mẫu Excel khác
- F16 `mplis/api_adapter.py` gọi thẳng request của nút Lưu — 🔒 chỉ khi đơn vị quản lý MPLIS đồng ý

---

## Câu hỏi mở (👤 trả lời ngay dưới mỗi câu)
1. Mỗi dòng Excel là một hồ sơ, hay các dòng cùng *Mã đầu vào* gộp thành một hồ sơ? (mặc định đang là mỗi dòng)
2. *Mã đầu vào* (vd H31.36-260316-0024) nhập vào ô nào trên form, hay là mã do MPLIS sinh?
3. Màn tra cứu tìm được theo tờ + thửa + CCCD không? Nếu không, khóa tìm trùng là gì?
4. STT 1 của file mẫu mất Mẫu nhà, Phân loại đường, Cán bộ XL do ô gộp: lấy ở dòng 9 hay để trống?
5. Thiếu Mã phát hành / Thời hạn: vẫn tạo hồ sơ (cảnh báo) hay chặn?
6. Mẫu nhà, Phân loại đường, Cán bộ XL có điền lên form Thêm mới nhanh không? (hiện chưa ánh xạ vào form)
7. Có môi trường MPLIS thử nghiệm để chạy thật ở Giai đoạn 3 không?
