import cv2
import numpy as np
from typing import Optional, Tuple
from calibration import CalibrationResult

class VisionTracker:
    """
    计算机视觉引擎：基于HSV色彩空间的非接触式物理探针坐标解析。
    支持标定板校准，动态更新像素-毫米转换比例。
    """
    def __init__(self):
        # 默认假设探针笔尖贴了醒目的绿色标记，使用HSV颜色空间进行颜色阈值范围设定
        self.marker_lower_hsv = np.array([35, 100, 100])
        self.marker_upper_hsv = np.array([85, 255, 255])

        # 像素到物理坐标(毫米)的转换比例（测量坐标系，受标定影响）
        self.pixels_per_mm = 5.0

        # 预览坐标系（显示用，与测量解耦，避免标定后刻度突变/中心漂移）
        self.display_pixels_per_mm: Optional[float] = None

        # 标定状态
        self.is_calibrated = False
        self.calibration_result: Optional[CalibrationResult] = None

        # 标定板中心偏移补偿（像素，仅用于物理坐标换算，不直接驱动显示中心）
        self.center_offset_x = 0.0
        self.center_offset_y = 0.0

    def apply_calibration(self, calibration_result: CalibrationResult):
        """
        应用标定结果，更新像素-毫米转换比例和中心偏移
        
        Args:
            calibration_result: 标定结果对象
        """
        if calibration_result.success:
            self.pixels_per_mm = calibration_result.pixels_per_mm
            self.center_offset_x = calibration_result.center_offset[0]
            self.center_offset_y = calibration_result.center_offset[1]
            self.calibration_result = calibration_result
            self.is_calibrated = True
            print(f"[VisionTracker] 标定已应用: pixels_per_mm={self.pixels_per_mm:.2f}, "
                  f"center_offset=({self.center_offset_x:.1f}, {self.center_offset_y:.1f})")
        else:
            print(f"[VisionTracker] 标定失败: {calibration_result.error_message}")
    
    def reset_calibration(self):
        """重置标定状态"""
        self.is_calibrated = False
        self.calibration_result = None
        self.center_offset_x = 0.0
        self.center_offset_y = 0.0
        self.pixels_per_mm = 5.0  # 恢复默认值
        print("[VisionTracker] 标定已重置")
    
    def _get_display_params(self, width: int, height: int) -> Tuple[float, float, float]:
        """
        获取显示网格参数（显示坐标系）

        说明：
        - 显示网格始终以图像中心为原点，避免标定中心偏移导致“中心刻度跑偏”
        - 显示刻度按当前窗口尺寸自适应到约190mm视野，保持与初始状态一致
        """
        target_ppm = max(min(width, height) / 190.0, 0.1)
        self.display_pixels_per_mm = target_ppm
        cx = width / 2.0
        cy = height / 2.0
        return self.display_pixels_per_mm, cx, cy

    def physical_to_display_pixel(self, physical_x: float, physical_y: float, frame_width: int, frame_height: int) -> Tuple[int, int]:
        """
        将物理坐标(mm)映射到显示像素坐标（用于历史点绘制）
        """
        display_ppm, cx, cy = self._get_display_params(frame_width, frame_height)
        px = int(cx + physical_x * display_ppm)
        py = int(cy - physical_y * display_ppm)
        return px, py

    def get_pen_tip_coordinate(self, frame):
        """
        核心检测算法
        :param frame: 摄像头捕获的BGR图像
        :return: 物理坐标 (x, y) 毫米，以及供界面显示的带有标注框的图像
        """
        # 预先绘制坐标级辅助线，方便实时掌握取点位置而不超限
        debug_frame = frame.copy()
        height, width = debug_frame.shape[:2]
        
        # 测量坐标系中心：应用标定偏移（仅用于物理坐标换算）
        self.cx_float = width / 2.0 + self.center_offset_x
        self.cy_float = height / 2.0 + self.center_offset_y

        # 显示坐标系：固定以画面中心绘制，刻度按窗口大小自适应
        display_ppm, display_cx_float, display_cy_float = self._get_display_params(width, height)
        cx = int(display_cx_float)
        cy = int(display_cy_float)

        # 依据显示坐标系计算可见网格范围
        ppm = display_ppm
        max_mm_x = int((width / 2) / ppm) + 1
        max_mm_y = int((height / 2) / ppm) + 1
        max_mm = max(max_mm_x, max_mm_y)
        
        # 绘制网格，包含1mm小格和10mm大格
        for i in range(1, max_mm + 1):
            is_major = (i % 10 == 0)
            is_mid = (i % 5 == 0) and not is_major
            
            # 使用不同亮度和粗细区分主次网格
            color = (150, 150, 150) if is_major else ((90, 90, 90) if is_mid else (50, 50, 50))
            
            px_pos = int(display_cx_float + i * ppm)
            px_neg = int(display_cx_float - i * ppm)
            if px_pos < width: cv2.line(debug_frame, (px_pos, 0), (px_pos, height), color, 1)
            if px_neg > 0: cv2.line(debug_frame, (px_neg, 0), (px_neg, height), color, 1)

            py_pos = int(display_cy_float + i * ppm)
            py_neg = int(display_cy_float - i * ppm)
            if py_pos < height: cv2.line(debug_frame, (0, py_pos), (width, py_pos), color, 1)
            if py_neg > 0: cv2.line(debug_frame, (0, py_neg), (width, py_neg), color, 1)
            
            # 仅10mm级显示大格文字
            if is_major:
                if px_pos < width: cv2.putText(debug_frame, f"{i}", (px_pos - 10, cy + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
                if px_neg > 0: cv2.putText(debug_frame, f"{-i}", (px_neg - 15, cy + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
                if py_pos < height: cv2.putText(debug_frame, f"{-i}", (cx + 5, py_pos + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
                if py_neg > 0: cv2.putText(debug_frame, f"{i}", (cx + 5, py_neg + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

        # 绘制中心十字系统主轴
        cv2.line(debug_frame, (cx, 0), (cx, height), (100, 255, 100), 2)
        cv2.line(debug_frame, (0, cy), (width, cy), (100, 255, 100), 2)
                
        # 1. 颜色空间转换
        hsv_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # 2. 颜色阈值二值化提取 - 调整阈值以减少手部干扰
        mask = cv2.inRange(hsv_frame, self.marker_lower_hsv, self.marker_upper_hsv)
        
        # 3. 形态学开运算去噪
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        # 4. 形态学闭运算填充小孔
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        # 5. 寻找所有轮廓边框
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return None, debug_frame

        # 6. 过滤轮廓，选择合适的标定板标记
        valid_contours = []
        for contour in contours:
            # 计算轮廓面积
            area = cv2.contourArea(contour)
            
            # 过滤太小或太大的轮廓
            if area < 100 or area > 5000:
                continue
            
            # 计算轮廓的边界框
            x, y, w, h = cv2.boundingRect(contour)
            
            # 计算宽高比，过滤过于狭长的轮廓
            aspect_ratio = float(w) / h if h != 0 else 0
            if aspect_ratio < 0.5 or aspect_ratio > 2.0:
                continue
            
            # 计算轮廓的圆度，过滤不规则形状
            perimeter = cv2.arcLength(contour, True)
            if perimeter > 0:
                circularity = 4 * np.pi * area / (perimeter * perimeter)
                # 圆度在0.5到1.0之间的轮廓更可能是标定板标记
                if 0.3 < circularity < 1.2:
                    valid_contours.append(contour)

        if not valid_contours:
            return None, debug_frame

        # 7. 选择最适合的轮廓（面积适中且接近中心的）
        # 计算每个轮廓到中心的距离
        contour_info = []
        for contour in valid_contours:
            M = cv2.moments(contour)
            if M["m00"] != 0:
                cx_contour = M["m10"] / M["m00"]
                cy_contour = M["m01"] / M["m00"]
                distance_to_center = np.sqrt((cx_contour - self.cx_float) ** 2 + (cy_contour - self.cy_float) ** 2)
                area = cv2.contourArea(contour)
                # 综合考虑面积和距离，选择最合适的轮廓
                score = 1.0 / (1.0 + distance_to_center) * area
                contour_info.append((score, contour, cx_contour, cy_contour))

        if not contour_info:
            return None, debug_frame

        # 选择得分最高的轮廓
        contour_info.sort(key=lambda x: x[0], reverse=True)
        best_score, best_contour, probe_x, probe_y = contour_info[0]
        
        c_x, c_y = int(probe_x), int(probe_y)
        
        # 8. 坐标系转换：图像像素 -> 物理毫米
        # y轴物理上正方向为上，图像上正方向为下，需要翻转
        # cx_float, cy_float 是标定板中心（考虑了偏移）
        physical_x = (probe_x - self.cx_float) / self.pixels_per_mm
        physical_y = (self.cy_float - probe_y) / self.pixels_per_mm
        
        # 9. 绘制验证图像信息
        cv2.drawContours(debug_frame, [best_contour], -1, (0, 255, 0), 2)
        cv2.circle(debug_frame, (c_x, c_y), 5, (0, 0, 255), -1)
        cv2.putText(debug_frame, f"({physical_x:.1f}mm, {physical_y:.1f}mm)", 
                    (c_x + 15, c_y - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
        
        return (physical_x, physical_y), debug_frame
