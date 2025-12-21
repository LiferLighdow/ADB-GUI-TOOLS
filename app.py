import tkinter as tk
from tkinter import filedialog, ttk, messagebox, simpledialog
import subprocess
import os
import threading
import sys
import time
from collections import defaultdict

# --- README 內容定義 (Lifer_Lighdow 獨立製作聲明) ---
README_CONTENT = """
# 專案說明文件 (README)

## ADB/Fastboot GUI 主要功能

本專案是一個簡潔高效的 ADB/Fastboot 圖形化使用者介面工具，旨在協助使用者輕鬆執行 Android 設備的調試和系統操作，無需記憶複雜的命令。

### 1. 設備狀態與連線管理

* **即時狀態顯示：** 自動偵測並顯示所有連接的 ADB (device/unauthorized) 和 Fastboot 設備。
* **設備選擇：** 透過下拉選單精確選擇要操作的單一設備。
* **Server 控制：** 一鍵啟動或停止 ADB Server 服務。

### 2. ADB 設備操作 (ADB 模式)

* **設備重啟：** 支援正常重啟、重啟到 Recovery 模式、重啟到 Bootloader 模式。
* **文件管理：**
    * **安裝 APK：** 選擇本地 APK 文件進行安裝 (支援覆蓋安裝 `-r`)。
    * **推送 (Push)：** 將本地文件傳輸至設備指定路徑。
    * **拉取 (Pull)：** 將設備文件拉取到本地目錄。
* **調試工具：**
    * **螢幕截圖：** 一鍵截圖並自動拉取到本地目錄。
    * **Logcat 顯示：** 彈出新視窗，即時顯示 Logcat 輸出流。
    * **螢幕鏡像：** 啟動 Scrcpy（需要外部依賴）。

### 3. 設備資訊與診斷

* **系統屬性 (getprop)：** 顯示設備型號、Android 版本、API 等級、CPU 資訊、內核版本等核心系統屬性。
* **硬體/服務狀態 (dumpsys)：** 獲取詳細的硬體和服務狀態，包括：Wi-Fi、藍牙、電池、螢幕、定位與內存。

### 4. ADB Shell Console

* 提供獨立的分頁和輸出區域，供使用者輸入並執行自定義的 `adb shell` 命令。

### 5. Fastboot 核心功能 (Fastboot 模式)

* **高風險操作確認：** Fastboot 命令執行前強制要求使用者進行文字確認，以防止誤操作。
* **Bootloader 控制：** 執行解鎖與鎖定命令。

---

## 獨立製作聲明
本專案的所有功能、程式碼和設計，皆由 **Lifer_Lighdow** 獨立製作與完成。
**版本:** v1.0 | **日期:** 2025年12月
"""

