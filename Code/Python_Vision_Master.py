import cv2
import numpy as np
import serial
import time
import math

# --- CẤU HÌNH HỆ THỐNG ---
CONG_COM = 'COM6' 

# --- HÀM TÌM TỌA ĐỘ LASER ---
def tim_toa_do_laser(anh_dau_vao):
    # 1. Chuyển sang ảnh xám
    anh_xam = cv2.cvtColor(anh_dau_vao, cv2.COLOR_BGR2GRAY)
    
    # 2. Bắt các điểm chói sáng (ngưỡng 245)
    _, mat_na_sang_nhat = cv2.threshold(anh_xam, 245, 255, cv2.THRESH_BINARY)
    
    # 3. Tìm danh sách các đốm sáng
    danh_sach_vien, _ = cv2.findContours(mat_na_sang_nhat, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if len(danh_sach_vien) > 0:
        # Sắp xếp các viền từ lớn đến bé
        danh_sach_vien_sap_xep = sorted(danh_sach_vien, key=cv2.contourArea, reverse=True)
        
        for vien_laser in danh_sach_vien_sap_xep:
            dien_tich = cv2.contourArea(vien_laser)
            
            # NỚI LỎNG: Diện tích từ 5 đến 1000 pixel đề phòng lóa hoặc laser nhỏ đi
            if 5 < dien_tich < 1000: 
                chu_vi_vien = cv2.arcLength(vien_laser, True)
                
                if chu_vi_vien > 0:
                    do_tron = 4 * np.pi * dien_tich / (chu_vi_vien * chu_vi_vien)
                    
                    # NỚI LỎNG: Hạ độ tròn xuống 0.4 để chấp nhận các đốm bị méo thành elip khi chiếu xiên
                    if do_tron > 0.4:
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

# --- HIỂN THỊ KÍCH THƯỚC PIXEL CỦA CAMERA ---
chieu_rong = int(may_anh.get(cv2.CAP_PROP_FRAME_WIDTH))
chieu_cao = int(may_anh.get(cv2.CAP_PROP_FRAME_HEIGHT))
print(f"Kích thước Camera: {chieu_rong} x {chieu_cao} pixels")
print("Đang chờ camera ổn định...")

for _ in range(30): may_anh.read()

# --- BIẾN TOÀN CỤC ---
trang_thai = "START_GRID_CALIB"

danh_sach_calib_step = [] 
du_lieu_ma_tran = []      
danh_sach_toa_do_tam = [] 
ma_tran_phoi_canh = None

# Biến lưu sai số
danh_sach_sai_so = []
sai_so_hien_tai = None
sai_so_x = None # THÊM: Lưu sai số trục X
sai_so_y = None # THÊM: Lưu sai số trục Y

# Cấu hình lưới Calib
for sx in range(0, 41, 8):
    for sy in range(0, 36, 7):
        danh_sach_calib_step.append((sx, sy))

diem_step_hien_tai = None 
thoi_gian_doi = 0
toa_do_laser_hien_tai = None
toa_do_laser_cuoi_cung = None 
toa_do_muc_tieu = None
diem_hien_thi_muc_tieu = None 

step_hien_tai_X = 0
step_hien_tai_Y = 0

# --- HÀM XỬ LÝ CLICK CHUỘT ---
def xu_ly_chuot(event, x, y, flags, param):
    global toa_do_muc_tieu, diem_hien_thi_muc_tieu
    if event == cv2.EVENT_LBUTTONDOWN and (trang_thai == "READY" or trang_thai == "MOVING_TO_TARGET" or trang_thai == "STABILIZING_TARGET"):
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

    # ================= MÁY TRẠNG THÁI =================
    
    # 1. QUÁ TRÌNH CALIB
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
        if time.time() - thoi_gian_doi > 0.5:
            if toa_do_laser_hien_tai:
                danh_sach_toa_do_tam.append(toa_do_laser_hien_tai)
            
            if len(danh_sach_toa_do_tam) >= 3: 
                trang_thai = "READ_GRID_CALIB"

    elif trang_thai == "READ_GRID_CALIB":
        px_x = sum(p[0] for p in danh_sach_toa_do_tam) / len(danh_sach_toa_do_tam)
        px_y = sum(p[1] for p in danh_sach_toa_do_tam) / len(danh_sach_toa_do_tam)
        
        step_x, step_y = diem_step_hien_tai
        du_lieu_ma_tran.append([px_x, px_y, step_x, step_y])
        
        trang_thai = "START_GRID_CALIB"

    # 2. TÍNH TOÁN MA TRẬN
    elif trang_thai == "CALCULATE_HOMOGRAPHY":
        print("\n>> Đang phân tích mặt phẳng nghiêng bằng RANSAC...")
        
        pts_pixel = np.float32([[d[0], d[1]] for d in du_lieu_ma_tran])
        pts_step = np.float32([[d[2], d[3]] for d in du_lieu_ma_tran])
        
        ma_tran_phoi_canh, mask = cv2.findHomography(pts_pixel, pts_step, cv2.RANSAC, 3.0)
        
        if ma_tran_phoi_canh is not None:
            step_hien_tai_X = int(pts_step[-1][0])
            step_hien_tai_Y = int(pts_step[-1][1])
            
            print(f">> HOÀN THÀNH! Lưới {len(du_lieu_ma_tran)} điểm đã hội tụ thành công.")
            print(">> SẴN SÀNG! Bạn có thể click ra vô tận.\n")
            trang_thai = "READY"
        else:
            print(">> LỖI: Dữ liệu quá nhiễu, không thể tính toán mặt phẳng. Vui lòng chạy lại.")
            break

    # 3. ĐIỀU HƯỚNG MỤC TIÊU VÀ TÍNH SAI SỐ
    elif trang_thai == "READY" or trang_thai == "MOVING_TO_TARGET" or trang_thai == "STABILIZING_TARGET":
        if toa_do_muc_tieu:
            if ma_tran_phoi_canh is not None:
                target_px = np.array([[[toa_do_muc_tieu[0], toa_do_muc_tieu[1]]]], dtype=np.float32)
                target_step = cv2.perspectiveTransform(target_px, ma_tran_phoi_canh)
                
                sent_X = int(target_step[0][0][0])
                sent_Y = int(target_step[0][0][1])
                
                print(f">> Click tại {toa_do_muc_tieu} -> Homography tính ra Step: ({sent_X}, {sent_Y})")
                
                lenh = f"{sent_X},{sent_Y}\n"
                bo_dieu_khien.write(lenh.encode())
                
                trang_thai = "MOVING_TO_TARGET"
                toa_do_muc_tieu = None 

        if trang_thai == "MOVING_TO_TARGET" and tin_hieu == "DONE":
            # Đổi trạng thái sang chờ ổn định cơ khí
            trang_thai = "STABILIZING_TARGET"
            thoi_gian_doi = time.time()

        elif trang_thai == "STABILIZING_TARGET":
            thoi_gian_da_qua = time.time() - thoi_gian_doi
            
            # Chờ 0.5s cho hệ cơ khí bớt rung rồi mới bắt đầu tìm
            if thoi_gian_da_qua > 0.5:
                
                # Nếu thấy laser -> Chốt luôn tọa độ
                if toa_do_laser_hien_tai:
                    dx = toa_do_laser_hien_tai[0] - diem_hien_thi_muc_tieu[0]
                    dy = toa_do_laser_hien_tai[1] - diem_hien_thi_muc_tieu[1]
                    
                    sai_so_pixel = math.sqrt(dx**2 + dy**2)
                    sai_so_hien_tai = round(sai_so_pixel, 2)
                    sai_so_x = dx
                    sai_so_y = dy
                    danh_sach_sai_so.append(sai_so_pixel)
                    
                    # THÊM: In kết quả chi tiết X và Y
                    print(f">> Đã tới đích! Sai số: {sai_so_hien_tai} px (X = {dx}; Y = {dy})")
                    
                    trang_thai = "READY"
                    if diem_hien_thi_muc_tieu:
                        toa_do_laser_cuoi_cung = diem_hien_thi_muc_tieu
                
                # CƠ CHẾ DU DI: Nếu trôi qua 1.5 giây mà vẫn không thấy laser
                elif thoi_gian_da_qua > 1.5:
                    sai_so_hien_tai = "-"
                    sai_so_x = "-"
                    sai_so_y = "-"
                    print(">> Đã tới đích! Sai số: - (Quá 1.5s không nhận diện được laser)")
                    
                    trang_thai = "READY"

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
        if sai_so_hien_tai is not None:
            # THÊM: Cập nhật hiển thị text trên video
            if sai_so_hien_tai == "-":
                txt_sai_so = "Sai so test truoc: -"
            else:
                txt_sai_so = f"Sai so test truoc: {sai_so_hien_tai} px (X={sai_so_x}, Y={sai_so_y})"
            cv2.putText(khung_hinh, txt_sai_so, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
    elif trang_thai == "MOVING_TO_TARGET" or trang_thai == "STABILIZING_TARGET":
        cv2.putText(khung_hinh, "Dang di chuyen / on dinh muc tieu...", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)

    cv2.imshow("He Thong Dieu Huong Laser", khung_hinh)
    
    # --- PHÍM TẮT ---
    phim = cv2.waitKey(1) & 0xFF
    if phim == ord('q'):
        break
    elif phim == ord('r'):
        print(">> Lệnh Reset! Về gốc...")
        bo_dieu_khien.write(b"r\n")
    elif phim == ord('p'):
        if danh_sach_sai_so:
            sai_so_max = round(max(danh_sach_sai_so), 2)
            sai_so_min = round(min(danh_sach_sai_so), 2)
            print("\n" + "="*30)
            print("TỔNG KẾT BÀI TEST")
            print(f"- Số lần test hợp lệ: {len(danh_sach_sai_so)}")
            print(f"- Sai số LỚN NHẤT: {sai_so_max} px")
            print(f"- Sai số NHỎ NHẤT: {sai_so_min} px")
            print("="*30 + "\n")
        else:
            print("\n>> Chưa có dữ liệu test nào thành công để tính sai số max/min.")
        break

may_anh.release()
bo_dieu_khien.close()
cv2.destroyAllWindows()
