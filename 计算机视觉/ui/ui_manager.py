import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk

class UIManager:
    def __init__(self, app):
        self.app = app
        self._build_ui()
    
    def _build_ui(self):
        """构建完整UI"""
        self._build_sidebar()
        self._build_home_page()
        self._build_exp_page()
        self._build_calibration_page()
        self._build_ai_page()
        self.select_frame_by_name("home")
    
    def _build_sidebar(self):
        """左侧导航侧边栏"""
        self.sidebar_frame = ctk.CTkFrame(self.app, width=220, corner_radius=0, fg_color="#F8F9FA")
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_columnconfigure(0, weight=1)
        self.sidebar_frame.grid_rowconfigure(2, weight=1)

        logo_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="⚡ AI Field",
            font=ctk.CTkFont("Microsoft YaHei", size=34, weight="bold"),
            text_color="#0F172A"
        )
        logo_label.grid(row=0, column=0, padx=22, pady=(34, 24), sticky="w")

        nav_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        nav_frame.grid(row=1, column=0, padx=14, pady=(0, 10), sticky="ew")
        nav_frame.grid_columnconfigure(0, weight=1)

        base_btn_cfg = {
            "corner_radius": 10,
            "height": 48,
            "border_spacing": 8,
            "font": ctk.CTkFont("Microsoft YaHei", 15),
            "fg_color": "transparent",
            "text_color": "#0F172A",
            "hover_color": "#E9EEF6",
            "anchor": "w"
        }

        self.btn_home = ctk.CTkButton(
            nav_frame,
            text="🏠 首页概览",
            command=lambda: self.select_frame_by_name("home"),
            **base_btn_cfg
        )
        self.btn_home.grid(row=0, column=0, sticky="ew", padx=4, pady=6)

        self.btn_calib = ctk.CTkButton(
            nav_frame,
            text="📐 相机标定",
            command=lambda: self.select_frame_by_name("calibration"),
            **base_btn_cfg
        )
        self.btn_calib.grid(row=1, column=0, sticky="ew", padx=4, pady=6)

        self.btn_exp = ctk.CTkButton(
            nav_frame,
            text="📹 测绘与采集",
            command=lambda: self.select_frame_by_name("exp"),
            **base_btn_cfg
        )
        self.btn_exp.grid(row=2, column=0, sticky="ew", padx=4, pady=6)

        self.btn_ai = ctk.CTkButton(
            nav_frame,
            text="🤖 AI 实验助手",
            command=lambda: self.select_frame_by_name("ai"),
            **base_btn_cfg
        )
        self.btn_ai.grid(row=3, column=0, sticky="ew", padx=4, pady=6)

    def _build_home_page(self):
        """页面1：主页面（功能及使用方法）"""
        self.home_frame = ctk.CTkFrame(self.app, corner_radius=0, fg_color="#FFFFFF")
        
        # 头部 Banner
        title_lbl = ctk.CTkLabel(self.home_frame, text="静电场智能识别与分析系统", font=ctk.CTkFont("Microsoft YaHei", 28, "bold"), text_color="#1E3A8A")
        title_lbl.pack(pady=(60, 10))
        
        desc_lbl = ctk.CTkLabel(self.home_frame, text="基于openCV与插值算法，自动化获取探针坐标坐标，精准出图", font=ctk.CTkFont("Microsoft YaHei", 15), text_color="gray")
        desc_lbl.pack(pady=(0, 40))

        # 功能卡片横向布局
        cards_frame = ctk.CTkFrame(self.home_frame, fg_color="transparent")
        cards_frame.pack(fill="x", padx=60)
        cards_frame.grid_columnconfigure((0, 1, 2), weight=1)

        def make_card(parent, row, col, icon, title, desc):
            f = ctk.CTkFrame(parent, corner_radius=15, fg_color="#F3F4F6", height=180)
            f.grid(row=row, column=col, padx=15, pady=15, sticky="ew")
            l1 = ctk.CTkLabel(f, text=icon, font=("Arial", 36))
            l1.pack(pady=(20, 10))
            l2 = ctk.CTkLabel(f, text=title, font=ctk.CTkFont("Microsoft YaHei", 16, "bold"))
            l2.pack(pady=(0, 5))
            l3 = ctk.CTkLabel(f, text=desc, font=ctk.CTkFont("Microsoft YaHei", 12), text_color="#555", wraplength=180)
            l3.pack(pady=(0, 20), padx=10)

        make_card(cards_frame, 0, 0, "🎥", "智能视觉捕捉", "利用OpenCV图像识别技术追踪高亮探针，解决传统眼看手绘的数据迟滞与测量误差。")
        make_card(cards_frame, 0, 1, "📊", "高斯插值建模", "自动将散点数据经过Scipy样条插值，重构连续电场分布曲面与场强剃度场。")
        make_card(cards_frame, 0, 2, "🤖", "GPT 智能辅助", "对接GitHub模型API，为实验过程中的物理疑问和调试提供AI级的实时技术答疑。")

        # 使用提示卡片
        help_frame = ctk.CTkFrame(self.home_frame, corner_radius=15, fg_color="#EBF5FF")
        help_frame.pack(fill="x", padx=75, pady=40)
        help_title = ctk.CTkLabel(help_frame, text="快速使用指南", font=ctk.CTkFont("Microsoft YaHei", 16, "bold"), text_color="#1E3A8A")
        help_title.pack(anchor="w", padx=20, pady=(20, 10))
        help_text = (
            "1. 点击左侧【📹 测绘与采集】进入实验操作盘。\n"
            "2. 在面板右下侧输入当前的探针电压值，点击【捕获本位数据】自动截取屏幕坐标。\n"
            "3. 采集至少5个以上的不同点位后，点击【🚀合成全局电场图】查看结果。\n"
            "4. 遇到理论问题？左侧进入【🤖 AI 实验助手】输入API后进行答疑。"
        )
        help_desc = ctk.CTkLabel(help_frame, text=help_text, font=ctk.CTkFont("Microsoft YaHei", 13), justify="left", text_color="#333")
        help_desc.pack(anchor="w", padx=20, pady=(0, 20))

    def _build_exp_page(self):
        """页面2：数据拍照处理及图表生成页面"""
        self.exp_frame = ctk.CTkFrame(self.app, corner_radius=0, fg_color="#FFFFFF")
        
        # 优化布局：左侧 70% 宽度给正方形图纸，右侧 30% 给控制和日志
        self.exp_frame.rowconfigure(0, weight=1) 
        self.exp_frame.columnconfigure(0, weight=7)
        self.exp_frame.columnconfigure(1, weight=3)

        # 1. 视频显示区 (占左侧完整块，为了更好地展示正方坐标纸比例)
        self.view_panel = ctk.CTkFrame(self.exp_frame, fg_color="#F8F9FA", corner_radius=10)
        self.view_panel.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        
        lbl_view = ctk.CTkLabel(self.view_panel, text="实时探针示波视窗 (Camera Preview)  |  实验对标精度要求: ± 0.5 mm", font=ctk.CTkFont("Microsoft YaHei", 14, "bold"))
        lbl_view.pack(anchor="w", padx=15, pady=(10, 0))
        
        # 真实的图像呈现容器
        self.video_label = tk.Label(self.view_panel, bg="#111")
        self.video_label.pack(fill="both", expand=True, padx=15, pady=(5, 15))
        if not self.app.has_camera:
           self.video_label.bind("<Button-1>", self.app._on_mock_click)

        # 侧边控制组容器
        side_panel = ctk.CTkFrame(self.exp_frame, fg_color="transparent")
        side_panel.grid(row=0, column=1, padx=(0, 20), pady=20, sticky="nsew")
        side_panel.rowconfigure(0, weight=1)
        side_panel.rowconfigure(1, weight=0)

        # 2. 日志区 (放入侧边上册)
        self.log_panel = ctk.CTkFrame(side_panel, fg_color="#F8F9FA", corner_radius=10)
        self.log_panel.grid(row=0, column=0, pady=(0, 10), sticky="nsew")
        
        lbl_log = ctk.CTkLabel(self.log_panel, text="系统操作及数据游标日志", font=ctk.CTkFont("Microsoft YaHei", 12, "bold"))
        lbl_log.pack(anchor="w", padx=15, pady=(10, 5))

        self.textbox_log = ctk.CTkTextbox(self.log_panel, font=ctk.CTkFont("Consolas", 12), text_color="#333", fg_color="#FFFFFF")
        self.textbox_log.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        # 3. 控制面板区 (放入侧边下方固定高度)
        self.ctrl_panel = ctk.CTkFrame(side_panel, fg_color="#EBF5FF", corner_radius=10)
        self.ctrl_panel.grid(row=1, column=0, sticky="nsew")
        
        lbl_ctrl = ctk.CTkLabel(self.ctrl_panel, text="数据总线与控制", font=ctk.CTkFont("Microsoft YaHei", 14, "bold"), text_color="#1E3A8A")
        lbl_ctrl.pack(anchor="w", padx=15, pady=(10, 5))

        # 参数配置（一上一下排布，避免拥挤）
        config_frame = ctk.CTkFrame(self.ctrl_panel, fg_color="transparent")
        config_frame.pack(fill="x", padx=15, pady=5)
        
        ctk.CTkLabel(config_frame, text="数据链路:", font=ctk.CTkFont("Microsoft YaHei", 12)).grid(row=0, column=0, sticky="w", pady=5)
        self.combo_port = ctk.CTkComboBox(config_frame, values=["虚拟挂载 (纯软)", "COM3"], state="readonly", width=180)
        self.combo_port.grid(row=0, column=1, padx=10, pady=5)
        
        ctk.CTkLabel(config_frame, text="检测电位(V):", font=ctk.CTkFont("Microsoft YaHei", 12)).grid(row=1, column=0, sticky="w", pady=5)
        self.voltage_var = ctk.StringVar(value="5.0")
        self.entry_voltage = ctk.CTkEntry(config_frame, textvariable=self.voltage_var, font=ctk.CTkFont("Microsoft YaHei", 16, "bold"), justify="center", width=180)
        self.entry_voltage.grid(row=1, column=1, padx=10, pady=5)

        # 采集操作需求说明
        collect_req_text = (
            "采集操作需求：\n"
            "1) 建议先完成【相机标定】并应用；\n"
            "2) 电压读数稳定后再点击采集；\n"
            "3) 点位尽量分散（相邻点建议≥5mm）；\n"
            "4) 至少采集5个非重合点再生成场图。"
        )
        self.collect_req_label = ctk.CTkLabel(
            self.ctrl_panel,
            text=collect_req_text,
            justify="left",
            anchor="w",
            text_color="#1F2937",
            font=ctk.CTkFont("Microsoft YaHei", 11),
            wraplength=300
        )
        self.collect_req_label.pack(fill="x", padx=15, pady=(5, 8))

        # 功能按钮
        btn_frame = ctk.CTkFrame(self.ctrl_panel, fg_color="transparent")
        btn_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        self.btn_capture = ctk.CTkButton(btn_frame, text="🎯 捕获本位数据", fg_color="#2ECC71", hover_color="#27AE60", 
                                         font=ctk.CTkFont("Microsoft YaHei", 13, "bold"), height=35, command=self.app._capture_point)
        self.btn_capture.pack(fill="x", side="top", pady=(10, 5))

        self.btn_clear = ctk.CTkButton(btn_frame, text="🗑️ 清除所有数据", fg_color="#E74C3C", hover_color="#C0392B", font=ctk.CTkFont("Microsoft YaHei", 13, "bold"), height=35, command=self.app._clear_data)
        self.btn_clear.pack(fill="x", side="top", pady=(5, 5))

        # 默认开启AI空间密度全局补偿插值
        self.use_ai_var = ctk.BooleanVar(value=True)

        self.btn_generate = ctk.CTkButton(btn_frame, text="🚀 合成超清电场图", fg_color="#9C27B0", hover_color="#8E24AA",
                                         font=ctk.CTkFont("Microsoft YaHei", 13, "bold"), height=35, command=self.app._generate_map)
        self.btn_generate.pack(fill="x", side="bottom")

    def _build_ai_page(self):
        """页面3：AI助手辅助实验页面"""
        self.ai_frame = ctk.CTkFrame(self.app, corner_radius=0, fg_color="#F3F4F6")
        
        self.ai_frame.grid_rowconfigure(2, weight=1)
        self.ai_frame.grid_columnconfigure(0, weight=1)

        # 顶部配置栏
        top_bar = ctk.CTkFrame(self.ai_frame, fg_color="#FFFFFF", height=60, corner_radius=0)
        top_bar.grid(row=0, column=0, sticky="ew")
        top_bar.pack_propagate(False)

        ctk.CTkLabel(top_bar, text="⚙️ Github Student Models 配置:", font=ctk.CTkFont("Microsoft YaHei", 13, "bold")).pack(side="left", padx=20)
        
        self.api_key_var = ctk.StringVar()
        self.entry_apikey = ctk.CTkEntry(top_bar, textvariable=self.api_key_var, show="*", placeholder_text="输入 GitHub Personal Access Token (按回车连接)", width=350)
        self.entry_apikey.pack(side="left", padx=10, pady=10)
        self.entry_apikey.bind("<Return>", self.app._init_ai_client)
        
        self.lbl_ai_status = ctk.CTkLabel(top_bar, text="等待连接...", text_color="red", font=ctk.CTkFont("Microsoft YaHei", 12))
        self.lbl_ai_status.pack(side="left", padx=10)

        # 欢迎卡片
        intro_str = (
            "👋 您好！我是您的物理实验 AI 助手 (Powered by GPT-4o)。\n\n"
            "您可以通过 GitHub 学生包的 Models API 免费向我提问。\n"
            "我可以帮您解答：等势面特点、数据分析异常、实验操作要点等物理问题！\n"
            "初次使用，请先在上方填入 Token 并按回车键！"
        )
        intro_box = ctk.CTkFrame(self.ai_frame, fg_color="#E0F2FE", corner_radius=10)
        intro_box.grid(row=1, column=0, sticky="ew", padx=20, pady=(20, 10))
        ctk.CTkLabel(intro_box, text=intro_str, font=ctk.CTkFont("Microsoft YaHei", 13), text_color="#0369A1", justify="left").pack(padx=20, pady=20, anchor="w")

        # 聊天显示区
        self.chat_textbox = ctk.CTkTextbox(self.ai_frame, font=ctk.CTkFont("Microsoft YaHei", 13), fg_color="#FFFFFF", text_color="#333", wrap="word")
        self.chat_textbox.grid(row=2, column=0, sticky="nsew", padx=20, pady=10)
        self.chat_textbox.configure(state="disabled")

        # 聊天输入区
        bottom_bar = ctk.CTkFrame(self.ai_frame, fg_color="transparent")
        bottom_bar.grid(row=3, column=0, sticky="ew", padx=20, pady=(10, 20))
        
        self.chat_input = ctk.CTkEntry(bottom_bar, height=45, placeholder_text="请输入您的物理/实验问题...", font=ctk.CTkFont("Microsoft YaHei", 14))
        self.chat_input.pack(side="left", fill="x", expand=True, padx=(0,10))
        self.chat_input.bind("<Return>", lambda event: self.app._send_ai_msg())

        btn_send = ctk.CTkButton(bottom_bar, text="🚀 发送", width=100, height=45, font=ctk.CTkFont("Microsoft YaHei", 14, "bold"), fg_color="#3498DB", hover_color="#2980B9", command=self.app._send_ai_msg)
        btn_send.pack(side="right")

    def _build_calibration_page(self):
        """页面：相机标定页面"""
        self.calib_frame = ctk.CTkFrame(self.app, corner_radius=0, fg_color="#FFFFFF")
        
        # 标题
        title_frame = ctk.CTkFrame(self.calib_frame, fg_color="#F8F9FA", corner_radius=10)
        title_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        title_lbl = ctk.CTkLabel(title_frame, text="📐 相机标定 - 红色十字交叉标定板",
                                 font=ctk.CTkFont("Microsoft YaHei", 18, "bold"), text_color="#1E3A8A")
        title_lbl.pack(pady=15)
        
        desc_lbl = ctk.CTkLabel(title_frame,
                               text="标定板规格：80x80mm，红色毫米尺线，多十字交叉 | 请将标定板放置在摄像头视野中央",
                               font=ctk.CTkFont("Microsoft YaHei", 12), text_color="#555")
        desc_lbl.pack(pady=(0, 15))
        
        # 主内容区：左侧视频，右侧控制
        content_frame = ctk.CTkFrame(self.calib_frame, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        content_frame.rowconfigure(0, weight=1)
        content_frame.columnconfigure(0, weight=7)
        content_frame.columnconfigure(1, weight=3)
        
        # 左侧：视频显示区
        self.calib_view_panel = ctk.CTkFrame(content_frame, fg_color="#F8F9FA", corner_radius=10)
        self.calib_view_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        lbl_calib_view = ctk.CTkLabel(self.calib_view_panel, text="标定板实时检测",
                                      font=ctk.CTkFont("Microsoft YaHei", 14, "bold"))
        lbl_calib_view.pack(anchor="w", padx=15, pady=(10, 0))
        
        self.calib_video_label = tk.Label(self.calib_view_panel, bg="#111")
        self.calib_video_label.pack(fill="both", expand=True, padx=15, pady=(5, 15))
        
        # 右侧：控制面板
        calib_ctrl_panel = ctk.CTkFrame(content_frame, fg_color="#EBF5FF", corner_radius=10)
        calib_ctrl_panel.grid(row=0, column=1, sticky="nsew")
        
        lbl_calib_ctrl = ctk.CTkLabel(calib_ctrl_panel, text="标定控制",
                                      font=ctk.CTkFont("Microsoft YaHei", 14, "bold"), text_color="#1E3A8A")
        lbl_calib_ctrl.pack(anchor="w", padx=15, pady=(15, 10))
        
        # 标定状态显示
        self.calib_status_frame = ctk.CTkFrame(calib_ctrl_panel, fg_color="#FFFFFF", corner_radius=8)
        self.calib_status_frame.pack(fill="x", padx=15, pady=10)
        
        self.calib_status_label = ctk.CTkLabel(self.calib_status_frame, text="状态: 未标定",
                                              font=ctk.CTkFont("Microsoft YaHei", 12), text_color="#E74C3C")
        self.calib_status_label.pack(pady=10)
        
        self.calib_info_label = ctk.CTkLabel(self.calib_status_frame, text="像素比例: --",
                                            font=ctk.CTkFont("Microsoft YaHei", 11), text_color="#555")
        self.calib_info_label.pack(pady=(0, 10))
        
        # 标定按钮
        btn_calib_frame = ctk.CTkFrame(calib_ctrl_panel, fg_color="transparent")
        btn_calib_frame.pack(fill="x", padx=15, pady=10)
        
        self.btn_start_calib = ctk.CTkButton(btn_calib_frame, text="🎯 开始标定", fg_color="#3498DB", hover_color="#2980B9",
                                            font=ctk.CTkFont("Microsoft YaHei", 13, "bold"), height=40,
                                            command=self.app._start_calibration)
        self.btn_start_calib.pack(fill="x", pady=(5, 5))
        
        self.btn_apply_calib = ctk.CTkButton(btn_calib_frame, text="✅ 应用标定结果", fg_color="#2ECC71", hover_color="#27AE60",
                                            font=ctk.CTkFont("Microsoft YaHei", 13, "bold"), height=40,
                                            command=self.app._apply_calibration, state="disabled")
        self.btn_apply_calib.pack(fill="x", pady=(5, 5))
        
        self.btn_reset_calib = ctk.CTkButton(btn_calib_frame, text="🔄 重置标定", fg_color="#E74C3C", hover_color="#C0392B",
                                            font=ctk.CTkFont("Microsoft YaHei", 13, "bold"), height=40,
                                            command=self.app._reset_calibration)
        self.btn_reset_calib.pack(fill="x", pady=(5, 5))
        
        # 使用说明
        help_frame = ctk.CTkFrame(calib_ctrl_panel, fg_color="#FFF3CD", corner_radius=8)
        help_frame.pack(fill="x", padx=15, pady=10)
        
        help_title = ctk.CTkLabel(help_frame, text="使用说明", font=ctk.CTkFont("Microsoft YaHei", 12, "bold"), text_color="#856404")
        help_title.pack(anchor="w", padx=10, pady=(10, 5))
        
        help_text = (
            "1. 将红色标定板放置在摄像头视野中央\n"
            "2. 确保标定板平整，无反光\n"
            "3. 点击【开始标定】自动检测\n"
            "4. 检测成功后点击【应用标定结果】\n"
            "5. 标定完成后可进入【测绘与采集】页面"
        )
        help_label = ctk.CTkLabel(help_frame, text=help_text, font=ctk.CTkFont("Microsoft YaHei", 10),
                                 text_color="#856404", justify="left")
        help_label.pack(anchor="w", padx=10, pady=(0, 10))

    def select_frame_by_name(self, name):
        """控制侧边栏样式并切换页面"""
        # 按钮样式切换
        active_fg = "#DCEBFF"
        active_text = "#0B3B8C"
        normal_text = "#0F172A"

        self.btn_home.configure(
            fg_color=active_fg if name == "home" else "transparent",
            text_color=active_text if name == "home" else normal_text
        )
        self.btn_calib.configure(
            fg_color=active_fg if name == "calibration" else "transparent",
            text_color=active_text if name == "calibration" else normal_text
        )
        self.btn_exp.configure(
            fg_color=active_fg if name == "exp" else "transparent",
            text_color=active_text if name == "exp" else normal_text
        )
        self.btn_ai.configure(
            fg_color=active_fg if name == "ai" else "transparent",
            text_color=active_text if name == "ai" else normal_text
        )

        # 页面切换
        if name == "home":
            self.home_frame.grid(row=0, column=1, sticky="nsew")
        else:
            self.home_frame.grid_forget()
            
        if name == "calibration":
            self.calib_frame.grid(row=0, column=1, sticky="nsew")
        else:
            self.calib_frame.grid_forget()
            
        if name == "exp":
            self.exp_frame.grid(row=0, column=1, sticky="nsew")
        else:
            self.exp_frame.grid_forget()
            
        if name == "ai":
            self.ai_frame.grid(row=0, column=1, sticky="nsew")
        else:
            self.ai_frame.grid_forget()
    
    def _append_chat(self, sender, text):
        """添加聊天消息"""
        self.chat_textbox.configure(state="normal")
        self.chat_textbox.insert("end", f"{sender}: \n{text}\n\n")
        self.chat_textbox.see("end") # 修复 CustomTkinter 滚动方法
        self.chat_textbox.configure(state="disabled")