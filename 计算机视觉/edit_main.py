import sys

with open('main.py', 'r', encoding='utf-8') as f:
    t = f.read()

t = t.replace('def _generate_map(self):', 'def _clear_data(self):\n        self.analyzer.clear_data()\n        self.record_counter = 0\n        self._log_msg(\"[SYS_OK] All data cleared.\")\n\n    def _generate_map(self):')

btn_str = 'self.btn_generate.pack(fill="x", side="bottom")\n\n        self.btn_clear = ctk.CTkButton(btn_frame, text="清除所有数据", fg_color="#E74C3C", hover_color="#C0392B", font=ctk.CTkFont("Microsoft YaHei", 13, "bold"), height=35, command=self._clear_data)\n        self.btn_clear.pack(fill="x", side="bottom", pady=(0,5))'

t = t.replace('self.btn_generate.pack(fill="x", side="bottom")', btn_str)

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(t)
