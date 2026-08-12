# Hệ thống Laser Điều hướng 2 Trục XY Tích hợp Xử lý ảnh

## 1. Tổng quan đề tài
Đây là dự án điều khiển hướng chiếu của tia laser bằng cách sử dụng 2 động cơ bước (trục X và Y) gắn gương phản xạ. Hệ thống nhận tọa độ từ camera và điều khiển động cơ quay để hướng tia laser đến vị trí cần thiết.

## 2. Phần cứng và Công nghệ sử dụng

**Phần cứng:**
- Mạch xử lý: Arduino Nano
- Mạch mở rộng: CNC Shield V4 + 2x driver A4988 
  *(Lưu ý phần cứng: Mạch CNC V4 này có lỗi thiết kế từ NSX là thiếu chân 5V cấp cho Jumper cấu hình vi bước (MS). Hiện tại động cơ đang phải chạy full-step. Cần hàn câu dây 5V dưới gầm mạch để chạy được 1/16 step, giúp hệ thống bớt ồn và di chuyển mượt hơn).*
- Cơ cấu: 2x Động cơ bước, module phát laser, gương phẳng.
- Cảm biến: Webcam.

**Phần mềm:**
- Code máy tính (Python 3): Dùng `OpenCV` để lọc màu, nhận diện tia laser và tính toán ma trận Homography; dùng `PySerial` để gửi lệnh xuống Arduino.
- Code Arduino (C++): Dùng thư viện `AccelStepper` và `MultiStepper` để nhận chuỗi tọa độ (ví dụ: `100,50`) và điều khiển motor chạy đến đích.

## 3. Mục đích của Repository
- Lưu trữ source code (Python & C++), tài liệu và báo cáo tổng kết trong quá trình thực tập đề tài.
