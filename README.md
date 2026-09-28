# Pipe Support Analysis Tool

Công cụ tính **giá đỡ (support) đường ống** bằng **phần tử hữu hạn khung phẳng**,
dành cho đường ống công nghệ — đặc biệt là LNG/NG.

Nhập kích thước ống, môi chất và bảo ôn → ra tải phân bố và khoảng cách gối đỡ →
dựng khung support bằng toạ độ → giải PTHH → ra nội lực, mức sử dụng từng thanh,
tải tối đa chịu được, và đề xuất về hình dáng support.

> ⚠️ Đây là công cụ **sàng lọc và định cỡ sơ bộ**. Hồ sơ thiết kế phát hành phải
> được kỹ sư có thẩm quyền kiểm tra độc lập. Xem mục *Giới hạn* ở cuối.

---

## Chạy chương trình

**Không cần cài thêm bất cứ thư viện nào.** Chỉ cần Python 3.10 trở lên, bản cài
mặc định trên Windows đã có sẵn `tkinter`.

```bash
python run.py
```

Trên Windows có thể bấm đúp vào `Chay chuong trinh.bat`.

Nếu máy chưa có Python, tải bản `.exe` ở mục **Releases** của repo này — chạy trực
tiếp, không cần cài gì.

---

## Có gì bên trong

### 1 · Ống & môi chất
Tra nhanh OD và chiều dày theo NPS/Schedule (ASME B36.10M / B36.19M), chọn vật liệu
ống, môi chất và bảo ôn. **Mọi ô đều sửa tay được** — bảng tra chỉ để điền nhanh.

Kết quả: tải phân bố `w` [N/mm] tách theo ống / môi chất / bảo ôn, rồi khoảng cách
gối đỡ lớn nhất theo **hai điều kiện độc lập**:

```
ứng suất :  w·L² / cm / Z  ≤  σ_cho_phép
độ võng  :  w·L⁴ / (cd·E·I) ≤  δ_cho_phép
```

Mặc định `σ = 15,9 MPa` và `δ = 2,5 mm` — đúng cơ sở mà ASME B31.1 Table 121.5 dùng
để lập bảng khoảng cách gối đỡ. Chương trình lấy giá trị nhỏ hơn và nói rõ điều kiện
nào quyết định. Nút *→ Dùng làm lực tác dụng* chuyển `N = w × L` thẳng sang bài toán
khung.

### 2 · Tiết diện thép
Ống tròn, hộp vuông/chữ nhật, chữ I/H, thép U, thép góc, chữ T, thép bản, tròn đặc.

**Mọi đặc trưng (A, Ix, Iy, Sx, Sy, Zx, r) đều được tính từ kích thước bạn nhập**,
không tra bảng — nên không có số liệu nào bị bịa. Các "preset" chỉ điền sẵn kích
thước danh nghĩa thường gặp và có cảnh báo phải đối chiếu catalogue.

Với thép góc, `r_min` được tính theo **trục chính v** chứ không phải trục song song
cạnh, nên độ mảnh không bị đánh giá thiếu.

### 3 · Khung support
Mỗi dòng là một thanh, khai báo bằng toạ độ hai đầu. **Hai thanh có toạ độ trùng
nhau thì tự động nối với nhau.** Thêm lực (độ lớn + góc), thêm gối tựa (ngàm / khớp
/ con lăn).

Nếu điểm đặt lực **không nằm trên thanh nào**, chương trình từ chối tính và chỉ ra
thanh gần nhất cách bao nhiêu — vì lực không thể truyền vào kết cấu ở chỗ không có
vật liệu.

Ô *Dự kiến* (Kéo / Nén) không dùng để tính; nó dùng để **đối chiếu**: nếu bạn khai
một thanh là giằng chịu kéo mà PTHH cho ra chịu nén, chương trình sẽ cảnh báo.

### 4 · Kết quả
Nội lực từng thanh, vị trí mặt cắt nguy hiểm (cả toạ độ dọc thanh và toạ độ toàn
cục), mức sử dụng, và **hệ số tải cho phép** — nhân với tải đang xét ra ngay
**tải tối đa chịu được**.

Đề xuất được suy từ chính con số tính ra, không phải lời khuyên chung: khi nào nên
thêm thanh chéo, khi nào nên đổi sang tiết diện kín, co ngót vì lạnh bao nhiêu mm,
vì sao cần cold shoe.

### 5 · Báo cáo
Toàn bộ số liệu đầu vào, nội lực, kiểm tra và kết luận dạng văn bản, lưu ra `.txt`.

### Tự chọn tiết diện
Thử lần lượt mọi tiết diện trong thư viện và **giải lại toàn bộ bài toán PTHH cho
từng phương án** (đổi độ cứng sẽ phân bố lại nội lực trong khung siêu tĩnh), rồi
chỉ ra phương án nhẹ nhất còn đạt.

---

## Phương pháp tính

### Phần tử hữu hạn
Phần tử dầm–cột **Euler–Bernoulli 2D**, 6 bậc tự do (`u`, `v`, `θ` tại mỗi nút), nút
cứng. Mỗi thanh vật lý được chia thành nhiều phần tử để bắt được biến thiên nội lực
và dạng mất ổn định. Có kể trọng lượng bản thân thanh dưới dạng tải phân bố đều với
lực ngàm hai đầu.

