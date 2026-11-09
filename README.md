# Thêm mới nhanh hồ sơ tiếp nhận MPLIS

Đọc file Excel *Phiếu chuyển thông tin địa chính*, kiểm tra theo quy tắc nghiệp vụ, rồi tạo hồ sơ tiếp nhận
trên MPLIS bằng Playwright + Chromium. Tra cứu lại từng hồ sơ trước khi ghi Thành công; chạy lại
không bao giờ tạo trùng.

```powershell
uv sync --all-groups
uv run pytest -q
uv run tiep-nhan kiem-tra tests\data\phieu_mau_an_danh.xlsx
```

| Tài liệu | Nội dung |
| --- | --- |
| `plan.md` | Kế hoạch, task, câu hỏi mở |
| `CLAUDE.md` | Quy tắc cho Claude Code |
| `docs/nghiep-vu.md` | Quy trình, dữ liệu phiếu chuyển, BR-01…BR-08 |
| `docs/tinh-nang.md` | F01–F16 |
| `docs/kien-truc.md` | Lớp, máy trạng thái, công nghệ |
| `docs/wireframe.md` | 8 màn hình M1–M8 |
| `docs/locators/README.md` | Cách lấy locator MPLIS |

Trạng thái hiện tại: lõi, kiểm tra dữ liệu và chống trùng đã có test; **locator MPLIS chưa lấy**
(`config/locators.toml` toàn `TODO`), giao diện mới là khung.
# MPLIS-Quick-Intake
