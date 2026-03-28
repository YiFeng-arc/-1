"""
相机标定模块 - 红色十字交叉标定板检测与透视变换
标定板规格：80x80mm，红色毫米尺线，多十字交叉
"""
import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from dataclasses import dataclass
from typing import Optional, Tuple, List


@dataclass
class CalibrationResult:
    """标定结果数据类"""
    success: bool
    pixels_per_mm: float
    matrix: np.ndarray  # 透视变换矩阵
    corners: np.ndarray  # 检测到的四个角点 (像素坐标)
    physical_size: float = 80.0  # 标定板物理尺寸 (mm)
    error_message: str = ""
    center_offset: Tuple[float, float] = (0.0, 0.0)  # 标定板中心相对于图像中心的偏移 (像素)


class RedCrossCalibrator:
    """
    红色十字交叉标定板检测器
    
    检测原理：
    1. 使用HSV颜色空间提取红色区域
    2. 通过形态学操作和轮廓分析找到十字交叉点
    3. 识别标定板的四个角点
    4. 计算透视变换矩阵和像素-毫米转换比例
    """
    
    def __init__(self, board_size_mm: float = 80.0):
        """
        初始化标定器
        
        Args:
            board_size_mm: 标定板物理尺寸（毫米），默认80x80mm
        """
        self.board_size_mm = board_size_mm
        
        # 红色HSV范围（根据实际标定板调整，适应不同光照）
        # 红色在HSV空间有两个范围：[0,10] 和 [170,180]
        self.red_lower1 = np.array([0, 80, 80])
        self.red_upper1 = np.array([15, 255, 255])
        self.red_lower2 = np.array([165, 80, 80])
        self.red_upper2 = np.array([180, 255, 255])
        
        # 十字交叉检测参数
        self.min_cross_area = 20  # 最小十字交叉面积（降低阈值以检测更小的交叉点）
        self.max_cross_area = 100000  # 最大十字交叉面积
        
        # 网格线检测参数
        self.min_line_length = 30  # 最小线段长度
        self.max_line_gap = 10  # 最大线段间隙

        # Windows 中文字体候选（用于OpenCV画面叠字，避免中文显示为????）
        self._font_candidates = [
            "C:/Windows/Fonts/msyh.ttc",      # 微软雅黑
            "C:/Windows/Fonts/msyhbd.ttc",    # 微软雅黑粗体
            "C:/Windows/Fonts/simhei.ttf",    # 黑体
        ]
        self._cached_font = None
        
    def auto_adjust_hsv_threshold(self, frame: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        自动调整HSV阈值以适应不同光照条件
        
        Args:
            frame: 输入图像
            
        Returns:
            调整后的HSV阈值范围
        """
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # 计算图像的平均亮度和饱和度
        mean_brightness = np.mean(hsv[:, :, 2])
        mean_saturation = np.mean(hsv[:, :, 1])
        
        # 根据亮度调整V通道阈值
        if mean_brightness < 100:
            # 低光照环境
            v_min = 50
            v_max = 200
        elif mean_brightness > 200:
            # 高光照环境
            v_min = 100
            v_max = 255
        else:
            # 正常光照
            v_min = 80
            v_max = 255
        
        # 根据饱和度调整S通道阈值
        if mean_saturation < 50:
            s_min = 30
        else:
            s_min = 80
        
        # 更新红色HSV范围
        self.red_lower1 = np.array([0, s_min, v_min])
        self.red_upper1 = np.array([15, 255, v_max])
        self.red_lower2 = np.array([165, s_min, v_min])
        self.red_upper2 = np.array([180, 255, v_max])
        
        return self.red_lower1, self.red_upper1, self.red_lower2, self.red_upper2
    
    def _extract_red_regions(self, frame: np.ndarray) -> np.ndarray:
        """
        提取图像中的红色区域
        
        Args:
            frame: BGR图像
            
        Returns:
            二值化掩码图像
        """
        # 增强图像对比度，提高红色区域的识别率
        enhanced = cv2.convertScaleAbs(frame, alpha=1.2, beta=0)
        
        hsv = cv2.cvtColor(enhanced, cv2.COLOR_BGR2HSV)
        
        # 提取两个红色范围并合并
        mask1 = cv2.inRange(hsv, self.red_lower1, self.red_upper1)
        mask2 = cv2.inRange(hsv, self.red_lower2, self.red_upper2)
        mask = cv2.bitwise_or(mask1, mask2)
        
        # 形态学操作去噪
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        # 填充小的孔洞
        kernel_fill = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_fill)
        
        return mask
    
    def _detect_cross_centers(self, mask: np.ndarray, frame_shape: Tuple[int, int]) -> List[Tuple[int, int]]:
        """
        检测十字交叉中心点（增强版，结合多种检测方法）
        
        Args:
            mask: 二值化掩码
            frame_shape: 原始图像尺寸 (height, width)
            
        Returns:
            十字交叉中心点列表 [(x, y), ...]
        """
        height, width = frame_shape
        cross_centers = []
        
        # 方法1：基于轮廓检测（适用于明显的十字交叉）
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if self.min_cross_area < area < self.max_cross_area:
                # 计算轮廓的质心
                M = cv2.moments(contour)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    cross_centers.append((cx, cy))
        
        # 方法2：基于角点检测（Harris角点）作为补充
        if len(cross_centers) < 10:
            gray = mask.astype(np.uint8)
            corners = cv2.goodFeaturesToTrack(
                gray,
                maxCorners=200,
                qualityLevel=0.01,
                minDistance=8,
                blockSize=3
            )
            
            if corners is not None:
                for corner in corners:
                    x, y = corner.ravel()
                    if 0 <= int(x) < width and 0 <= int(y) < height:
                        if mask[int(y), int(x)] > 0:
                            cross_centers.append((int(x), int(y)))
        
        # 方法3：基于网格线交点检测（适用于规则网格）
        if len(cross_centers) < 10:
            # 使用霍夫变换检测直线
            edges = cv2.Canny(mask, 50, 150)
            # 降低阈值以检测更多线条
            lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=30, 
                                   minLineLength=20, 
                                   maxLineGap=15)
            
            if lines is not None and len(lines) > 4:
                # 分离水平和垂直线
                h_lines = []
                v_lines = []
                
                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    if abs(x2 - x1) > abs(y2 - y1):  # 水平线
                        h_lines.append(line[0])
                    else:  # 垂直线
                        v_lines.append(line[0])
                
                # 计算线交点
                for h_line in h_lines:
                    for v_line in v_lines:
                        x1, y1, x2, y2 = h_line
                        x3, y3, x4, y4 = v_line
                        
                        # 计算两条直线的交点
                        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
                        if denom != 0:
                            px = ((x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)) / denom
                            py = ((x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4)) / denom
                            
                            if 0 <= px < width and 0 <= py < height:
                                if mask[int(py), int(px)] > 0:
                                    cross_centers.append((int(px), int(py)))
        
        # 方法4：基于模板匹配检测十字交叉（增强识别率）
        if len(cross_centers) < 10:
            # 创建十字模板
            cross_template = np.zeros((11, 11), dtype=np.uint8)
            cv2.line(cross_template, (5, 0), (5, 10), 255, 2)
            cv2.line(cross_template, (0, 5), (10, 5), 255, 2)
            
            # 进行模板匹配
            result = cv2.matchTemplate(mask, cross_template, cv2.TM_CCOEFF_NORMED)
            threshold = 0.6
            loc = np.where(result >= threshold)
            
            for pt in zip(*loc[::-1]):
                cx = pt[0] + 5  # 模板中心
                cy = pt[1] + 5
                if 0 <= cx < width and 0 <= cy < height:
                    cross_centers.append((cx, cy))
        
        # 去重（使用距离阈值）
        unique_centers = []
        min_dist = 8  # 最小间距（像素）
        
        for center in cross_centers:
            is_duplicate = False
            for existing in unique_centers:
                dist = np.sqrt((center[0] - existing[0])**2 + (center[1] - existing[1])**2)
                if dist < min_dist:
                    is_duplicate = True
                    break
            if not is_duplicate:
                unique_centers.append(center)
        
        return unique_centers
    
    def _find_board_corners(self, cross_centers: List[Tuple[int, int]], 
                           frame_shape: Tuple[int, int]) -> Optional[np.ndarray]:
        """
        从十字交叉点中找出标定板的四个角点（增强版）
        
        策略：
        1. 使用凸包算法找到外围点
        2. 对凸包进行多边形逼近，找到四个角点
        3. 验证角点形成的四边形是否合理
        
        Args:
            cross_centers: 十字交叉中心点列表
            frame_shape: 原始图像尺寸
            
        Returns:
            四个角点坐标 [[x1,y1], [x2,y2], [x3,y3], [x4,y4]] (左上, 右上, 右下, 左下)
        """
        if len(cross_centers) < 4:
            return None
        
        points = np.array(cross_centers, dtype=np.float32)
        
        # 计算凸包
        hull = cv2.convexHull(points)
        hull = hull.reshape(-1, 2)
        
        # 如果凸包点数正好是4，直接使用
        if len(hull) == 4:
            corners = hull
        else:
            # 使用多边形逼近简化到4个点
            epsilon = 0.02 * cv2.arcLength(hull, True)
            approx = cv2.approxPolyDP(hull, epsilon, True)
            
            if len(approx) == 4:
                corners = approx.reshape(4, 2)
            elif len(approx) > 4:
                # 如果点多于4个，选择最外层的4个角点
                corners = self._select_four_corners(approx.reshape(-1, 2))
            else:
                # 点数不足，使用凸包的极值点
                corners = self._get_extreme_corners(hull)
        
        # 验证角点是否合理（不能太靠近边缘）
        height, width = frame_shape
        margin = 20  # 边缘容差
        valid = True
        for corner in corners:
            if corner[0] < margin or corner[0] > width - margin or \
               corner[1] < margin or corner[1] > height - margin:
                valid = False
                break
        
        if not valid:
            # 如果角点太靠近边缘，尝试使用极值点
            corners = self._get_extreme_corners(points)
        
        # 按顺序排列角点：左上、右上、右下、左下
        corners = self._order_corners(corners)
        
        return corners
    
    def _select_four_corners(self, points: np.ndarray) -> np.ndarray:
        """从多个点中选择四个角点"""
        # 计算中心点
        center = np.mean(points, axis=0)
        
        # 计算每个点到中心的距离和角度
        angles = []
        for point in points:
            vec = point - center
            angle = np.arctan2(vec[1], vec[0])
            angles.append((angle, point))
        
        # 按角度排序，选择四个象限的代表点
        angles.sort(key=lambda x: x[0])
        
        # 将360度分成4个区间，每个区间选最远的点
        quadrants = [[], [], [], []]
        for angle, point in angles:
            deg = np.degrees(angle)
            if deg < 0:
                deg += 360
            idx = int(deg // 90) % 4
            dist = np.linalg.norm(point - center)
            quadrants[idx].append((dist, point))
        
        corners = []
        for quad in quadrants:
            if quad:
                corners.append(max(quad, key=lambda x: x[0])[1])
        
        if len(corners) < 4:
            # 备选方案：直接用凸包的极值点
            return self._get_extreme_corners(points)
        
        return np.array(corners, dtype=np.float32)
    
    def _get_extreme_corners(self, points: np.ndarray) -> np.ndarray:
        """获取点集的四个极值角点"""
        # 按x+y排序（左上角最小）
        sorted_tl = sorted(points, key=lambda p: p[0] + p[1])
        top_left = sorted_tl[0]
        
        # 按x-y排序（右上角最小）
        sorted_tr = sorted(points, key=lambda p: p[0] - p[1])
        top_right = sorted_tr[-1]
        
        # 按x+y排序（右下角最大）
        sorted_br = sorted(points, key=lambda p: p[0] + p[1])
        bottom_right = sorted_br[-1]
        
        # 按x-y排序（左下角最大）
        sorted_bl = sorted(points, key=lambda p: p[0] - p[1])
        bottom_left = sorted_bl[0]
        
        return np.array([top_left, top_right, bottom_right, bottom_left], dtype=np.float32)
    
    def _order_corners(self, corners: np.ndarray) -> np.ndarray:
        """
        将四个角点按顺序排列：左上、右上、右下、左下
        
        Args:
            corners: 4x2数组，四个角点
            
        Returns:
            排序后的4x2数组
        """
        # 计算中心点
        center = np.mean(corners, axis=0)
        
        # 根据相对于中心的位置分类
        ordered = []
        for corner in corners:
            diff = corner - center
            if diff[0] < 0 and diff[1] < 0:
                ordered.append((0, corner))  # 左上
            elif diff[0] >= 0 and diff[1] < 0:
                ordered.append((1, corner))  # 右上
            elif diff[0] >= 0 and diff[1] >= 0:
                ordered.append((2, corner))  # 右下
            else:
                ordered.append((3, corner))  # 左下
        
        ordered.sort(key=lambda x: x[0])
        return np.array([p for _, p in ordered], dtype=np.float32)
    
    def _calculate_pixels_per_mm(self, corners: np.ndarray) -> float:
        """
        计算像素到毫米的转换比例
        
        Args:
            corners: 四个角点坐标
            
        Returns:
            每毫米对应的像素数
        """
        # 计算四条边的像素长度
        top_edge = np.linalg.norm(corners[1] - corners[0])
        right_edge = np.linalg.norm(corners[2] - corners[1])
        bottom_edge = np.linalg.norm(corners[2] - corners[3])
        left_edge = np.linalg.norm(corners[3] - corners[0])
        
        # 取平均值
        avg_pixel_size = (top_edge + right_edge + bottom_edge + left_edge) / 4
        
        # 标定板物理尺寸是80mm
        pixels_per_mm = avg_pixel_size / self.board_size_mm
        
        return pixels_per_mm
    
    def calibrate(self, frame: np.ndarray) -> CalibrationResult:
        """
        执行标定流程
        
        Args:
            frame: 包含标定板的图像帧
            
        Returns:
            CalibrationResult 对象
        """
        height, width = frame.shape[:2]
        image_center = (width / 2.0, height / 2.0)
        
        # 自动调整HSV阈值
        self.auto_adjust_hsv_threshold(frame)
        
        # 1. 提取红色区域
        mask = self._extract_red_regions(frame)
        
        # 2. 检测十字交叉中心
        cross_centers = self._detect_cross_centers(mask, (height, width))
        
        if len(cross_centers) < 4:
            return CalibrationResult(
                success=False,
                pixels_per_mm=0.0,
                matrix=np.eye(3),
                corners=np.array([]),
                error_message=f"检测到的十字交叉点不足（当前：{len(cross_centers)}，需要：≥4）"
            )
        
        # 3. 找到标定板四个角点
        corners = self._find_board_corners(cross_centers, (height, width))
        
        if corners is None:
            return CalibrationResult(
                success=False,
                pixels_per_mm=0.0,
                matrix=np.eye(3),
                corners=np.array([]),
                error_message="无法识别标定板的四个角点"
            )
        
        # 4. 计算像素-毫米转换比例
        pixels_per_mm = self._calculate_pixels_per_mm(corners)
        
        # 5. 计算标定板中心相对于图像中心的偏移
        board_center = np.mean(corners, axis=0)
        center_offset = (board_center[0] - image_center[0], board_center[1] - image_center[1])
        
        # 6. 计算透视变换矩阵
        # 目标坐标：将标定板变换为正方形，中心在原点
        half_size = self.board_size_mm / 2 * pixels_per_mm
        dst_corners = np.array([
            [-half_size, -half_size],  # 左上
            [half_size, -half_size],   # 右上
            [half_size, half_size],    # 右下
            [-half_size, half_size]    # 左下
        ], dtype=np.float32)
        
        # 计算从图像坐标到标准坐标的变换矩阵
        matrix = cv2.getPerspectiveTransform(corners, dst_corners)
        
        return CalibrationResult(
            success=True,
            pixels_per_mm=pixels_per_mm,
            matrix=matrix,
            corners=corners,
            physical_size=self.board_size_mm,
            center_offset=center_offset
        )
    
    def _get_unicode_font(self, font_size: int = 24):
        """获取可用于中文绘制的字体对象"""
        if self._cached_font is not None:
            return self._cached_font

        for font_path in self._font_candidates:
            if os.path.exists(font_path):
                try:
                    self._cached_font = ImageFont.truetype(font_path, font_size)
                    return self._cached_font
                except Exception:
                    continue

        # 兜底字体（若系统字体读取失败则退化为默认，可能不支持中文）
        self._cached_font = ImageFont.load_default()
        return self._cached_font

    def _draw_unicode_text(self, frame: np.ndarray, text: str, org: Tuple[int, int],
                           color: Tuple[int, int, int], font_size: int = 24) -> np.ndarray:
        """在OpenCV帧上绘制Unicode文本（含中文）"""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb_frame)
        draw = ImageDraw.Draw(pil_img)

        # PIL使用RGB，OpenCV使用BGR
        rgb_color = (color[2], color[1], color[0])
        draw.text(org, text, font=self._get_unicode_font(font_size), fill=rgb_color)

        return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    def draw_calibration_result(self, frame: np.ndarray, result: CalibrationResult) -> np.ndarray:
        """
        在图像上绘制标定结果
        
        Args:
            frame: 原始图像
            result: 标定结果
            
        Returns:
            绘制后的图像
        """
        debug_frame = frame.copy()
        height, width = debug_frame.shape[:2]
        
        if not result.success:
            # 失败信息也走Unicode绘制，避免中文错误原因显示为????
            header = "标定失败 Calibration Failed"
            debug_frame = self._draw_unicode_text(debug_frame, header, (20, 16), (0, 0, 255), font_size=28)

            error_text = f"原因: {result.error_message}"
            max_chars_per_line = 42
            wrapped_lines = [
                error_text[i:i + max_chars_per_line]
                for i in range(0, len(error_text), max_chars_per_line)
            ]
            for idx, line in enumerate(wrapped_lines[:3]):
                debug_frame = self._draw_unicode_text(
                    debug_frame,
                    line,
                    (20, 52 + idx * 30),
                    (0, 0, 255),
                    font_size=24
                )
            return debug_frame
        
        # 绘制检测到的角点
        corners = result.corners.astype(int)
        colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]
        labels = ["TL", "TR", "BR", "BL"]
        
        for corner, color, label in zip(corners, colors, labels):
            cv2.circle(debug_frame, tuple(corner), 8, color, -1)
            cv2.putText(debug_frame, label, (corner[0] + 15, corner[1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        # 绘制标定板边框
        cv2.polylines(debug_frame, [corners], True, (0, 255, 255), 3)
        
        # 绘制标定板中心
        board_center = np.mean(corners, axis=0).astype(int)
        cv2.circle(debug_frame, tuple(board_center), 5, (255, 0, 255), -1)
        cv2.line(debug_frame, (board_center[0] - 20, board_center[1]),
                 (board_center[0] + 20, board_center[1]), (255, 0, 255), 1)
        cv2.line(debug_frame, (board_center[0], board_center[1] - 20),
                 (board_center[0], board_center[1] + 20), (255, 0, 255), 1)
        
        # 显示标定信息（中文通过PIL绘制，避免????）
        info_lines = [
            "标定成功 Calibration SUCCESS",
            f"标定板尺寸: {result.physical_size:.1f}mm x {result.physical_size:.1f}mm",
            f"像素比例: {result.pixels_per_mm:.2f} px/mm",
            f"中心偏移: ({result.center_offset[0]:.1f}, {result.center_offset[1]:.1f}) px"
        ]

        for i, line in enumerate(info_lines):
            debug_frame = self._draw_unicode_text(
                debug_frame,
                line,
                (20, 15 + i * 32),
                (0, 255, 0),
                font_size=24
            )
        
        # 绘制图像中心十字线
        cv2.line(debug_frame, (width // 2, 0), (width // 2, height), (100, 255, 100), 1)
        cv2.line(debug_frame, (0, height // 2), (width, height // 2), (100, 255, 100), 1)
        
        return debug_frame


class CalibrationValidator:
    """标定结果验证器"""
    
    @staticmethod
    def validate_aspect_ratio(corners: np.ndarray, tolerance: float = 0.2) -> bool:
        """
        验证检测到的标定板长宽比是否接近1:1
        
        Args:
            corners: 四个角点
            tolerance: 容差比例
            
        Returns:
            是否通过验证
        """
        # 计算四条边长度
        top = np.linalg.norm(corners[1] - corners[0])
        bottom = np.linalg.norm(corners[2] - corners[3])
        left = np.linalg.norm(corners[3] - corners[0])
        right = np.linalg.norm(corners[2] - corners[1])
        
        width_avg = (top + bottom) / 2
        height_avg = (left + right) / 2
        
        ratio = max(width_avg, height_avg) / min(width_avg, height_avg)
        
        return ratio <= (1 + tolerance)
    
    @staticmethod
    def validate_area(corners: np.ndarray, min_area: float = 10000, 
                     max_area: float = 1000000) -> bool:
        """
        验证标定板面积是否在合理范围内
        
        Args:
            corners: 四个角点
            min_area: 最小面积（像素平方）
            max_area: 最大面积（像素平方）
            
        Returns:
            是否通过验证
        """
        area = cv2.contourArea(corners)
        return min_area <= area <= max_area


def create_synthetic_calibration_board(size_mm: float = 80.0, 
                                      pixels_per_mm: float = 10.0,
                                      output_path: str = "calibration_board.png") -> np.ndarray:
    """
    创建合成标定板图像用于测试（模拟实际标定板样式）
    
    Args:
        size_mm: 标定板物理尺寸（毫米）
        pixels_per_mm: 每毫米像素数
        output_path: 输出文件路径
        
    Returns:
        标定板图像
    """
    size_px = int(size_mm * pixels_per_mm)
    # 白色背景
    board = np.ones((size_px, size_px, 3), dtype=np.uint8) * 255
    
    # 绘制红色网格线（每1mm一条细线，每10mm一条粗线）
    for i in range(0, size_px + 1, max(1, int(pixels_per_mm))):
        is_main = (i % int(10 * pixels_per_mm) == 0)
        is_mid = (i % int(5 * pixels_per_mm) == 0) and not is_main
        thickness = 3 if is_main else (2 if is_mid else 1)
        color = (0, 0, 255)  # BGR格式的红色
        
        cv2.line(board, (i, 0), (i, size_px), color, thickness)
        cv2.line(board, (0, i), (size_px, i), color, thickness)
    
    # 绘制十字交叉标记（每10mm一个，更明显的十字）
    cross_size = int(4 * pixels_per_mm)
    for x in range(0, size_px + 1, int(10 * pixels_per_mm)):
        for y in range(0, size_px + 1, int(10 * pixels_per_mm)):
            # 绘制粗十字
            cv2.line(board, (x - cross_size, y), (x + cross_size, y), (0, 0, 255), 3)
            cv2.line(board, (x, y - cross_size), (x, y + cross_size), (0, 0, 255), 3)
    
    # 添加外边框（粗红线）
    border_thickness = int(5 * pixels_per_mm)
    cv2.rectangle(board, (0, 0), (size_px - 1, size_px - 1), (0, 0, 255), border_thickness)
    
    # 添加刻度数字（每10mm标注）
    font_scale = 0.5 * pixels_per_mm / 10
    for i in range(0, int(size_mm) + 1, 10):
        pos = int(i * pixels_per_mm)
        # 上边刻度
        cv2.putText(board, str(i), (pos + 2, 15), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 255), 1)
        # 左边刻度
        cv2.putText(board, str(i), (5, pos + 5), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 255), 1)
    
    cv2.imwrite(output_path, board)
    return board


if __name__ == "__main__":
    # 测试代码：创建合成标定板并测试检测
    print("创建合成标定板...")
    board = create_synthetic_calibration_board(size_mm=80, pixels_per_mm=15)
    print(f"标定板已保存到 calibration_board.png")
    
    # 测试检测
    calibrator = RedCrossCalibrator(board_size_mm=80.0)
    result = calibrator.calibrate(board)
    
    if result.success:
        print(f"标定成功！")
        print(f"像素/毫米比例: {result.pixels_per_mm:.2f}")
        print(f"检测到的角点:\n{result.corners}")
    else:
        print(f"标定失败: {result.error_message}")