### Ổn định — bài toán trị riêng
Không dùng `KL/r` đoán tay cho cả khung. Chương trình lập **ma trận độ cứng hình
học** `Kg` từ chính lực dọc trục vừa giải ra, rồi giải

```
(K + λ·Kg)·φ = 0
```

`λ_cr` là hệ số tải tới hạn của **toàn khung** — `λ_cr = 2.5` nghĩa là kết cấu mất
ổn định khi tải hiện tại tăng 2,5 lần. Bài toán trị riêng được giải bằng phép lặp
luỹ thừa trên toán tử `L⁻¹(−Kg)L⁻ᵀ` với phân tích Cholesky của `K`, dịch phổ tối
thiểu. Cholesky không phân tích được ⇔ kết cấu thiếu liên kết — chương trình báo
đúng nguyên nhân đó thay vì ném lỗi số học.

### Kiểm tra thanh — ứng suất cho phép (ASD)
```
kéo     Ft = 0,6·Fy
uốn     Fb = 0,6·Fy
cắt     Fv = 0,4·Fy
nén     Fa = Fcr / 1,67,  Fcr theo AISC 360 chương E
            Fe = π²E/(KL/r)²
            KL/r ≤ 4,71·√(E/Fy) :  Fcr = 0,658^(Fy/Fe)·Fy
            ngược lại           :  Fcr = 0,877·Fe
tổ hợp  AISC H1-1
```
Cách này **thiên về an toàn** so với AISC 360 đầy đủ: không cộng dự trữ dẻo
(dùng `S` chứ không phải `Z`), không cộng điểm cho ổn định ngang.

### Kiểm chứng
`tests/verify_fem.py` so kết quả solver với nghiệm giải tích:

| Bài toán | Sai số |
|---|---|
| Công xôn + lực tập trung (chuyển vị, moment ngàm) | < 0,01 % |
| Công xôn + tải phân bố đều | < 0,01 % |
| Dầm đơn giản, lực giữa nhịp | < 0,01 % |
| Thanh kéo dọc trục | < 0,01 % |
| Euler, cột 2 đầu khớp | 0,001 % |
| Euler, cột ngàm – tự do | 0,000 % |
| Euler, cột ngàm – khớp | 0,015 % |
| Cân bằng phản lực khung | ~1e-9 N |

```bash
python tests/verify_fem.py
```

---

## Cấu trúc mã nguồn

```
run.py              khởi chạy
psat/linalg.py      đại số tuyến tính thuần Python (Cholesky, trị riêng)
psat/fem.py         phần tử hữu hạn khung phẳng: tĩnh học + ổn định
psat/sections.py    đặc trưng hình học tiết diện
psat/pipe.py        tải trọng ống, khoảng cách gối đỡ, co giãn nhiệt
psat/checks.py      kiểm tra thanh theo ASD
psat/analysis.py    điều phối: nhập liệu → mô hình → kiểm tra
psat/advice.py      đề xuất kỹ thuật
psat/report.py      xuất báo cáo
psat/draw.py        vẽ trên Tkinter Canvas
psat/ui.py          giao diện
psat/data.py        bảng tra: ống, vật liệu, môi chất, tiêu chuẩn
tests/verify_fem.py kiểm chứng solver
```

Không phụ thuộc gói ngoài nào. `numpy`, `scipy`, `matplotlib` đều **không** được
dùng — đại số tuyến tính và phần vẽ đều tự viết, để tool chạy được trên máy chỉ có
Python trần.

---

## Tiêu chuẩn tham chiếu

| Nhóm | Tiêu chuẩn |
|---|---|
| Đường ống công nghệ LNG | ASME B31.3; EN 1473; NFPA 59A; EN 13480 |
| Tuyến ống dẫn khí | ASME B31.8; API 5L |
| Giá đỡ | MSS SP-58; MSS SP-69; ASME B31.3 §321 |
| Khoảng cách gối đỡ | ASME B31.1 Table 121.5 |
| Thanh thép | AISC 360; EN 1993-1-1 |
| Kích thước ống | ASME B36.10M; B36.19M |

Bảng tra trong `psat/data.py` là **dữ liệu tham khảo để điền nhanh**, không thay thế
tiêu chuẩn gốc. Ứng suất cho phép của ống ở nhiệt độ thiết kế phải lấy từ ASME B31.3
Bảng A-1/A-2.

---

## Giới hạn

Mô hình là **khung phẳng 2D, nút cứng**. Không xét:

- xoắn, và tâm cắt lệch của thép U / thép góc
- ổn định ngang của dầm (LTB) và ổn định cục bộ của bản thành
- mỏi, tải trọng động, rung, động đất, gió
- liên kết bu-lông và mối hàn
- ứng suất do giãn nở nhiệt của ống truyền vào giá đỡ (chương trình chỉ *cảnh báo*
  về độ co ngót, không tính lực)

Tiết diện coi là đặc chắc. Kết quả dùng để sàng lọc phương án và định cỡ sơ bộ.
