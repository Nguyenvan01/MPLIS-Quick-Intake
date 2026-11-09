# CLAUDE.md — hướng dẫn cho Claude Code

Tool desktop Windows: đọc file Excel *Phiếu chuyển thông tin địa chính* và tạo mới hồ sơ tiếp nhận trên
MPLIS (hye.mplis.gov.vn) rồi chuyển quyền qua wizard (`docs/luong-thao-tac.md`). Việc cần làm theo thứ tự nằm trong `plan.md`.

## Đọc trước khi code
- `plan.md` — giai đoạn, task, tiêu chí xong. Làm task theo thứ tự, tick `[x]` khi xong.
- `docs/nghiep-vu.md` — quy tắc BR-01…BR-09. Code kiểm tra dữ liệu phải trích đúng mã BR.
- `docs/kien-truc.md` — 5 lớp, máy trạng thái, chống tạo trùng.
- `docs/wireframe.md` — đặc tả 8 màn hình M1–M8.
- `docs/locators/README.md` — locator do người dùng lấy; cách đọc bản ghi codegen.

## Lệnh
```
uv sync --all-groups                 # cài
uv run pytest -q                     # test (không cần mạng, không mở trình duyệt)
uv run tiep-nhan kiem-tra tests/data/phieu_mau_an_danh.xlsx
uv run tiep-nhan locator-todo        # còn locator nào chưa lấy
uv run tiep-nhan kiem-locator --section tiep_nhan     # mở Chromium thật
uv run tiep-nhan chay-thu <file>     # mở Chromium thật, điền form, KHÔNG lưu
uv run tiep-nhan gui
```

## Quy tắc kiến trúc (không phá)
- Gọi một chiều: `app → core → domain / mplis → infra`. `domain/` không import `mplis/`, `app/`, Playwright.
- `core/runner.py` chỉ biết `mplis/port.py::MplisPort`. Mọi thao tác web nằm trong `mplis/`.
- **Mọi locator nằm trong `config/locators.toml`**. Không viết chuỗi selector trong file `.py`.
- Locator ưu tiên `role` > `label` > `placeholder` > `text` > `test_id` > `css`. Không XPath dài.
- Chờ bằng `expect(...)` / `wait_for_*`, không `time.sleep`.
- Trạng thái hồ sơ chỉ đổi qua `StateStore.mark`. Trước khi bấm Lưu phải ghi `DANG_TAO`.
- Thêm hành vi cho Runner → thêm test trong `tests/test_runner.py` dùng `FakeMplis` trước.

## Quy tắc an toàn (bắt buộc)
- **Không đoán locator.** Gặp `TODO` hoặc không chắc → dừng và hỏi người dùng, hoặc ghi vào mục
  "Câu hỏi mở" của `plan.md`. Đừng tự bịa tên nhãn/nút.
- **Không bấm Lưu trên MPLIS thật** trừ khi người dùng nói rõ trong phiên này. Mặc định `dry_run=True`.
- Không commit dữ liệu thật: họ tên, CCCD, file Excel gốc, trace, ảnh chụp. Test chỉ dùng
  `tests/data/phieu_mau_an_danh.xlsx`. Bản ghi codegen phải xóa mật khẩu trước khi lưu vào repo.
- Không ghi CCCD đầy đủ ra log — dùng `infra/logging.py::che_cccd`.
- Mật khẩu chỉ qua `keyring`, không lưu file.

## Quy ước
- Chữ hiển thị, log, docs: tiếng Việt có dấu. Tên biến/hàm: tiếng Việt không dấu hoặc tiếng Anh, nhất quán file đang sửa.
- Python 3.13, type hints đầy đủ, `from __future__ import annotations`.
- Cấu hình người dùng sửa được (`danh_muc.toml`, `locators.toml`) đọc qua `infra/config.py::config_file`
  (ưu tiên bản trong `%APPDATA%\NhapPhieuMPLIS\`).
