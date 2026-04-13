# QUY TRÌNH VẬN HÀNH KHO — STANDARD OPERATING PROCEDURE

Ban hành: 01/01/2024 | Phiên bản: 3.1 | Bộ phận: Warehouse Operations

## 1. QUY TRÌNH NHẬP KHO

- Kiểm tra tờ khai hải quan — `clearance_status` PHẢI = "cleared" trước khi nhập kho.

- Đối chiếu số kiện thực tế với số kiện trên manifest chuyến bay.

- Chụp ảnh tình trạng kiện hàng trước khi nhập (lưu vào hệ thống WMS).

- Cập nhật `item_status` = arrived_domestic_warehouse trong hệ thống.

- Xếp kiện hàng vào vị trí đúng theo `item_category` và `customer_tier`.

- Khu VIP và Gold: khu vực ưu tiên, dễ lấy, có kiểm soát nhiệt độ.

## 2. QUY TRÌNH ĐÓNG GÓI

- Chỉ đóng gói khi `item_status` = arrived_domestic_warehouse.

- Bắt buộc: `qc_checked` = true trước khi xuất kho.

- NV QC PHẢI KHÁC NV đóng gói (tránh xung đột lợi ích).

- Hàng is_fragile = true: bắt buộc dùng bubble wrap + thùng carton đôi + nhãn Dê Vỡ.

- Ghi nhận cân thực tế (`actual_weight_kg`) và cân thể tích (`volumetric_weight_kg`).

- Cân tính cước = MAX(actual, volumetric) — áp dụng cho cả cước quốc tế và nội địa.

- Sau đóng gói, cập nhật `item_status` = packed.

## 3. QUY TRÌNH ĐÓNG GÓI LẠI (REPACK)

- Lập yêu cầu repack (`repack_id`), ghi rõ lý do (`reason`).

- Repack phải có phê duyệt của quản lý kho (`approved_by`).

- Chụp ảnh TRƯỚC (`before_photo_url`) khi bắt đầu thực hiện.

- Lỗi của công ty: `repack_fee` = 0, khách không phát sinh phí.

- Khách yêu cầu: tính phí theo bảng giá (30.000 – 200.000 VND).

- Chụp ảnh SAU (`after_photo_url`) khi hoàn thành.

- Cập nhật `new_weight_kg`, `new_box_count` vào hệ thống.

## 4. QUY TRÌNH XUẤT KHO — GIAO NV VẬN CHUYỂN

- Tạo `delivery_id`, cập nhật `item_status` = dispatched.

- Bàn giao cho carrier: GHN, GHTK, Viettel Post, J&T, SPX...

- `carrier_tracking_code` PHẢI được cập nhật ngay sau bàn giao.

- COD chỉ thu khi `payment_status` = "pending" hoặc "partial".

- Giao hàng thất bại (`failed_attempt`): cập nhật `attempt_count` += 1.

- Sau 3 lần thất bại: đơn tự động về kho (`returning`), thông báo NV kinh doanh.

## 5. QUY TẮC CÂN NẶNG — TÍNH CƯỚC

- Cân thể tích = (Dài × Rộng × Cao) / 6000 (đơn vị cm, kết quả kg).

- Cước tính theo: chargeable_weight = MAX(actual\_weight, volumetric\_weight).

- Ví dụ: thùng 50×40×30cm — thể tích = 10kg. Thực tế 3kg — Tính 10kg.

- Một đơn nhiều kiện: tính cước độc lập từng kiện, KHÔNG cộng gộp.

- Sau repack: nếu cân thay đổi, tính cước theo cân mới (new\_weight\_kg).