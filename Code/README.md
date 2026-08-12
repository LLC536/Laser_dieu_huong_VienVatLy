HƯỚNG DẪN CÀI ĐẶT VÀ CHẠY CODE HỆ THỐNG LASER ĐIỀU HƯỚNG
=========================================================

1. CẤU TRÚC THƯ MỤC
- Arduino_Motor_Controller.ino : Code nạp cho bo mạch Arduino Nano.
- Python_Vision_Master.py      : Code chạy trên máy tính (nhận diện hình ảnh và ra lệnh).

---------------------------------------------------------
2. YÊU CẦU CHUẨN BỊ (MÔI TRƯỜNG)
- Phần cứng: 
  + Cắm dây cáp nối Arduino với máy tính. 
  + Kết nối Camera (Webcam) với máy tính.
- Môi trường Arduino:
  + Cài đặt thư viện: Mở Arduino IDE -> Sketch -> Include Library -> Manage Libraries -> Tìm và cài đặt thư viện "AccelStepper".
- Môi trường Python:
  + Cài đặt Python (phiên bản 3.x).
  + Mở Terminal/CMD và cài các thư viện sau:
    pip install opencv-python numpy pyserial

---------------------------------------------------------
3. CÁC BƯỚC CHẠY HỆ THỐNG
* Bước 1: Nạp code cho Arduino
- Mở file Arduino_Motor_Controller.ino.
- Chọn đúng board (Arduino Nano) và cổng COM hiện tại.
- Bấm Upload.
- Sau khi Upload xong, tắt hoàn toàn phần mềm Arduino IDE (để giải phóng cổng COM cho Python).

* Bước 2: Cấu hình cổng COM trong Python
- Mở file Python_Vision_Master.py bằng bất kỳ Editor nào (VS Code, Pycharm, Thonny...).
- Tìm dòng 7: CONG_COM = 'COM6' -> Đổi 'COM6' thành cổng COM thực tế của Arduino trên máy bạn.
- Đảm bảo Camera đang không bị phần mềm khác sử dụng (dòng may_anh = cv2.VideoCapture(1) - thay số 1 thành 0 nếu chỉ dùng 1 camera mặc định của máy).

* Bước 3: Chạy chương trình
- Run file Python_Vision_Master.py.
- Chờ vài giây để hệ thống nhận diện Camera. 
- Ngay khi lên hình, hệ thống sẽ TỰ ĐỘNG chạy quy trình quét lưới (Grid Calibration) để tính toán ma trận không gian. Lúc này KHÔNG che camera hay động vào giá đỡ cơ khí.
- Chờ đến khi màn hình hiển thị dòng chữ màu xanh: "SAN SANG! Click chuot de di chuyen."

---------------------------------------------------------
4. THAO TÁC SỬ DỤNG
- Điều hướng: Click chuột trái vào bất kỳ điểm nào trên khung hình camera, tia laser sẽ tự động tính toán số bước motor và bắn tới vị trí đó.

⚠️ LƯU Ý QUAN TRỌNG KHI KẾT THÚC CHƯƠNG TRÌNH
=========================================================
Động cơ bước là hệ thống hở, nếu tắt ngang (mất điện), động cơ sẽ quên vị trí gốc. Do đó, để lần chạy sau hệ thống không bị lỗi tọa độ, BẮT BUỘC thực hiện thao tác tắt như sau:

1. Nhấn phím 'r' trên bàn phím: Lệnh này sẽ yêu cầu mạch Arduino reset tọa độ, đưa cả 2 trục motor từ từ quay ngược về đúng vị trí gốc (0,0).
2. Chờ hệ thống dừng hẳn ở vị trí gốc.
3. Nhấn phím 'q' trên bàn phím: Để ngắt kết nối Camera an toàn, đóng cổng Serial và thoát phần mềm Python. 
4. Rút nguồn điện phần cứng.
