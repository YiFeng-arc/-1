import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import cv2
from PIL import Image, ImageTk
import numpy as np

# 导入模块
from ui_manager import UIManager
from business_manager import BusinessManager

# 设置现代UI主题
ctk.set_appearance_mode("Light")  # 可选: "System", "Dark", "Light"
ctk.set_default_color_theme("blue")  

class ModernApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("模拟静电场智能测绘与分析系统")
        self.geometry("1100x800")
        self.minsize(1000, 700)
        
        # 默认全屏模式
        try:
            self.state('zoomed')
        except Exception:
            self.attributes('-fullscreen', True)

        # UI Grid Layout: 1 row, 2 columns (Sidebar + Main Content)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # 初始化业务逻辑管理器
        self.business_manager = BusinessManager(self)
        self.has_camera = self.business_manager.has_camera
        self.mock_x = self.business_manager.mock_x
        self.mock_y = self.business_manager.mock_y
        
        # 初始化UI管理器
        self.ui_manager = UIManager(self)
        
        # 启动视频流
        self.video_loop()

    # ================= 业务与交互逻辑 ================= #

    def _log_msg(self, msg):
        """记录日志"""
        self.ui_manager.textbox_log.configure(state="normal")
        self.ui_manager.textbox_log.insert("end", msg + "\n")
        self.ui_manager.textbox_log.see("end") # 修复 CustomTkinter 滚动方法
        self.ui_manager.textbox_log.configure(state="disabled")

    def _on_mock_click(self, event):
        """模拟点击事件"""
        self.business_manager.mock_x = event.x
        self.business_manager.mock_y = event.y

    def _start_calibration(self):
        """开始标定流程"""
        if not self.has_camera:
            messagebox.showwarning("摄像头未连接", "请先连接摄像头后再进行标定")
            return
        
        self.ui_manager.calib_status_label.configure(text="状态: 正在检测...", text_color="#F39C12")
        
        # 调用业务逻辑进行标定
        success, message = self.business_manager.start_calibration()
        
        if success:
            result = self.business_manager.calibration_result
            self.ui_manager.calib_status_label.configure(text="状态: 检测成功!", text_color="#2ECC71")
            self.ui_manager.calib_info_label.configure(
                text=f"像素比例: {result.pixels_per_mm:.2f} px/mm\n"
                     f"中心偏移: ({result.center_offset[0]:.1f}, {result.center_offset[1]:.1f}) px"
            )
            self.ui_manager.btn_apply_calib.configure(state="normal")
            self._log_msg(f"[标定] 检测成功! 像素比例: {result.pixels_per_mm:.2f} px/mm")
        else:
            self.ui_manager.calib_status_label.configure(text="状态: 检测失败", text_color="#E74C3C")
            self.ui_manager.calib_info_label.configure(text=f"错误: {message}")
            self.ui_manager.btn_apply_calib.configure(state="disabled")
            self._log_msg(f"[标定] 检测失败: {message}")
    
    def _apply_calibration(self):
        """应用标定结果"""
        success = self.business_manager.apply_calibration()
        if success:
            result = self.business_manager.calibration_result
            self.ui_manager.calib_status_label.configure(text="状态: 已应用 ✓", text_color="#2ECC71")
            self._log_msg(f"[标定] 标定结果已应用到视觉追踪系统")
            messagebox.showinfo("标定成功",
                              f"像素比例: {result.pixels_per_mm:.2f} px/mm\n"
                              f"中心偏移: ({result.center_offset[0]:.1f}, {result.center_offset[1]:.1f}) px\n\n"
                              f"现在可以进入【测绘与采集】页面进行实验")
    
    def _reset_calibration(self):
        """重置标定"""
        self.business_manager.reset_calibration()
        self.ui_manager.calib_status_label.configure(text="状态: 未标定", text_color="#E74C3C")
        self.ui_manager.calib_info_label.configure(text="像素比例: --")
        self.ui_manager.btn_apply_calib.configure(state="disabled")
        self._log_msg("[标定] 标定已重置")

    def video_loop(self):
        """视频循环"""
        w = max(self.ui_manager.video_label.winfo_width(), 640)
        h = max(self.ui_manager.video_label.winfo_height(), 360)

        current_frame = None
        if self.has_camera:
            current_frame = self.business_manager.get_latest_frame()
            if current_frame is not None:
                debug_img = self.business_manager.process_frame(current_frame)
                if debug_img is not None:
                    cv_img = cv2.cvtColor(debug_img, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(cv_img).resize((w, h))
                    self.photo = ImageTk.PhotoImage(image=img)
                    self.ui_manager.video_label.configure(image=self.photo)
        else:
            # 模拟模式
            mock_img = self.business_manager.create_mock_frame(w, h)
            self.photo = ImageTk.PhotoImage(image=Image.fromarray(mock_img))
            self.ui_manager.video_label.configure(image=self.photo)

        # 标定页面视频循环（复用同一帧，避免重复采集造成卡顿）
        if hasattr(self.ui_manager, 'calib_video_label'):
            self._update_calibration_preview(current_frame)

        self.after(30, self.video_loop)

    def _update_calibration_preview(self, frame=None):
        """更新标定页面的视频预览"""
        if not hasattr(self.ui_manager, 'calib_video_label'):
            return

        w = max(self.ui_manager.calib_video_label.winfo_width(), 640)
        h = max(self.ui_manager.calib_video_label.winfo_height(), 480)

        if self.has_camera and frame is not None:
            debug_img = self.business_manager.update_calibration_preview(frame)
            if debug_img is not None:
                cv_img = cv2.cvtColor(debug_img, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(cv_img).resize((w, h))
                self.calib_photo = ImageTk.PhotoImage(image=img)
                self.ui_manager.calib_video_label.configure(image=self.calib_photo)
        else:
            # 模拟模式下的标定预览
            mock_img = np.ones((h, w, 3), dtype=np.uint8) * 200
            cv2.putText(mock_img, "Camera Not Connected", (w // 2 - 150, h // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            cv2.putText(mock_img, "Please connect camera to use calibration", (w // 2 - 220, h // 2 + 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 100), 1)
            self.calib_photo = ImageTk.PhotoImage(image=Image.fromarray(mock_img))
            self.ui_manager.calib_video_label.configure(image=self.calib_photo)

    def _capture_point(self):
        """捕获数据点"""
        try:
            voltage = float(self.ui_manager.voltage_var.get())
        except ValueError:
            messagebox.showerror("中断", "请在下位机表冠核验电位数据的数值准确性")
            return

        # 调用业务逻辑捕获点
        success, message = self.business_manager.capture_point(voltage)
        self._log_msg(message)

    def _clear_data(self):
        """清除所有数据"""
        self.business_manager.clear_data()
        self._log_msg("[SYS_OK] All data cleared.")

    def _generate_map(self):
        """生成电场图"""
        use_ai = self.ui_manager.use_ai_var.get()
        success, message = self.business_manager.generate_map(use_ai)
        if success:
            self._log_msg(message)
        else:
            messagebox.showwarning("特征矩阵稀疏", message)

    def _init_ai_client(self, event=None):
        """初始化 GitHub Models API 客服端"""
        token = self.ui_manager.api_key_var.get().strip()
        if not token:
            self.ui_manager.lbl_ai_status.configure(text="Token为空", text_color="red")
            return
            
        success, message = self.business_manager.init_ai_client(token)
        if success:
            self.ui_manager.lbl_ai_status.configure(text=message, text_color="green")
            self._append_chat("🤖 AI 助手", "我已经连接至云端大模型，可以解答您的物理问题了！\n")
        else:
            self.ui_manager.lbl_ai_status.configure(text=message, text_color="red")
            self._append_chat("⚠️ 系统提示", f"初始化失败，详细错误：{message}")

    def _append_chat(self, sender, text):
        """添加聊天消息"""
        self.ui_manager.chat_textbox.configure(state="normal")
        self.ui_manager.chat_textbox.insert("end", f"{sender}: \n{text}\n\n")
        self.ui_manager.chat_textbox.see("end") # 修复 CustomTkinter 滚动方法
        self.ui_manager.chat_textbox.configure(state="disabled")

    def _send_ai_msg(self):
        """发送AI消息"""
        user_text = self.ui_manager.chat_input.get().strip()
        if not user_text:
            return

        self.ui_manager.chat_input.delete(0, "end")
        self._append_chat("🧑(您)", user_text)
        
        # 调用业务逻辑发送消息
        success, message = self.business_manager.send_ai_msg(user_text)
        if not success:
            messagebox.showwarning("API 未连接", message)

    def on_closing(self):
        """关闭应用"""
        print("[主控级] 卸载显存与驱动信道...")
        self.business_manager.stop()
        self.destroy()

if __name__ == "__main__":
    app = ModernApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
