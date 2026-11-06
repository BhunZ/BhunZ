# Design brief — "Ink & Signal" · v2

> Prompt tôi tự viết cho chính mình, đã sửa theo góp ý vòng 1.
> Những thay đổi so với v1 được đánh dấu **[v2]**.

## Prompt

Thiết kế profile GitHub cho **BhunZ (Bao Hung Nguyen)**, data engineer, theo concept **"Ink & Signal"**:
nét mực viết tay (con người) gặp tín hiệu từ dữ liệu (máy móc). Tinh thần là **một tờ ấn phẩm in đen trắng
cao cấp**: tiết chế, nhiều khoảng thở, mỗi chữ trên trang phải có lý do để ở đó.
**[v2]** Giọng văn chuyên nghiệp: không viết những câu hiển nhiên ("pipelines that check their own work"),
không câu đùa nhạt ("Now: …"). Chỗ duy nhất được phép chơi chữ là slogan.

### Bảng màu (giữ nguyên)
Chỉ đen, trắng, các bậc xám. Màu "nhấn" duy nhất là độ sáng.
Ink `#050505` · Charcoal `#0F0F0F` · Graphite `#1A1A1A` · Rule `#2A2A2A` · Ash `#6E6E6E` · Silver `#A8A8A8` · Paper `#EDEDEA` · White `#FFFFFF`.
Gradient đóng vai ánh sáng: spotlight trên nền đen, chrome cho tên, hairline tan dần. Lớp film grain mỏng.

### Typography (giữ nguyên, tăng cỡ chữ)
Serif (Georgia, có nghiêng) cho giọng con người. Mono in hoa giãn chữ cho nhãn và số liệu.
**[v2]** GitHub thu nhỏ ảnh còn khoảng 830px (thẻ đôi chỉ còn ~400px), nên **không chữ nào nhỏ hơn 13px
sau khi thu nhỏ**. Chữ đọc (mô tả, giới thiệu) dùng Paper `#EDEDEA`, không dùng xám tối.

### 1 · Hero banner [v2]
- Bên trái: nhãn nhỏ `Nº 01`, tên **Bao Hung / *Nguyen*** ánh chrome, một dòng vai trò mono in hoa,
  rồi **slogan** (serif nghiêng, to vừa, có dấu ngoặc kép kiểu trích dẫn) và dấu ấn "bh".
  Bỏ hẳn câu tagline cũ.
- Bên phải, thay ridgeline bằng **"Galaxy of 365 days"**: một thiên hà xoắn ốc, mỗi ngày trong năm là một
  ngôi sao nằm trên cánh xoắn theo thứ tự thời gian (từ lõi ra ngoài). Ngày không commit chỉ là bụi sao mờ;
  ngày có commit thành ngôi sao, càng nhiều commit càng sáng và càng có quầng sáng (glow).
  Phía sau là trường sao ngẫu nhiên (seed cố định), vài vòng quỹ đạo mảnh, lõi thiên hà là gradient sáng.
  Sao nhấp nháy rất chậm, cả thiên hà xoay cực chậm (một vòng khoảng 4 phút) để không gây rối mắt.
  Không có chú thích kiểu "fig. 1"; chỉ có một dòng nhãn mono nhỏ: `365 DAYS · 1 STAR EACH`.
- Dải số liệu ở đáy giữ nguyên (contributions · active days · peak · thành phố).

### 2 · Slogan [v2]
Chơi chữ kiểu *"If February didn't March, April May"*: một câu nghe như thơ, đọc lần hai mới thấy là
thuật ngữ data. **Đã chọn: số 4.** Các gợi ý ban đầu:
1. *"The universe is append-only."* (ăn khớp với thiên hà: không thứ gì bị xoá, chỉ được ghi thêm)
2. *"Ad astra, per data."* (chơi chữ câu Latin *ad astra per aspera*: tới các vì sao, qua dữ liệu)
3. *"I connect the dots, then LEFT JOIN the rest."*
4. *"Stream of consciousness, batch of conscience."*
5. *"Stars are just data points that learned to glow."*

