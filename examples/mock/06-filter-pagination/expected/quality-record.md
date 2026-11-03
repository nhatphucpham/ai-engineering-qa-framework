# MOCK-06 — Đáp án thiết kế, synthetic

Đã biết trước khi walkthrough. Không dùng file này làm input cho lượt review muốn kiểm tra khả năng tìm vấn đề mới.

| AC | Sau baseline tại head | Sau historical check/probe tại head |
|---|---|---|
| AC-01 — service lọc đúng | verified trong scope bằng baseline và source | verified trong scope service |
| AC-02 — UI reset trang | unverified; evidence reset chỉ ở base; diff gợi ý regression | failed: view giữ page=3, API nhận page=3 thay vì 1 |
| AC-03 — cache phân biệt category | unverified; baseline chỉ lặp cùng category hoặc thay page/size | failed: sau books page=1, tools page=1 nhận B1/B2 thay vì T1/T2 |
| AC-04 — pagination | verified trong scope fixed catalog/category bằng source và baseline | verified trong scope đó; không mở rộng claim sang mixed-category cache |
| AC-05 — category trống | Chuỗi rỗng verified; whitespace unverified do requirement chưa chốt | unverified toàn AC cho đến khi owner làm rõ phần còn lại |

Hai defect độc lập: thiếu reset tại `head/ui.py` và cache key thiếu category tại `head/api.py`. Check historical fail và probe reset fail cùng một defect, không cộng thành ba defect. Evidence base không chứng minh head; đây là observation về evidence, không phải defect code thứ ba.

Whitespace là requirement ambiguity, không có verdict pass/fail cho behavior đó. Không đòi thêm auth, tenant isolation, HTTP, invalid input hoặc TTL ngoài scope.

Hành động: developer sửa state và key trên snapshot riêng, thêm regression cho hai sequence; owner chốt whitespace rồi mới viết assertion expected tương ứng; reviewer kiểm tra evidence đúng head mới. Người thực hiện thật unknown, human decision pending. Xem [hồ sơ walkthrough và execution](../../../../pilot/mock/MOCK-06-review.md) để truy nguồn kết luận.
