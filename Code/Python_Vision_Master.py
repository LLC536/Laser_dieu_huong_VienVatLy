import cv2
import numpy as np
import serial
import time

# --- CẤU HÌNH HỆ THỐNG ---
CONG_COM = 'COM6' 

# --- HÀM TÌM TỌA ĐỘ LASER ---
def tim_toa_do_laser(anh_dau_vao):
    # 1. Chuyển sang ảnh xám theo logic gốc
    anh_xam = cv2.cvtColor(anh_dau_vao, cv2.COLOR_BGR2GRAY)
    
    # 2. Bắt các điểm chói sáng (ngưỡng 245 rất chuẩn với ảnh này)
    _, mat_na_sang_nhat = cv2.threshold(anh_xam, 245, 255, cv2.THRESH_BINARY)
    
    # 3. Tìm danh sách các đốm sáng
    danh_sach_vien, _ = cv2.findContours(mat_na_sang_nhat, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if len(danh_sach_vien) > 0:
        # CẢI TIẾN: Sắp xếp các viền từ lớn đến bé để kiểm tra lần lượt.
        # Nếu dùng max(), lỡ có một mảng tường lóa sáng to hơn 400, hàm sẽ bỏ qua luôn tia laser nhỏ bé.
        danh_sach_vien_sap_xep = sorted(danh_sach_vien, key=cv2.contourArea, reverse=True)
        
        for vien_laser in danh_sach_vien_sap_xep:
            dien_tich = cv2.contourArea(vien_laser)
            
            # Lọc bằng diện tích (chuẩn logic của bạn)
            if 10 < dien_tich < 400: 
                chu_vi_vien = cv2.arcLength(vien_laser, True)
                
                if chu_vi_vien > 0:
                    # Lọc bằng độ tròn (chuẩn logic của bạn)
                    do_tron = 4 * np.pi * dien_tich / (chu_vi_vien * chu_vi_vien)
                    
                    if do_tron > 0.75:
                        (tam_x, tam_y), _ = cv2.minEnclosingCircle(vien_laser)
                        return int(tam_x), int(tam_y)
                        
    return None

# --- KHỞI TẠO SERIAL & CAMERA ---
try:
    bo_dieu_khien = serial.Serial(CONG_COM, 115200, timeout=0.01)
    time.sleep(2)
except Exception as e:
    print("Không thể kết nối Arduino! Lỗi:", e)
    exit()

may_anh = cv2.VideoCapture(1)
if not may_anh.isOpened(): exit()

print("Đang chờ camera ổn định...")
for _ in range(30): may_anh.read()

# --- BIẾN TOÀN CỤC ---
trang_thai = "START_GRID_CALIB"

danh_sach_calib_step = [] 
du_lieu_ma_tran = []      
danh_sach_toa_do_tam = [] 
ma_tran_phoi_canh = None # Ma trận cốt lõi

# BẠN ĐANG Ở VÙNG AN TOÀN NÊN CHỈ CẦN QUÉT MỘT LƯỚI NHỎ
# Ví dụ: Từ 0 đến 41 step, mỗi lần nhích 8 step -> Tạo ra lưới 5x5 = 25 điểm
for sx in range(0, 41, 8):
    for sy in range(0, 36, 7):
        danh_sach_calib_step.append((sx, sy))

diem_step_hien_tai = None 
thoi_gian_doi = 0
toa_do_laser_hien_tai = None
toa_do_laser_cuoi_cung = None 
toa_do_muc_tieu = None
diem_hien_thi_muc_tieu = None 

# Các biến lưu tọa độ logic ảo hiện tại của motor
step_hien_tai_X = 0
step_hien_tai_Y = 0
last_dir_X = 1
last_dir_Y = 1

# --- HÀM XỬ LÝ CLICK CHUỘT ---
def xu_ly_chuot(event, x, y, flags, param):
    global toa_do_muc_tieu, diem_hien_thi_muc_tieu
    if event == cv2.EVENT_LBUTTONDOWN and (trang_thai == "READY" or trang_thai == "MOVING_TO_TARGET"):
        toa_do_muc_tieu = (x, y)
        diem_hien_thi_muc_tieu = (x, y)
        print(f">> Nhấp chuột tại: {x}, {y}. Đang tính toán điều hướng...")

cv2.namedWindow("He Thong Dieu Huong Laser")
cv2.setMouseCallback("He Thong Dieu Huong Laser", xu_ly_chuot)

# --- VÒNG LẶP CHÍNH ---
while True:
    kiem_tra, khung_hinh = may_anh.read()
    if not kiem_tra: break
    
    toa_do_laser_hien_tai = tim_toa_do_laser(khung_hinh)
    if toa_do_laser_hien_tai:
        toa_do_laser_cuoi_cung = toa_do_laser_hien_tai
    
    tin_hieu = ""
    if bo_dieu_khien.in_waiting > 0:
        tin_hieu = bo_dieu_khien.readline().decode('utf-8').strip()

    # ================= MÁY TRẠNG THÁI (STATE MACHINE) =================
    
    if trang_thai == "START_GRID_CALIB":
        if len(danh_sach_calib_step) > 0:
            diem_step_hien_tai = danh_sach_calib_step.pop(0)
            lenh = f"{diem_step_hien_tai[0]},{diem_step_hien_tai[1]}\n"
            bo_dieu_khien.write(lenh.encode())
            
            trang_thai = "WAIT_GRID_CALIB"
            print(f"Đang di chuyển để lấy mẫu tại Step: {diem_step_hien_tai} ...")
        else:
            trang_thai = "CALCULATE_HOMOGRAPHY"
            
    elif trang_thai == "WAIT_GRID_CALIB":
        if tin_hieu == "DONE":
            thoi_gian_doi = time.time()
            trang_thai = "STABILIZING"
            danh_sach_toa_do_tam = [] 
            
    elif trang_thai == "STABILIZING":
        # Chờ 0.5 giây để bệ cơ khí bớt rung
        if time.time() - thoi_gian_doi > 0.5:
            if toa_do_laser_hien_tai:
                danh_sach_toa_do_tam.append(toa_do_laser_hien_tai)
            
            if len(danh_sach_toa_do_tam) >= 3: # Lấy nhanh 3 frame
                trang_thai = "READ_GRID_CALIB"

    elif trang_thai == "READ_GRID_CALIB":
        px_x = sum(p[0] for p in danh_sach_toa_do_tam) / len(danh_sach_toa_do_tam)
        px_y = sum(p[1] for p in danh_sach_toa_do_tam) / len(danh_sach_toa_do_tam)
        
        step_x, step_y = diem_step_hien_tai
        du_lieu_ma_tran.append([px_x, px_y, step_x, step_y])
        
        trang_thai = "START_GRID_CALIB"

    # PHẦN QUAN TRỌNG: Dùng RANSAC để tính mặt phẳng nghiêng từ lưới điểm an toàn
    elif trang_thai == "CALCULATE_HOMOGRAPHY":
        print("\n>> Đang phân tích mặt phẳng nghiêng bằng RANSAC...")
        
        # Tách lấy các mảng (Pixel làm Source, Step làm Destination)
        pts_pixel = np.float32([[d[0], d[1]] for d in du_lieu_ma_tran])
        pts_step = np.float32([[d[2], d[3]] for d in du_lieu_ma_tran])
        
        # Hàm phép màu: Tính Homography từ nhiều điểm, tự động vứt bỏ các điểm bị nhiễu cơ khí
        ma_tran_phoi_canh, mask = cv2.findHomography(pts_pixel, pts_step, cv2.RANSAC, 3.0)
        
        if ma_tran_phoi_canh is not None:
            # Chốt tọa độ động cơ về mốc cuối cùng nó vừa chạy xong
            step_hien_tai_X = int(pts_step[-1][0])
            step_hien_tai_Y = int(pts_step[-1][1])
            
            print(f">> HOÀN THÀNH! Lưới {len(du_lieu_ma_tran)} điểm đã hội tụ thành công.")
            print(">> SẴN SÀNG! Bạn có thể click ra vô tận.\n")
            trang_thai = "READY"
        else:
            print(">> LỖI: Dữ liệu quá nhiễu, không thể tính toán mặt phẳng. Vui lòng chạy lại.")
            break

    # ĐIỀU HƯỚNG MỤC TIÊU (NGOẠI SUY VÔ TẬN)
    elif trang_thai == "READY" or trang_thai == "MOVING_TO_TARGET":
        if toa_do_muc_tieu:
            if ma_tran_phoi_canh is not None:
                # Chuyển đổi tọa độ click
                target_px = np.array([[[toa_do_muc_tieu[0], toa_do_muc_tieu[1]]]], dtype=np.float32)
                
                # Biến hình qua ma trận nghiêng (Ngoại suy thoải mái)
                target_step = cv2.perspectiveTransform(target_px, ma_tran_phoi_canh)
                
                sent_X = int(target_step[0][0][0])
                sent_Y = int(target_step[0][0][1])
                
                print(f">> Click tại {toa_do_muc_tieu} -> Homography tính ra Step: ({sent_X}, {sent_Y})")
                
                # Gửi lệnh
                lenh = f"{sent_X},{sent_Y}\n"
                bo_dieu_khien.write(lenh.encode())
                
                trang_thai = "MOVING_TO_TARGET"
                toa_do_muc_tieu = None 

        if trang_thai == "MOVING_TO_TARGET" and tin_hieu == "DONE":
            print(">> Đã tới đích! Chờ lệnh click tiếp theo...")
            trang_thai = "READY"
            if diem_hien_thi_muc_tieu:
                toa_do_laser_cuoi_cung = diem_hien_thi_muc_tieu

    # ================= HIỂN THỊ ĐỒ HOẠ =================
    if toa_do_laser_hien_tai:
        cv2.circle(khung_hinh, toa_do_laser_hien_tai, 15, (0, 255, 0), 2)
        cv2.circle(khung_hinh, toa_do_laser_hien_tai, 2, (0, 0, 255), -1)
        
    if diem_hien_thi_muc_tieu:
        tx, ty = diem_hien_thi_muc_tieu
        cv2.circle(khung_hinh, (tx, ty), 10, (0, 0, 255), 2)
        cv2.line(khung_hinh, (tx - 15, ty), (tx + 15, ty), (0, 0, 255), 2)
        cv2.line(khung_hinh, (tx, ty - 15), (tx, ty + 15), (0, 0, 255), 2)
        
    if "CALIB" in trang_thai or trang_thai == "STABILIZING" or "HOMOGRAPHY" in trang_thai:
        cv2.putText(khung_hinh, f"Dang thu thap ma tran... {trang_thai}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
        cv2.putText(khung_hinh, f"Da luu: {len(du_lieu_ma_tran)} diem", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
    elif trang_thai == "READY":
        cv2.putText(khung_hinh, "SAN SANG! Click chuot de di chuyen.", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    elif trang_thai == "MOVING_TO_TARGET":
        cv2.putText(khung_hinh, "Dang di chuyen den muc tieu...", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)

    cv2.imshow("He Thong Dieu Huong Laser", khung_hinh)
    
    # --- PHÍM TẮT ---
    phim = cv2.waitKey(1) & 0xFF
    if phim == ord('q'):
        break
    elif phim == ord('r'):
        print(">> Lệnh Reset! Về gốc...")
        bo_dieu_khien.write(b"r\n")

may_anh.release()
bo_dieu_khien.close()
cv2.destroyAllWindows()