### 3 · Dấu ấn "bh" [v4: thay chữ ký thật]
**Không bao giờ đưa chữ ký pháp lý lên repo public**: một bản vector sát nét, kèm animation lộ cả thứ tự nét,
là khuôn mẫu hoàn hảo cho người muốn giả mạo, và lịch sử git không xoá sạch được.
Thay vào đó dùng một **artist mark** vẽ tay từ đầu, không liên quan gì đến chữ ký thật:
chữ "bh" viết thường liền một nét, kết thúc bằng nét lượn và một **ngôi sao bốn cánh** (nối với chủ đề vũ trụ).
Nét đơn, mượt, đầu tròn; hiệu ứng tự viết ra từng nét. Định nghĩa trong `marks.py`.
Xuất hiện ở hero (dưới slogan) và footer (như lời ký kết thúc).

### 4 · In Brief [v2: dễ đọc hơn]
- Bỏ dòng "Now: …" và chữ ký trong khung này.
- Một đoạn giới thiệu ngắn hơn (2 câu), chữ serif 22px, màu Paper.
- Thay bảng có đường chấm bằng **lưới 3 × 2**: mỗi ô gồm nhãn mono nhỏ ở trên và giá trị serif lớn ở dưới
  (Based · Study · Focus · Also · Stack · Open to). Đọc lướt như card visit.

### 5 · Selected Work [v2: dễ đọc hơn]
- Thẻ cao hơn (440 × 250), ít chi tiết hơn: bỏ mã vạch và hiệu ứng ánh lướt.
- Tên dự án serif 26px. Mô tả **sans 15px, màu Paper, tối đa 3 dòng**, viết lại cho ngắn và rõ.
- Dòng công nghệ mono 11.5px màu Silver, tối đa 4 mục. Nhãn loại (MLOPS, RAG…) giữ ở góc phải.
- Số sao chỉ hiện khi > 0.

### 6 · The Year, After Dark [v3: thay thành phố isometric]
Một **thành phố về đêm dưới bầu trời sao**, cùng vũ trụ với banner:
- Mỗi tuần là một tòa nhà (53 tòa), cao theo số commit tuần đó; **mỗi ô cửa sáng là một commit**.
- Phía sau là lớp skyline xa mờ để có chiều sâu; bầu trời có sao nhấp nháy, trăng tròn xám bạc, sao băng thỉnh thoảng bay qua.
- Năm tòa cao nhất có ăng-ten với đèn nháy; tuần đỉnh có nhãn `PEAK · WEEK OF …`.
- Mặt nước phản chiếu skyline (mờ dần, gợn sóng chạy chậm).
- Chuyển động: các tòa nhà mọc lên lần lượt, đèn cửa sổ bật dần, vài ô chập chờn.

### 7 · Chuyển động cho các phần còn lại [v3]
Cả trang phải "thở" nhưng vẫn tiết chế, cùng một ngôn ngữ vũ trụ:
- **Header:** mỗi mục là một dải đen riêng (đọc được cả ở giao diện sáng); số outline tự vẽ ra,
  một đốm sáng chạy dọc đường kẻ, sao lấm tấm phía sau.
- **In Brief:** quầng sáng nền trôi chậm, sao nhấp nháy, sao băng; các ô hiện lần lượt, mỗi nhãn có một chấm sao.
- **Selected Work:** mỗi thẻ có biểu tượng quỹ đạo (một "mặt trăng" quay quanh, mỗi thẻ một tốc độ),
  vệt sáng quét chéo qua thẻ, sao nhấp nháy ở góc.
- **Toolkit:** một dải sáng mờ quét dọc qua các hàng như máy quét, chấm sao đầu mỗi hàng.
- **Ledger:** thanh ngôn ngữ mọc ra, có vệt sáng chạy dọc; sao ở góc.
- **Footer:** bầu trời sao, hai sao băng lệch nhịp, dấu ấn "bh" tự viết ra.

Tất cả SVG do `generate.py` sinh ra, GitHub Action làm mới mỗi ngày.

### Tránh
Màu neon, emoji trang trí, câu hiển nhiên, câu đùa nhạt, chữ quá nhỏ, chi tiết trang trí không mang thông tin.