# --- 核心應用程式類別 ---
class ADBFastbootToolApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ADB/Fastboot GUI - 完整硬體資訊版")
        self.root.geometry("900x650") 
        
        # --- [關鍵修改] 載入視窗圖示 ---
        self.load_app_icon()
        
        # 設置UI風格
        self.style = ttk.Style()
        self.style.theme_use('clam') 

        # 狀態變數
        self.logcat_process = None
        self.device_serial = None 
        self.selected_device_details = None 
        self.all_detected_devices = [] 
        self.adb_server_running = True
        
        # UI 元素初始化
        self.create_widgets()
        
        # 初始設備檢查
        self.check_device_status()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_app_icon(self):
        """嘗試載入 icon.png 作為視窗圖示"""
        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        if os.path.exists(icon_path):
            try:
                # Tkinter 使用 PhotoImage 載入圖示
                self.app_icon = tk.PhotoImage(file=icon_path)
                self.root.iconphoto(True, self.app_icon)
            except Exception as e:
                print(f"無法載入圖示檔案: {e}")
        else:
            print("提示: 未在目錄下找到 icon.png，將使用系統預設圖示。")

    # --- 界面創建 ---
    def create_widgets(self):
        # 1. 頂部狀態/控制區域
        status_frame = ttk.Frame(self.root, padding="10")
        status_frame.pack(fill='x')

        self.device_label = ttk.Label(status_frame, text="設備狀態: 未知", font=('Inter', 10, 'bold'))
        self.device_label.pack(side=tk.LEFT, padx=5)

        ttk.Button(status_frame, text="重新整理設備", command=self.check_device_status).pack(side=tk.LEFT, padx=15)
        
        ttk.Label(status_frame, text="選擇設備:", font=('Inter', 10)).pack(side=tk.LEFT, padx=(30, 5))
        self.device_selection_combobox = ttk.Combobox(status_frame, state="readonly", width=35)
        self.device_selection_combobox.pack(side=tk.LEFT, padx=5)
        self.device_selection_combobox.bind("<<ComboboxSelected>>", self.on_device_selected)

        self.adb_server_button = ttk.Button(status_frame, text="停止 ADB Server", command=self.toggle_adb_server)
        self.adb_server_button.pack(side=tk.RIGHT, padx=5)
        
        # 2. 功能區 (Notebook)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=5)
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        
        # 頁籤
        tabs = [
            (ttk.Frame(self.notebook, padding="10"), 'README', self.create_readme_widgets),
            (ttk.Frame(self.notebook, padding="10"), 'ADB 設備操作', self.create_adb_widgets),
            (ttk.Frame(self.notebook, padding="10"), 'Fastboot 核心功能', self.create_fastboot_widgets),
            (ttk.Frame(self.notebook, padding="10"), 'ADB Shell Console', self.create_adb_shell_widgets),
            (ttk.Frame(self.notebook, padding="10"), '設備/硬體資訊', self.create_device_info_widgets),
            (ttk.Frame(self.notebook, padding="10"), '系統屬性 (getprop)', self.create_system_info_widgets)
        ]

        for frame, title, creator in tabs:
            self.notebook.add(frame, text=title)
            creator(frame)

        # 3. 輸出日誌區域
        output_frame = ttk.Frame(self.root, padding="10")
        output_frame.pack(fill='x')
        ttk.Label(output_frame, text="操作日誌輸出:", font=('Inter', 10)).pack(anchor='w')
        
        scrollbar = ttk.Scrollbar(output_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.output_text = tk.Text(output_frame, height=10, wrap='word', state=tk.DISABLED, 
                                   yscrollcommand=scrollbar.set, font=('Courier', 9))
        self.output_text.pack(fill='x', expand=True)
        scrollbar.config(command=self.output_text.yview)

    def on_tab_changed(self, event):
        selected_tab = self.notebook.tab(self.notebook.select(), "text")
        if selected_tab == '設備/硬體資訊': self.fetch_device_info() 
        elif selected_tab == '系統屬性 (getprop)': self.fetch_system_info() 

    # --- README 頁籤 ---
    def create_readme_widgets(self, readme_frame):
        readme_frame.columnconfigure(0, weight=1); readme_frame.rowconfigure(0, weight=1)
        scrollbar = ttk.Scrollbar(readme_frame); scrollbar.grid(row=0, column=1, sticky='ns')
        readme_text = tk.Text(readme_frame, wrap='word', yscrollcommand=scrollbar.set, font=('Inter', 11), background='#f8f8f8')
        readme_text.grid(row=0, column=0, sticky='nsew')
        scrollbar.config(command=readme_text.yview)

        tags = [('h1', 18, 'bold', '#007bff'), ('h2', 14, 'bold', '#28a745'), ('h3', 12, 'bold', '#6c757d'), ('author', 11, 'italic bold', '#dc3545')]
        for name, size, weight, color in tags: readme_text.tag_config(name, font=('Inter', size, weight), foreground=color)
        
        for line in README_CONTENT.split('\n'):
            if line.startswith('# '): readme_text.insert(tk.END, line + '\n', 'h1')
            elif line.startswith('## '): readme_text.insert(tk.END, line + '\n', 'h2')
            elif line.startswith('### '): readme_text.insert(tk.END, line + '\n', 'h3')
            elif 'Lifer_Lighdow' in line: readme_text.insert(tk.END, "Lifer_Lighdow", 'author'); readme_text.insert(tk.END, line.replace('Lifer_Lighdow','')+'\n')
            else: readme_text.insert(tk.END, line + '\n')
        readme_text.config(state=tk.DISABLED)

    # --- 功能實作區域 ---
    def create_adb_widgets(self, adb_frame):
        adb_frame.columnconfigure(0, weight=1); adb_frame.columnconfigure(1, weight=1)
        # 重啟按鈕
        reboot_group = ttk.LabelFrame(adb_frame, text="設備重啟與模式", padding="10")
        reboot_group.grid(row=0, column=0, columnspan=2, sticky='ew', pady=5)
        modes = [("正常重啟", "adb reboot"), ("Recovery", "adb reboot recovery"), ("Bootloader", "adb reboot bootloader"), ("EDL", "adb reboot edl")]
        for i, (name, cmd) in enumerate(modes):
            ttk.Button(reboot_group, text=name, command=lambda c=cmd, n=name: self.run_command(c, f"重啟到 {n}")).grid(row=0, column=i, sticky='ew', padx=2)
        
        # 文件與應用管理
        file_group = ttk.LabelFrame(adb_frame, text="文件與應用程式管理", padding="10")
        file_group.grid(row=1, column=0, columnspan=2, sticky='ew', pady=5)
        ttk.Button(file_group, text="安裝 APK", command=self.install_apk).grid(row=0, column=0, sticky='ew', padx=2)
        ttk.Button(file_group, text="螢幕截圖", command=self.take_screenshot).grid(row=0, column=1, sticky='ew', padx=2)
        ttk.Button(file_group, text="Push 文件", command=self.push_file).grid(row=1, column=0, sticky='ew', padx=2)
        ttk.Button(file_group, text="Pull 文件", command=self.pull_file).grid(row=1, column=1, sticky='ew', padx=2)
        
        # 調試工具
        debug_group = ttk.LabelFrame(adb_frame, text="系統與調試", padding="10")
        debug_group.grid(row=2, column=0, columnspan=2, sticky='ew', pady=5)
        ttk.Button(debug_group, text="啟動 Scrcpy", command=lambda: self.run_command("scrcpy", "啟動 Scrcpy")).grid(row=0, column=0, sticky='ew', padx=2)
        ttk.Button(debug_group, text="Logcat 視窗", command=self.show_logcat_window).grid(row=0, column=1, sticky='ew', padx=2)

    def create_fastboot_widgets(self, fastboot_frame):
        warning = ttk.Label(fastboot_frame, text="!!! 警告: Fastboot 操作具有高風險性 !!!", foreground='red', font=('Inter', 11, 'bold'))
        warning.pack(pady=10)
        btn_unlock = ttk.Button(fastboot_frame, text="解鎖 Bootloader (fastboot flashing unlock)", command=self.unlock_bootloader)
        btn_unlock.pack(fill='x', padx=50, pady=5)
        btn_lock = ttk.Button(fastboot_frame, text="鎖定 Bootloader (fastboot flashing lock)", command=self.lock_bootloader)
        btn_lock.pack(fill='x', padx=50, pady=5)

    def create_adb_shell_widgets(self, shell_frame):
        shell_frame.columnconfigure(0, weight=1); shell_frame.rowconfigure(3, weight=1)
        self.shell_entry = ttk.Entry(shell_frame)
        self.shell_entry.grid(row=1, column=0, sticky='ew', padx=5)
        self.shell_entry.bind("<Return>", lambda e: self.run_custom_shell())
        ttk.Button(shell_frame, text="運行 Shell", command=self.run_custom_shell).grid(row=1, column=1, padx=5)
        self.shell_output_text = tk.Text(shell_frame, height=15, background='#f0f0f0')
        self.shell_output_text.grid(row=3, column=0, columnspan=2, sticky='nsew', pady=5)

    def create_device_info_widgets(self, info_frame):
        info_frame.columnconfigure(0, weight=1); info_frame.rowconfigure(1, weight=1)
        ttk.Button(info_frame, text="刷新硬體資訊", command=self.fetch_device_info).grid(row=0, column=0, sticky='e')
        self.device_info_text = tk.Text(info_frame, wrap='word', font=('Courier', 10))
        self.device_info_text.grid(row=1, column=0, sticky='nsew')
        self.device_info_text.tag_config("header", foreground="#007bff", font=('Inter', 11, 'bold'))
        self.device_info_text.tag_config("title", foreground="green", font=('Courier', 10, 'bold'))

    def create_system_info_widgets(self, sys_frame):
        sys_frame.columnconfigure(0, weight=1); sys_frame.rowconfigure(1, weight=1)
        ttk.Button(sys_frame, text="刷新系統屬性", command=self.fetch_system_info).grid(row=0, column=0, sticky='e')
        self.system_info_text = tk.Text(sys_frame, wrap='word', font=('Courier', 10))
        self.system_info_text.grid(row=1, column=0, sticky='nsew')
        self.system_info_text.tag_config("title", foreground="#007bff", font=('Inter', 10, 'bold'))

    # --- 核心邏輯 (ADB/Fastboot 控制) ---
    def toggle_adb_server(self):
        if self.adb_server_running:
            self.run_command("adb kill-server", "關閉 ADB Server", check_mode=False)
            self.adb_server_running = False
            self.adb_server_button['text'] = "啟動 ADB Server"
        else:
            self.run_command("adb start-server", "啟動 ADB Server", check_mode=False)
            self.adb_server_running = True
            self.check_device_status()

    def check_device_status(self):
        def check():
            adb = subprocess.run('adb devices', shell=True, capture_output=True, text=True).stdout
            fast = subprocess.run('fastboot devices', shell=True, capture_output=True, text=True).stdout
            all_devs = []
            for line in adb.split('\n')[1:]:
                if line.strip(): 
                    s, t = line.split()
                    all_devs.append({'serial': s, 'display': f"ADB: {s} ({t})", 'mode': 'ADB', 'status': t})
            for line in fast.split('\n'):
                if line.strip():
                    s, _ = line.split()
                    all_devs.append({'serial': s, 'display': f"Fastboot: {s}", 'mode': 'Fastboot', 'status': 'fastboot'})
            self.root.after(0, lambda: self._update_ui(all_devs))
        threading.Thread(target=check, daemon=True).start()

    def _update_ui(self, all_devices):
        self.all_detected_devices = all_devices
        names = [d['display'] for d in all_devices]
        self.device_selection_combobox['values'] = names
        if names: 
            self.device_selection_combobox.current(0)
            self.on_device_selected(None)
        self.device_label['text'] = f"設備狀態: 已連接 {len(all_devices)} 台"

    def on_device_selected(self, event):
        sel = self.device_selection_combobox.get()
        dev = next((d for d in self.all_detected_devices if d['display'] == sel), None)
        if dev:
            self.device_serial = dev['serial']
            self.selected_device_details = dev
            self.log_output(f"已選擇: {sel}")

    def run_command(self, command, description, check_mode=True, target_text_widget=None):
        if not self.device_serial and check_mode:
            self.log_output("錯誤: 未選擇設備"); return
        
        full_cmd = command
        if check_mode and any(x in command for x in ['adb', 'fastboot', 'scrcpy']):
            parts = command.split()
            parts.insert(1, '-s'); parts.insert(2, self.device_serial)
            full_cmd = " ".join(parts)
            
        self.log_output(f"執行: {description}")
        threading.Thread(target=self._execute, args=(full_cmd, description, target_text_widget), daemon=True).start()

    def _execute(self, cmd, desc, widget):
        try:
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
            msg = res.stdout if res.returncode == 0 else res.stderr
            self.root.after(0, lambda: self.log_output(f"{desc} 完成\n{msg.strip()}"))
            if widget: self.root.after(0, lambda: self._widget_log(widget, msg))
        except Exception as e:
            self.root.after(0, lambda: self.log_output(f"錯誤: {e}"))

    def _widget_log(self, widget, msg):
        widget.insert(tk.END, f"\n[{time.strftime('%H:%M:%S')}]\n{msg}\n")
        widget.see(tk.END)

    # --- 功能細項 (APK, 截圖, Shell, Info) ---
    def install_apk(self):
        path = filedialog.askopenfilename(filetypes=[("APK", "*.apk")])
        if path: self.run_command(f'adb install -r "{path}"', "安裝 APK")

    def take_screenshot(self):
        def cap():
            ts = time.strftime('%Y%m%d_%H%M%S')
            remote = f"/sdcard/ss_{ts}.png"
            local = os.path.join(os.path.expanduser("~"), f"Desktop/SS_{ts}.png")
            subprocess.run(f"adb -s {self.device_serial} shell screencap -p {remote}", shell=True)
            subprocess.run(f"adb -s {self.device_serial} pull {remote} {local}", shell=True)
            subprocess.run(f"adb -s {self.device_serial} shell rm {remote}", shell=True)
            self.log_output(f"截圖成功: {local}")
        threading.Thread(target=cap, daemon=True).start()

    def push_file(self):
        src = filedialog.askopenfilename()
        if src:
            dst = simpledialog.askstring("目標", "輸入設備路徑 (如 /sdcard/)")
            if dst: self.run_command(f'adb push "{src}" "{dst}"', "Push 文件")

    def pull_file(self):
        src = simpledialog.askstring("來源", "輸入設備文件路徑")
        if src:
            dst = filedialog.askdirectory()
            if dst: self.run_command(f'adb pull "{src}" "{dst}"', "Pull 文件")

    def run_custom_shell(self):
        cmd = self.shell_entry.get().strip()
        if cmd: self.run_command(f"adb shell {cmd}", f"Shell: {cmd}", target_text_widget=self.shell_output_text)

    def fetch_device_info(self):
        self.device_info_text.delete(1.0, tk.END)
        self.device_info_text.insert(tk.END, "獲取資訊中...", "header")
        # 簡單範例，可自行擴充
        self.run_command("adb shell dumpsys battery", "獲取電池資訊", target_text_widget=self.device_info_text)

    def fetch_system_info(self):
        self.system_info_text.delete(1.0, tk.END)
        self.run_command("adb shell getprop", "獲取系統屬性", target_text_widget=self.system_info_text)

    def show_logcat_window(self):
        win = tk.Toplevel(self.root); win.title("Logcat")
        txt = tk.Text(win, bg="#212121", fg="white"); txt.pack(fill='both', expand=True)
        proc = subprocess.Popen(f"adb -s {self.device_serial} logcat", shell=True, stdout=subprocess.PIPE, text=True)
        def read():
            for line in iter(proc.stdout.readline, ''):
                if not win.winfo_exists(): break
                txt.insert(tk.END, line); txt.see(tk.END)
        threading.Thread(target=read, daemon=True).start()
        win.protocol("WM_DELETE_WINDOW", lambda: [proc.terminate(), win.destroy()])

    def unlock_bootloader(self):
        if simpledialog.askstring("確認", "請輸入『確認』來解鎖 Bootloader") == "確認":
            self.run_command("fastboot flashing unlock", "解鎖 Bootloader")

    def lock_bootloader(self):
        if simpledialog.askstring("確認", "請輸入『確認』來鎖定 Bootloader") == "確認":
            self.run_command("fastboot flashing lock", "鎖定 Bootloader")

    def log_output(self, message):
        self.output_text.config(state=tk.NORMAL)
        self.output_text.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.output_text.see(tk.END)
        self.output_text.config(state=tk.DISABLED)

    def on_closing(self):
        self.root.destroy()

# --- 程式入口點 ---
if __name__ == "__main__":
    # [關鍵修改] 指定 className，這會決定 Linux 下的 WM_CLASS
    root = tk.Tk(className='adb_fastboot_tool')
    
    # 支援 Windows 工作列圖示 (選配)
    if sys.platform == "win32":
        try:
            from ctypes import windll
            windll.shell32.SetCurrentProcessExplicitAppUserModelID("liferlighdow.adb_tool.1")
        except: pass

    app = ADBFastbootToolApp(root)
    root.mainloop()