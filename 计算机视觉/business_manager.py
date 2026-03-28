import threading
import time
import cv2
import numpy as np
from PIL import Image, ImageTk
from hw_camera import CameraManager
from cv_tracker import VisionTracker
from data_engine import FieldAnalyzer
from hw_serial import SerialManager
from calibration import RedCrossCalibrator, CalibrationResult
from openai import OpenAI

class BusinessManager:
    def __init__(self, app):
        self.app = app
        self._init_core_components()
        self._init_threads()
    
    def _init_core_components(self):
        """初始化核心组件"""
        # 外接USB摄像头在本机映射为索引0
        self.camera_ctrl = CameraManager(camera_index=0)
        self.processor = VisionTracker()
        self.analyzer = FieldAnalyzer()
        self.serial_ctrl = SerialManager(port='COM3')
        self.calibrator = RedCrossCalibrator(board_size_mm=80.0)
        
        # 标定状态
        self.calibration_result: CalibrationResult = None
        self.is_calibrating = False
        
        self.FORCE_MOCK_MODE = False
        
        if self.FORCE_MOCK_MODE:
            self.has_camera = False
        else:
            self.has_camera = self.camera_ctrl.open()
            
        self.mock_x = 320
        self.mock_y = 180
        self.record_counter = 0

        # AI Assistant 令牌默认值存放处 (Github API)
        self.ai_client = None
        self.chat_history = []

        # 视频性能优化缓存
        self.latest_camera_frame = None
        self._last_calib_preview_time = 0.0
        self._calib_preview_interval = 0.2  # 标定实时检测降频到 5Hz，降低CPU占用
        self._cached_calib_preview = None
        
        # 线程控制
        self.camera_thread = None
        self.running = False
    
    def _init_threads(self):
        """初始化线程"""
        self.running = True
        self.camera_thread = threading.Thread(target=self._camera_capture_loop, daemon=True)
        self.camera_thread.start()
    
    def _camera_capture_loop(self):
        """摄像头采集线程"""
        while self.running:
            if self.has_camera:
                frame = self.camera_ctrl.capture_image()
                if frame is not None:
                    self.latest_camera_frame = frame
            time.sleep(0.03)  # 控制采集频率
    
    def stop(self):
        """停止业务逻辑"""
        self.running = False
        if self.camera_thread:
            self.camera_thread.join(timeout=1.0)
        self.camera_ctrl.close()
        if self.serial_ctrl.serial_conn:
            self.serial_ctrl.serial_conn.close()
    
    # --- 标定相关方法 ---    
    def start_calibration(self):
        """开始标定流程"""
        if not self.has_camera:
            return False, "摄像头未连接"
        
        self.is_calibrating = True
        
        # 优先复用主循环最新帧，避免重复采集导致瞬时卡顿
        frame = self.latest_camera_frame if self.latest_camera_frame is not None else self.camera_ctrl.capture_image()
        if frame is not None:
            result = self.calibrator.calibrate(frame)
            self.calibration_result = result
            
            self.is_calibrating = False
            return result.success, result.error_message if not result.success else ""
        else:
            self.is_calibrating = False
            return False, "无法获取图像"
    
    def apply_calibration(self):
        """应用标定结果"""
        if self.calibration_result and self.calibration_result.success:
            self.processor.apply_calibration(self.calibration_result)
            return True
        return False
    
    def reset_calibration(self):
        """重置标定"""
        self.processor.reset_calibration()
        self.calibration_result = None
    
    # --- 数据采集相关方法 ---    
    def capture_point(self, voltage):
        """捕获数据点"""
        self.record_counter += 1

        if self.has_camera:
            # 采点时复用实时预览帧，避免额外采集导致UI抖动
            frame = self.latest_camera_frame if self.latest_camera_frame is not None else self.camera_ctrl.capture_image()
            if frame is not None:
                coords, _ = self.processor.get_pen_tip_coordinate(frame)
                if coords:
                    phys_x, phys_y = coords
                    phys_x = round(phys_x, 1)  # 已自底向上更正为毫米，直接保留一位小数
                    phys_y = round(phys_y, 1)
                    self.analyzer.add_data_point(phys_x, phys_y, voltage)
                    return True, f"[{self.record_counter:02d}][SYS_OK] CV追踪 -> 物理位置 X: {phys_x:>5.1f} mm, Y: {phys_y:>5.1f} mm | {voltage}V"
                else:
                    return False, f"[{self.record_counter:02d}][FAILED] 机器视觉异常：本帧未能寻迹到 HSV 色彩标记！"
            else:
                return False, f"[{self.record_counter:02d}][FAILED] 无法获取摄像头图像！"
        else:
            # 模拟模式
            w = max(self.app.ui_manager.video_label.winfo_width(), 640)
            h = max(self.app.ui_manager.video_label.winfo_height(), 360)
            cx, cy = w // 2, h // 2
            
            # 计算模拟像素比例
            grid_size_px = min(w, h)
            pixels_per_mm = grid_size_px / 190.0
            
            phys_x = (self.mock_x - cx) / pixels_per_mm
            phys_y = (cy - self.mock_y) / pixels_per_mm
            
            # 四舍五入保留到 0.1 mm (远高于0.5mm精度要求)
            phys_x = round(phys_x, 1)
            phys_y = round(phys_y, 1)
            
            self.analyzer.add_data_point(phys_x, phys_y, voltage)
            return True, f"[{self.record_counter:02d}][MOCK_OK] 离线录入 -> 物理坐标 X: {phys_x:>5.1f} mm, Y: {phys_y:>5.1f} mm | 表显 {voltage}V"
    
    def clear_data(self):
        """清除所有数据"""
        self.analyzer.clear_data()
        self.record_counter = 0
    
    def generate_map(self, use_ai=True):
        """生成电场图"""
        if len(self.analyzer.points_x) < 5:
            return False, "特征矩阵稀疏，网格解算失败：最少需构建具有关联的5个非重合坐标基点以张开曲面。"
        
        algo_str = "[深度AI插值全场补偿]" if use_ai else "[标准实验原位点迹拟合]"
        self.analyzer.generate_electric_field_map(use_ai_interpolation=use_ai)
        return True, f">>> 核心挂载: 发起底层系统调用，开始渲染 {algo_str} 模式二维梯度场..."
    
    # --- AI 相关方法 ---    
    def init_ai_client(self, token):
        """初始化 GitHub Models API 客服端"""
        if not token:
            return False, "Token为空"
            
        try:
            # 根据 GitHub Models 文档，接入标准 openai 库
            self.ai_client = OpenAI(
                base_url="https://models.inference.ai.azure.com",
                api_key=token,
            )
            return True, "✅ 验证成功 (Ready)"
        except Exception as e:
            err_msg = str(e)
            return False, f"连接失败: {err_msg[:20]}..."
    
    def send_ai_msg(self, user_text):
        """发送AI消息"""
        if not self.ai_client:
            return False, "API 未连接"
            
        if not user_text:
            return False, "消息为空"

        # 构建聊天记录
        self.chat_history.append({"role": "user", "content": user_text})
        
        # 启用多线程防止卡死界面
        def fetch_api():
            try:
                response = self.ai_client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": "你是一位优秀的大学物理实验导师。你擅长指导“静电场模拟”等实验。请用简明扼要的中文回答用户提出的物理、AI相关或代码调试问题。"}
                    ] + self.chat_history,
                    model="gpt-4o",
                    temperature=0.7,
                )
                ai_reply = response.choices[0].message.content
                self.chat_history.append({"role": "assistant", "content": ai_reply})
                
                # 在主线程更新UI
                self.app.after(0, lambda: self.app.ui_manager._append_chat("🤖 AI 助手 (gpt-4o)", ai_reply))
                
            except Exception as e:
                self.app.after(0, lambda: self.app.ui_manager._append_chat("⚠️ 系统提示", f"大模型接口请求异常：{str(e)}"))

        threading.Thread(target=fetch_api, daemon=True).start()
        return True, "消息已发送"
    
    # --- 视频处理相关方法 ---    
    def get_latest_frame(self):
        """获取最新的摄像头帧"""
        return self.latest_camera_frame
    
    def process_frame(self, frame):
        """处理摄像头帧"""
        if frame is None:
            return None
        
        _, debug_img = self.processor.get_pen_tip_coordinate(frame)
        
        # 在真实画面上实时绘制历史采集点（使用显示坐标系，避免标定后刻度缩放与中心漂移）
        frame_h, frame_w = frame.shape[:2]
        for px_mm, py_mm, v in zip(self.analyzer.points_x, self.analyzer.points_y, self.analyzer.voltages):
            hx, hy = self.processor.physical_to_display_pixel(px_mm, py_mm, frame_w, frame_h)
            cv2.circle(debug_img, (hx, hy), 4, (0, 255, 255), -1)
        
        return debug_img
    
    def update_calibration_preview(self, frame):
        """更新标定预览"""
        if frame is None:
            return None
        
        now = time.perf_counter()

        if self.calibration_result and self.calibration_result.success:
            debug_img = self.calibrator.draw_calibration_result(frame, self.calibration_result)
            self._cached_calib_preview = debug_img
        else:
            # 标定预览检测降频，降低实时卡顿
            if (now - self._last_calib_preview_time) >= self._calib_preview_interval or self._cached_calib_preview is None:
                result = self.calibrator.calibrate(frame)
                self._cached_calib_preview = self.calibrator.draw_calibration_result(frame, result)
                self._last_calib_preview_time = now
            debug_img = self._cached_calib_preview
        
        return debug_img
    
    def create_mock_frame(self, width, height):
        """创建模拟帧"""
        mock_img = np.zeros((height, width, 3), np.uint8)
        mock_img[:] = (25, 30, 35)

        # 计算模拟像素比例
        grid_size_px = min(width, height)
        pixels_per_mm = grid_size_px / 190.0
        cx, cy = width // 2, height // 2

        # 最大绘制的毫米数 (向两边延伸)
        max_mm_x = int((width / 2) / pixels_per_mm) + 1
        max_mm_y = int((height / 2) / pixels_per_mm) + 1
        max_mm = max(max_mm_x, max_mm_y)

        # 绘制网格，包含1mm小格和10mm大格
        for i in range(1, max_mm + 1):
            is_major = (i % 10 == 0)
            is_mid = (i % 5 == 0) and not is_major

            # 大格高亮，中格稍暗，1mm小格最暗且最细
            color = (130, 140, 150) if is_major else ((70, 80, 90) if is_mid else (45, 50, 55))

            # 绘制刻度线
            px_pos = int(cx + i * pixels_per_mm)
            px_neg = int(cx - i * pixels_per_mm)
            if px_pos < width: cv2.line(mock_img, (px_pos, 0), (px_pos, height), color, 1)
            if px_neg > 0: cv2.line(mock_img, (px_neg, 0), (px_neg, height), color, 1)

            py_pos = int(cy + i * pixels_per_mm)
            py_neg = int(cy - i * pixels_per_mm)
            if py_pos < height: cv2.line(mock_img, (0, py_pos), (width, py_pos), color, 1)
            if py_neg > 0: cv2.line(mock_img, (0, py_neg), (width, py_neg), color, 1)

            # X/Y轴坐标数字(仅标注10mm大格)
            if is_major:
                if px_pos < width: cv2.putText(mock_img, f"{i}", (px_pos - 10, cy + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
                if px_neg > 0: cv2.putText(mock_img, f"{-i}", (px_neg - 15, cy + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
                if py_pos < height: cv2.putText(mock_img, f"{-i}", (cx + 5, py_pos + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
                if py_neg > 0: cv2.putText(mock_img, f"{i}", (cx + 5, py_neg + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

        # 十字主轴 (单独绘制盖补在上面)
        cv2.line(mock_img, (cx, 0), (cx, height), (100, 255, 100), 2)
        cv2.line(mock_img, (0, cy), (width, cy), (100, 255, 100), 2)

        # 文字提示置于右下方
        cv2.putText(mock_img, "Grid: 10mm/div | Target Precision: < 0.5mm  |  DEV MOCK", (width - 420, height - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)

        # 在离线雷达上绘制历史采集点
        for px_mm, py_mm, v in zip(self.analyzer.points_x, self.analyzer.points_y, self.analyzer.voltages):
            hx = int(px_mm * pixels_per_mm + cx)
            hy = int(cy - py_mm * pixels_per_mm)
            # 根据不同电压设置一些简单色差
            color = (0, int(255 - (v % 5) * 30), int(100 + (v % 5) * 30))
            cv2.circle(mock_img, (hx, hy), 5, color, -1)
            cv2.putText(mock_img, f"{v}V", (hx + 5, hy - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

        # 当前标点物理读数
        phys_xc = (self.mock_x - cx) / pixels_per_mm
        phys_yc = (cy - self.mock_y) / pixels_per_mm
        cv2.putText(mock_img, f"Target: X={phys_xc:.1f}mm, Y={phys_yc:.1f}mm", (20, height - 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 200, 0), 2)

        # 游标图案
        r = int(5 * pixels_per_mm)
        cv2.circle(mock_img, (self.mock_x, self.mock_y), r, (0, 0, 255), 1)
        cv2.line(mock_img, (self.mock_x - 15, self.mock_y), (self.mock_x + 15, self.mock_y), (0, 255, 255), 1)
        cv2.line(mock_img, (self.mock_x, self.mock_y - 15), (self.mock_x, self.mock_y + 15), (0, 255, 255), 1)

        return mock_img