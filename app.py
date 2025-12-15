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
* **硬體/服務狀態 (dumpsys)：** 獲取詳細的硬體和服務狀態，包括：
    * Wi-Fi 連接狀態
    * 藍牙服務狀態
    * 電池電量、溫度與充電狀態
    * 螢幕/顯示狀態
    * 定位服務提供者
    * 內存使用概況

### 4. ADB Shell Console

* 提供獨立的分頁和輸出區域，供使用者輸入並執行自定義的 `adb shell` 命令。

### 5. Fastboot 核心功能 (Fastboot 模式)

* **高風險操作確認：** Fastboot 命令執行前強制要求使用者進行文字確認，以防止誤操作。
* **Bootloader 控制：**
    * 執行 **Fastboot 解鎖** (`fastboot flashing unlock`)。
    * 執行 **Fastboot 鎖定** (`fastboot flashing lock`)。

---

## 獨立製作聲明

本專案的所有功能、程式碼和設計，皆由 **Lifer_Lighdow** 獨立製作與完成。

本文件將作為專案的起始說明，供使用者參考。

**版本:** v1.0
**日期:** 2025年12月
"""

# --- 核心應用程式類別 ---
class ADBFastbootToolApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ADB/Fastboot GUI - 完整硬體資訊版")
        self.root.geometry("900x650") 
        
        # 設置UI風格
        self.style = ttk.Style()
        self.style.theme_use('clam') 

        # 狀態變數
        self.logcat_process = None
        self.device_serial = None # 存儲當前選中的設備序列號
        self.selected_device_details = None # 存儲當前選中設備的完整資訊
        self.all_detected_devices = [] # 存儲所有偵測到的設備詳細資訊
        self.adb_server_running = True
        
        # UI 元素初始化
        self.create_widgets()
        
        # 初始設備檢查
        self.check_device_status()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    # --- 界面創建 ---
    def create_widgets(self):
        # 1. 頂部狀態/控制區域
        status_frame = ttk.Frame(self.root, padding="10")
        status_frame.pack(fill='x')

        self.device_label = ttk.Label(status_frame, text="設備狀態: 未知", font=('Inter', 10, 'bold'))
        self.device_label.pack(side=tk.LEFT, padx=5)

        ttk.Button(status_frame, text="重新整理設備", command=self.check_device_status).pack(side=tk.LEFT, padx=15)
        
        # 設備選擇下拉選單
        ttk.Label(status_frame, text="選擇設備:", font=('Inter', 10)).pack(side=tk.LEFT, padx=(30, 5))
        self.device_selection_combobox = ttk.Combobox(status_frame, state="readonly", width=35)
        self.device_selection_combobox.pack(side=tk.LEFT, padx=5)
        self.device_selection_combobox.bind("<<ComboboxSelected>>", self.on_device_selected)

        self.adb_server_button = ttk.Button(status_frame, text="停止 ADB Server", command=self.toggle_adb_server)
        self.adb_server_button.pack(side=tk.RIGHT, padx=5)
        
        # 2. 功能區 (使用 Notebook 區分功能組)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill='both', padx=10, pady=5)
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        
        # --- 頁籤初始化 ---
        
        # 1. README 頁籤 (新加入)
        readme_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(readme_frame, text='README')
        self.create_readme_widgets(readme_frame)

        # 2. 原始頁籤
        adb_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(adb_frame, text='ADB 設備操作')
        self.create_adb_widgets(adb_frame)

        fastboot_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(fastboot_frame, text='Fastboot 核心功能')
        self.create_fastboot_widgets(fastboot_frame)

        shell_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(shell_frame, text='ADB Shell Console')
        self.create_adb_shell_widgets(shell_frame)
        
        device_info_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(device_info_frame, text='設備/硬體資訊')
        self.create_device_info_widgets(device_info_frame)
        
        system_info_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(system_info_frame, text='系統屬性 (getprop)')
        self.create_system_info_widgets(system_info_frame)


        # 3. 輸出日誌區域
        output_frame = ttk.Frame(self.root, padding="10")
        output_frame.pack(fill='x')
        
        ttk.Label(output_frame, text="操作日誌輸出:", font=('Inter', 10)).pack(anchor='w')
        
        scrollbar = ttk.Scrollbar(output_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.output_text = tk.Text(
            output_frame, 
            height=10, 
            wrap='word', 
            state=tk.DISABLED, 
            yscrollcommand=scrollbar.set, 
            font=('Courier', 9)
        )
        self.output_text.config(spacing3=4) 
        self.output_text.pack(fill='x', expand=True)
        scrollbar.config(command=self.output_text.yview)

    def on_tab_changed(self, event):
        """處理頁籤切換事件，用於自動載入資訊頁面"""
        selected_tab = self.notebook.tab(self.notebook.select(), "text")
        
        if selected_tab == '設備/硬體資訊':
            self.fetch_device_info() 
        elif selected_tab == '系統屬性 (getprop)':
            self.fetch_system_info() 

    # --- 新增 README 頁籤定義 ---
    def create_readme_widgets(self, readme_frame):
        """README 說明頁籤"""
        readme_frame.columnconfigure(0, weight=1)
        readme_frame.rowconfigure(0, weight=1)

        scrollbar = ttk.Scrollbar(readme_frame)
        scrollbar.grid(row=0, column=1, sticky='ns')

        readme_text = tk.Text(
            readme_frame,
            wrap='word',
            yscrollcommand=scrollbar.set,
            font=('Inter', 11),
            background='#f8f8f8'
        )
        readme_text.grid(row=0, column=0, sticky='nsew')
        scrollbar.config(command=readme_text.yview)

        # 設置 Tag 樣式
        readme_text.tag_config('h1', font=('Inter', 18, 'bold'), foreground='#007bff')
        readme_text.tag_config('h2', font=('Inter', 14, 'bold'), foreground='#28a745')
        readme_text.tag_config('h3', font=('Inter', 12, 'bold'), foreground='#6c757d')
        readme_text.tag_config('hr', font=('Inter', 10), foreground='#aaa') 
        readme_text.tag_config('author', font=('Inter', 11, 'italic', 'bold'), foreground='#dc3545')
        
        # 插入並應用標籤
        self._insert_and_tag_readme(readme_text)

        readme_text.config(state=tk.DISABLED)

    def _insert_and_tag_readme(self, text_widget):
        """解析並插入 README 內容，同時應用格式標籤"""
        
        content = README_CONTENT.split('\n')
        
        for line in content:
            if line.startswith('# '):
                text_widget.insert(tk.END, line + '\n', 'h1')
            elif line.startswith('## '):
                text_widget.insert(tk.END, line + '\n', 'h2')
            elif line.startswith('### '):
                text_widget.insert(tk.END, line + '\n', 'h3')
            elif line.startswith('---'):
                text_widget.insert(tk.END, line + '\n', 'hr')
            elif line.strip().startswith('**Lifer_Lighdow**'):
                 # 專門標記作者名稱
                 parts = line.split('**Lifer_Lighdow**')
                 if len(parts) == 2:
                     text_widget.insert(tk.END, parts[0].replace('*', '').replace('_', ''))
                     text_widget.insert(tk.END, "Lifer_Lighdow", 'author')
                     text_widget.insert(tk.END, parts[1].replace('*', '').replace('_', '') + '\n')
                 else:
                     text_widget.insert(tk.END, line.replace('*', '').replace('_', '') + '\n')
            else:
                # 簡單處理列表項
                text_widget.insert(tk.END, line.replace('*', '').replace('_', '') + '\n')


    # --- 頁籤內容定義 (原有的 ADB/Fastboot/Shell/Info functions follow) ---

    def create_adb_widgets(self, adb_frame):
        adb_frame.columnconfigure(0, weight=1)
        adb_frame.columnconfigure(1, weight=1)

        row_idx = 0

        # A. 設備重啟與模式
        reboot_group = ttk.LabelFrame(adb_frame, text="設備重啟與模式", padding="10")
        reboot_group.grid(row=row_idx, column=0, columnspan=2, sticky='ew', pady=5, padx=5)
        reboot_group.columnconfigure(0, weight=1)
        reboot_group.columnconfigure(1, weight=1)
        reboot_group.columnconfigure(2, weight=1)
        reboot_group.columnconfigure(3, weight=1)

        ttk.Button(reboot_group, text="正常重啟", command=lambda: self.run_command("adb reboot", "正常重啟設備")).grid(row=0, column=0, sticky='ew', padx=5, pady=5)
        ttk.Button(reboot_group, text="重啟到 Recovery", command=lambda: self.run_command("adb reboot recovery", "重啟到 Recovery")).grid(row=0, column=1, sticky='ew', padx=5, pady=5)
        ttk.Button(reboot_group, text="重啟到 Bootloader", command=lambda: self.run_command("adb reboot bootloader", "重啟到 Bootloader")).grid(row=0, column=2, sticky='ew', padx=5, pady=5)
        ttk.Button(reboot_group, text="重啟到 EDL/Download", command=lambda: self.run_command("adb reboot edl", "重啟到 EDL (可能不支援)")).grid(row=0, column=3, sticky='ew', padx=5, pady=5)
        
        row_idx += 1

        # B. 文件與應用程式管理
        file_group = ttk.LabelFrame(adb_frame, text="文件與應用程式管理", padding="10")
        file_group.grid(row=row_idx, column=0, columnspan=2, sticky='ew', pady=5, padx=5)
        file_group.columnconfigure(0, weight=1)
        file_group.columnconfigure(1, weight=1)
        
        ttk.Button(file_group, text="1. 安裝 APK (adb install -r)", command=self.install_apk).grid(row=0, column=0, sticky='ew', padx=5, pady=5)
        ttk.Button(file_group, text="2. 設備螢幕截圖 (自動拉取)", command=self.take_screenshot).grid(row=0, column=1, sticky='ew', padx=5, pady=5)
        ttk.Button(file_group, text="3. 推送文件至設備 (Push)", command=self.push_file).grid(row=1, column=0, sticky='ew', padx=5, pady=5)
        ttk.Button(file_group, text="4. 從設備拉取文件 (Pull)", command=self.pull_file).grid(row=1, column=1, sticky='ew', padx=5, pady=5)
        
        row_idx += 1

        # C. 系統與調試
        debug_group = ttk.LabelFrame(adb_frame, text="系統與調試", padding="10")
        debug_group.grid(row=row_idx, column=0, columnspan=2, sticky='ew', pady=5, padx=5)
        debug_group.columnconfigure(0, weight=1)
        debug_group.columnconfigure(1, weight=1)

        ttk.Button(debug_group, text="5. 啟動 Scrcpy (外部依賴)", command=lambda: self.run_command("scrcpy", "啟動 Scrcpy 螢幕鏡像")).grid(row=0, column=0, sticky='ew', padx=5, pady=5)
        ttk.Button(debug_group, text="6. 顯示即時 Logcat (新視窗)", command=self.show_logcat_window).grid(row=0, column=1, sticky='ew', padx=5, pady=5)

        row_idx += 1

    def create_fastboot_widgets(self, fastboot_frame):
        fastboot_frame.columnconfigure(0, weight=1)
        
        warning_label = ttk.Label(fastboot_frame, 
                                  text="!!! 警告: Fastboot 功能具有高風險性，操作不當可能導致設備變磚。請謹慎操作。 !!!", 
                                  foreground='red', 
                                  wraplength=750,
                                  font=('Inter', 11, 'bold'))
        warning_label.pack(pady=10, fill='x')

        # 鎖定/解鎖 Bootloader
        bootloader_group = ttk.LabelFrame(fastboot_frame, text="Bootloader 鎖定/解鎖", padding="10")
        bootloader_group.pack(fill='x', padx=5, pady=5)
        bootloader_group.columnconfigure(0, weight=1)
        bootloader_group.columnconfigure(1, weight=1)
        
        ttk.Button(bootloader_group, text="解鎖 Bootloader (fastboot flashing unlock)", 
                   command=self.unlock_bootloader, 
                   style='Danger.TButton').grid(row=0, column=0, sticky='ew', padx=5, pady=5)
        
        ttk.Button(bootloader_group, text="鎖定 Bootloader (fastboot flashing lock)", 
                   command=self.lock_bootloader, 
                   style='Danger.TButton').grid(row=0, column=1, sticky='ew', padx=5, pady=5)

        # 樣式定義 (危險按鈕)
        self.style.configure('Danger.TButton', foreground='white', background='#dc3545', font=('Inter', 10, 'bold'))
        self.style.map('Danger.TButton', 
                       background=[('active', '#c82333'), ('!disabled', '#dc3545')],
                       foreground=[('active', 'white'), ('!disabled', 'white')])

    def create_adb_shell_widgets(self, shell_frame):
        """獨立的 ADB Shell Console 頁籤"""
        shell_frame.columnconfigure(0, weight=1)

        ttk.Label(shell_frame, text="請輸入要執行的 adb shell 命令 (例如: ls /system):", font=('Inter', 10)).grid(row=0, column=0, sticky='w', pady=(0, 5))
        
        # 輸入控制
        input_frame = ttk.Frame(shell_frame)
        input_frame.grid(row=1, column=0, sticky='ew', pady=(0, 10))
        input_frame.columnconfigure(0, weight=1)

        self.shell_entry = ttk.Entry(input_frame)
        self.shell_entry.grid(row=0, column=0, sticky='ew', padx=(0, 10))
        
        # 獨立的控制按鈕 (CTL)
        ttk.Button(input_frame, text="運行 Shell", command=self.run_custom_shell).grid(row=0, column=1, sticky='e')
        
        # 輸出區域 (獨立於主日誌)
        ttk.Label(shell_frame, text="Shell 輸出結果:", font=('Inter', 10)).grid(row=2, column=0, sticky='w', pady=(10, 5))

        shell_output_frame = ttk.Frame(shell_frame)
        shell_output_frame.grid(row=3, column=0, sticky='nsew')
        shell_output_frame.columnconfigure(0, weight=1)
        shell_output_frame.rowconfigure(0, weight=1)

        shell_scrollbar = ttk.Scrollbar(shell_output_frame)
        shell_scrollbar.grid(row=0, column=1, sticky='ns')

        self.shell_output_text = tk.Text(
            shell_output_frame, 
            wrap='none', 
            height=15, 
            yscrollcommand=shell_scrollbar.set, 
            font=('Courier', 9),
            background='#f0f0f0'
        )
        self.shell_output_text.grid(row=0, column=0, sticky='nsew')
        shell_scrollbar.config(command=self.shell_output_text.yview)


    def create_device_info_widgets(self, info_frame):
        """設備/硬體資訊頁籤：顯示選定設備的硬體與服務狀態"""
        info_frame.columnconfigure(0, weight=1)
        info_frame.rowconfigure(1, weight=1)
        
        control_frame = ttk.Frame(info_frame)
        control_frame.grid(row=0, column=0, sticky='ew', pady=5)
        # 更新標題以反映新的功能範圍 (Wi-Fi, 螢幕, 電池等)
        ttk.Label(control_frame, text="選定設備的硬體與服務狀態 (ADB 模式):", font=('Inter', 10, 'bold')).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="獲取詳細硬體資訊", command=self.fetch_device_info).pack(side=tk.RIGHT)

        scrollbar = ttk.Scrollbar(info_frame)
        scrollbar.grid(row=1, column=1, sticky='ns')

        self.device_info_text = tk.Text(
            info_frame,
            wrap='word',
            yscrollcommand=scrollbar.set,
            font=('Courier', 10)
        )
        self.device_info_text.grid(row=1, column=0, sticky='nsew')
        scrollbar.config(command=self.device_info_text.yview)
        
        self.device_info_text.tag_config("header", foreground="#007bff", font=('Inter', 11, 'bold'))
        self.device_info_text.tag_config("title", foreground="green", font=('Courier', 10, 'bold'))
        self.device_info_text.tag_config("unknown", foreground="red")


    def create_system_info_widgets(self, sys_frame):
        """系統屬性頁籤：顯示選中設備的系統屬性 (ro.* getprop)"""
        sys_frame.columnconfigure(0, weight=1)
        sys_frame.rowconfigure(1, weight=1)

        control_frame = ttk.Frame(sys_frame)
        control_frame.grid(row=0, column=0, sticky='ew', pady=5)
        # 更新標題以反映這是 getprop 屬性
        ttk.Label(control_frame, text="選定設備的系統屬性 (ro.* getprop):", font=('Inter', 10, 'bold')).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="獲取系統屬性", command=self.fetch_system_info).pack(side=tk.RIGHT)

        scrollbar = ttk.Scrollbar(sys_frame)
        scrollbar.grid(row=1, column=1, sticky='ns')

        self.system_info_text = tk.Text(
            sys_frame,
            wrap='word',
            yscrollcommand=scrollbar.set,
            font=('Courier', 10)
        )
        self.system_info_text.grid(row=1, column=0, sticky='nsew')
        scrollbar.config(command=self.system_info_text.yview)
        
        self.system_info_text.tag_config("header", foreground="#343a40", font=('Inter', 12, 'bold'))
        self.system_info_text.tag_config("title", foreground="#007bff", font=('Inter', 10, 'bold'))


    # --- 修正後的 ADB Server 開關 ---
    def toggle_adb_server(self):
        """
        處理 ADB 伺服器的啟動和停止邏輯。
        """
        if self.adb_server_running:
            # 嘗試停止 ADB 伺服器
            self.run_command("adb kill-server", "關閉 ADB 伺服器", check_mode=False)
            self.adb_server_running = False
            self.adb_server_button['text'] = "啟動 ADB Server"
            self.device_label['text'] = "設備狀態: ADB Server 已停止"
            self.device_selection_combobox.set("未偵測到任何設備")
            self.device_selection_combobox['values'] = []
            self.device_serial = None
            self.selected_device_details = None # 清除詳細資訊
            self.all_detected_devices = []
        else:
            # 嘗試啟動 ADB 伺服器
            self.run_command("adb start-server", "啟動 ADB 伺服器", check_mode=False)
            self.adb_server_running = True
            # 重新檢查設備狀態
            self.check_device_status() 


    # --- 設備狀態與選擇 ---

    def check_device_status(self):
        """檢查並更新 ADB/Fastboot 設備連接狀態"""
        
        def check():
            # 1. 檢查 ADB 設備
            adb_result = subprocess.run('adb devices', shell=True, capture_output=True, text=True, encoding='utf-8')
            
            # 過濾掉 'list of devices attached' 和 'daemon' 相關的行
            adb_entries = [line.split() for line in adb_result.stdout.strip().split('\n') 
                           if line and len(line.split()) >= 2 and not line.startswith('*') and not line.startswith('List')]
            
            all_devices = []
            
            for entry in adb_entries:
                serial = entry[0]
                status = entry[1] if len(entry) > 1 else "device"
                
                if status == 'device':
                    display_name = f"ADB: {serial} (已連接)"
                    all_devices.append({'serial': serial, 'mode': 'ADB', 'status': status, 'display': display_name, 'level': '活躍/連線中'})
                elif status == 'unauthorized':
                    display_name = f"ADB: {serial} (未授權)"
                    all_devices.append({'serial': serial, 'mode': 'ADB', 'status': status, 'display': display_name, 'level': '需授權/未連線'})
                else: 
                    display_name = f"ADB: {serial} ({status})"
                    all_devices.append({'serial': serial, 'mode': 'ADB', 'status': status, 'display': display_name, 'level': '離線/不穩定'})
            
            # 2. 檢查 Fastboot 設備
            fastboot_result = subprocess.run('fastboot devices', shell=True, capture_output=True, text=True, encoding='utf-8')
            fastboot_entries = [line.split() for line in fastboot_result.stdout.strip().split('\n') if line and len(line.split()) >= 1]
            
            for entry in fastboot_entries:
                serial = entry[0]
                display_name = f"Fastboot: {serial} (已連接)"
                all_devices.append({'serial': serial, 'mode': 'Fastboot', 'status': 'fastboot', 'display': display_name, 'level': 'Bootloader/高權限'})

            adb_count = len([d for d in all_devices if d['mode'] == 'ADB'])
            fastboot_count = len([d for d in all_devices if d['mode'] == 'Fastboot'])
            
            self.all_detected_devices = all_devices 
            
            self.root.after(0, lambda: self._update_device_ui(all_devices, adb_count, fastboot_count))

        thread = threading.Thread(target=check, daemon=True)
        thread.start()

    def _update_device_ui(self, all_devices, adb_count, fastboot_count):
        """在主執行緒中更新設備相關的 UI 元素"""
        
        display_names = [d['display'] for d in all_devices]
        self.device_selection_combobox['values'] = display_names
        
        # 嘗試重新選擇或清除選擇
        current_selection = self.device_selection_combobox.get()
        if display_names:
            if not current_selection or current_selection not in display_names:
                self.device_selection_combobox.current(0)
                self.on_device_selected(None) # 觸發選擇事件
            # 如果當前選擇有效，則保持 current_selection 和 self.device_serial 不變
            elif self.device_serial:
                # 重新確認 self.device_serial 仍然有效
                selected_device_details = next((d for d in all_devices if d['serial'] == self.device_serial), None)
                if selected_device_details:
                    # 更新下拉選單的顯示名稱，以防狀態改變
                    self.device_selection_combobox.set(selected_device_details['display'])
                    self.selected_device_details = selected_device_details # 確保詳細資訊是最新的
                else:
                    # 設備斷開，重新選擇第一個
                    self.device_selection_combobox.current(0)
                    self.on_device_selected(None)
        else:
            self.device_selection_combobox.set("未偵測到任何設備")
            self.device_serial = None
            self.selected_device_details = None
            
        # 更新整體狀態標籤
        total_count = adb_count + fastboot_count
        if total_count > 0:
            status_text = f"設備狀態: {total_count} 台設備已連接 (ADB: {adb_count}, Fastboot: {fastboot_count})"
            self.adb_server_running = True
            self.adb_server_button.config(text="停止 ADB Server", state=tk.NORMAL)
        else:
            status_text = "設備狀態: 未連接"
            self.adb_server_button.config(text="啟動 ADB Server", state=tk.NORMAL) 
            
        self.device_label.config(text=status_text)
        self.log_output(f"狀態檢查完成. {status_text}")
        if total_count > 0:
            self.log_output(f"偵測到設備: {', '.join(display_names)}")

    def on_device_selected(self, event):
        """處理設備選擇事件，更新 self.device_serial 和 self.selected_device_details"""
        selected_display = self.device_selection_combobox.get()
        # 查找匹配的設備詳細資訊
        selected_device = next((d for d in self.all_detected_devices if d['display'] == selected_display), None)

        if selected_device:
            self.device_serial = selected_device['serial']
            self.selected_device_details = selected_device # 存儲完整的設備資訊
            self.log_output(f"已選擇設備: {selected_display} (序列號: {self.device_serial}, 模式: {selected_device['mode']}, 狀態: {selected_device['status']})")
        else:
            self.device_serial = None
            self.selected_device_details = None
            self.log_output("未選擇有效設備或設備已離線。")


    # --- 設備/硬體資訊頁籤邏輯 (新定義) ---
    def fetch_device_info(self):
        """獲取選定 ADB 設備的詳細硬體/服務資訊 (Wi-Fi, 螢幕, 電池等)"""
        
        # 檢查是否選擇了設備且處於 ADB 模式
        is_adb_device = self.device_serial and self.device_selection_combobox.get().startswith('ADB:')
        
        self.device_info_text.config(state=tk.NORMAL)
        self.device_info_text.delete(1.0, tk.END)

        if not is_adb_device:
            self.device_info_text.insert(tk.END, "錯誤：請先在主頁面選擇一台處於 ADB 模式的設備。\n此頁籤僅顯示單一選定設備的詳細硬體狀態。", "unknown")
            self.device_info_text.config(state=tk.DISABLED)
            return
            
        # 檢查授權狀態
        if self.selected_device_details and self.selected_device_details.get('status') != 'device':
            status = self.selected_device_details.get('status', 'unauthorized')
            self.device_info_text.insert(tk.END, f"錯誤：設備狀態為 '{status}'，請檢查設備是否已授權 (USB 偵錯)。", "unknown")
            self.device_info_text.config(state=tk.DISABLED)
            return

        self.device_info_text.insert(tk.END, "--- 正在獲取設備硬體/服務資訊 (可能需要幾秒鐘)... ---\n", "header")
        self.device_info_text.config(state=tk.DISABLED)
        
        self.log_output(f"正在為設備 {self.device_serial} 獲取詳細硬體資訊...")

        threading.Thread(target=self._run_detailed_device_info_commands, daemon=True).start()

    def _run_detailed_device_info_commands(self):
        """在執行緒中運行 ADB shell dumpsys 命令並收集硬體資訊"""
        commands = [
            ("Wi-Fi 狀態", "dumpsys wifi | grep -E 'Wi-Fi is|mNetworkInfo|mWifiInfo'"),
            ("藍牙狀態", "dumpsys bluetooth_manager | grep 'State'"),
            ("定位 (GPS) 服務", "settings get secure location_mode; echo -n '提供者: '; settings get secure location_providers_allowed"),
            ("螢幕/顯示狀態", "dumpsys display | grep 'mScreenState'"),
            ("電池狀態/電量", "dumpsys battery | grep -E 'level:|status:|AC powered|USB powered|temperature:'"),
            ("鏡頭服務狀態", "service list | grep camera"), 
            ("內存使用概況", "dumpsys meminfo | head -n 10"),
        ]
        
        output = []
        for title, command_args in commands:
            # 修正 f-string SyntaxError：先進行替換，再構建 f-string。
            escaped_args = command_args.replace('"', '\\"') 
            full_command = f"adb -s {self.device_serial} shell \"{escaped_args}\""
            
            try:
                result = subprocess.run(
                    full_command, 
                    shell=True, 
                    capture_output=True, 
                    text=True, 
                    encoding='utf-8',
                    timeout=30
                )
                content = result.stdout.strip() if result.returncode == 0 else f"錯誤: {result.stderr.strip()}"
                output.append((title, content))
            except Exception as e:
                output.append((title, f"執行失敗: {e}"))

        self.root.after(0, lambda: self._display_detailed_device_info(output))

    def _display_detailed_device_info(self, data):
        """將獲取的詳細硬體資訊顯示在文本區域"""
        self.device_info_text.config(state=tk.NORMAL)
        self.device_info_text.delete(1.0, tk.END)
        self.device_info_text.insert(tk.END, f"=== 設備硬體/服務資訊報告 (設備: {self.device_serial}) ===\n", "header")
        self.device_info_text.insert(tk.END, "--------------------------------------------------\n\n")

        for title, content in data:
            self.device_info_text.insert(tk.END, f"【{title}】\n", "title")
            self.device_info_text.insert(tk.END, "原始輸出:\n")
            self.device_info_text.insert(tk.END, f"{content}\n\n")

        self.device_info_text.config(state=tk.DISABLED)

        # Log completion in the main log
        self.log_output(f"設備 {self.device_serial} 詳細資訊獲取完成。")


    # --- 系統屬性頁籤邏輯 (舊系統資訊) ---
    def fetch_system_info(self):
        """獲取選定 ADB 設備的系統屬性 (ro.* getprop)"""
        
        is_adb_device = self.device_serial and self.device_selection_combobox.get().startswith('ADB:')
        
        self.system_info_text.config(state=tk.NORMAL)
        self.system_info_text.delete(1.0, tk.END)

        if not is_adb_device:
            self.system_info_text.insert(tk.END, "錯誤：請先在主頁面選擇一台處於 ADB 模式的設備。\n此頁籤僅顯示單一選定設備的系統屬性。", "unknown")
            self.system_info_text.config(state=tk.DISABLED)
            return
            
        # 檢查授權狀態
        if self.selected_device_details and self.selected_device_details.get('status') != 'device':
            status = self.selected_device_details.get('status', 'unauthorized')
            self.system_info_text.insert(tk.END, f"錯誤：設備狀態為 '{status}'，請檢查設備是否已授權 (USB 偵錯)。", "unknown")
            self.system_info_text.config(state=tk.DISABLED)
            return

        self.system_info_text.insert(tk.END, "--- 正在獲取系統屬性 (這可能需要幾秒鐘)... ---\n", "header")
        self.system_info_text.config(state=tk.DISABLED)

        threading.Thread(target=self._run_system_info_commands, daemon=True).start()

    def _run_system_info_commands(self):
        """在執行緒中運行 ADB shell getprop 命令並收集資訊"""
        commands = [
            ("設備型號與品牌", "getprop ro.product.model; echo -n ' / '; getprop ro.product.brand"),
            ("Android 版本/API 等級", "getprop ro.build.version.release; echo -n ' / API: '; getprop ro.build.version.sdk"),
            ("內部版本號/指紋", "getprop ro.build.fingerprint"),
            ("CPU/平台資訊", "getprop ro.product.cpu.abi; echo -n ' / '; getprop ro.board.platform"),
            ("內核版本 (uname)", "uname -a"),
            ("儲存空間使用情況 (/data)", "df -h /data"),
            ("ADB 介面狀態", "getprop init.svc.adbd"),
        ]
        
        output = []
        for title, command_args in commands:
            # 這裡的命令是簡單的，不需要複雜轉義
            full_command = f"adb -s {self.device_serial} shell \"{command_args}\""
            try:
                result = subprocess.run(
                    full_command, 
                    shell=True, 
                    capture_output=True, 
                    text=True, 
                    encoding='utf-8',
                    timeout=45 
                )
                content = result.stdout.strip() if result.returncode == 0 else f"錯誤: {result.stderr.strip()}"
                output.append((title, content))
            except Exception as e:
                output.append((title, f"執行失敗: {e}"))

        self.root.after(0, lambda: self._display_system_info(output))

    def _display_system_info(self, data):
        """將獲取的系統屬性顯示在文本區域"""
        self.system_info_text.config(state=tk.NORMAL)
        self.system_info_text.delete(1.0, tk.END)
        self.system_info_text.insert(tk.END, f"=== 系統屬性報告 (設備: {self.device_serial}) ===\n\n", "header")

        for title, content in data:
            self.system_info_text.insert(tk.END, f"--------------------------------------------------\n")
            self.system_info_text.insert(tk.END, f"【{title}】\n", "title")
            self.system_info_text.insert(tk.END, f"--------------------------------------------------\n")
            self.system_info_text.insert(tk.END, f"{content}\n\n")

        self.system_info_text.config(state=tk.DISABLED)


    # --- ADB Shell 獨立功能 ---
    def run_custom_shell(self):
        """運行自定義 adb shell 命令 (在獨立頁面)"""
        is_adb_device = self.device_serial and self.device_selection_combobox.get().startswith('ADB:')
        if not is_adb_device:
            self.log_output(f"錯誤: 請先在下拉選單中選擇要操作的 ADB 設備。")
            self.log_to_shell_output(f"錯誤: 請先在主頁面選擇要操作的 ADB 設備。", self.shell_output_text)
            return
            
        command_args = self.shell_entry.get().strip()
        
        self.shell_output_text.config(state=tk.NORMAL)
        self.shell_output_text.delete(1.0, tk.END)
        self.shell_output_text.insert(tk.END, f"--- 準備執行: adb shell {command_args} ---\n", "header")
        self.shell_output_text.config(state=tk.DISABLED)

        if command_args:
            # 這裡只傳遞 "adb shell <args>"，具體的 -s 注入在 run_command 中處理
            command = f"adb shell {command_args}"
            description = f"運行自定義 Shell: {command_args}"
            self.run_command(command, description, target_text_widget=self.shell_output_text)
        else:
            self.log_output("請輸入要執行的 adb shell 命令。")

    def log_to_shell_output(self, message, text_widget):
        """將訊息輸出到指定的 Shell 輸出文本區域"""
        text_widget.config(state=tk.NORMAL)
        text_widget.insert(tk.END, f"\n[{time.strftime('%H:%M:%S')}] {message}\n")
        text_widget.see(tk.END)
        text_widget.config(state=tk.DISABLED)


    # --- 通用命令執行器 (非同步) ---
    def run_command_in_thread(self, command, description, target_text_widget=None):
        """在單獨的執行緒中運行命令以保持 GUI 響應"""
        thread = threading.Thread(target=self._execute_command, args=(command, description, target_text_widget), daemon=True)
        thread.start()

    def run_command(self, command, description, check_mode=True, target_text_widget=None):
        """主介面調用的命令啟動函數，處理設備序列號和模式檢查"""
        
        command_parts = command.split()
        tool = command_parts[0] 
        
        # 處理不需要設備序列號的特殊命令
        if not check_mode and ('start-server' in command or 'kill-server' in command):
            self.log_output(f"\n--- 正在執行: {description} ({command}) ---")
            self.run_command_in_thread(command, description, target_text_widget)
            return

        # 檢查設備選擇
        if not self.device_serial:
            self.log_output(f"錯誤: 請先在下拉選單中選擇要操作的設備。")
            if target_text_widget:
                self.log_to_shell_output(f"錯誤: 請先在主頁面選擇要操作的設備。", target_text_widget)
            return

        # 檢查模式匹配
        selected_device_display = self.device_selection_combobox.get()
        
        if tool == 'fastboot' and not selected_device_display.startswith('Fastboot:'):
            self.log_output(f"錯誤: Fastboot 命令只能在 Fastboot 模式的設備上執行。請選擇 Fastboot 設備。")
            return
        
        if tool == 'adb' and not selected_device_display.startswith('ADB:'):
             self.log_output(f"錯誤: ADB 命令只能在 ADB 模式的設備上執行。請選擇 ADB 設備。")
             return

        # 檢查 ADB 設備是否已授權 (ADB shell 必須是 'device' 狀態)
        if tool == 'adb' and self.selected_device_details and self.selected_device_details.get('status') != 'device':
            status = self.selected_device_details.get('status', 'unauthorized')
            self.log_output(f"錯誤: 設備 {self.device_serial} 狀態為 '{status}'，無法執行 ADB 命令。請檢查設備是否已授權 (USB 偵錯)。")
            if target_text_widget:
                self.log_to_shell_output(f"錯誤: 設備狀態為 '{status}'，無法執行 ADB Shell。", target_text_widget)
            return

        # 注入設備選擇 (-s <serial>)
        if tool in ['adb', 'fastboot', 'scrcpy']:
            command_parts.insert(1, '-s')
            command_parts.insert(2, self.device_serial)
            command = " ".join(command_parts)
        
        # 執行
        self.log_output(f"\n--- 正在執行: {description} (最終命令: {command}) ---")
        self.run_command_in_thread(command, description, target_text_widget)


    def _execute_command(self, command, description, target_text_widget):
        """實際執行 shell 命令的私有方法"""
        try:
            result = subprocess.run(
                command, 
                shell=True, 
                check=True, 
                capture_output=True, 
                text=True, 
                encoding='utf-8',
                timeout=300 
            )
            
            output_msg = f"命令執行成功: {description}"
            self.root.after(0, lambda: self.log_output(output_msg))
            if result.stdout:
                stdout_msg = result.stdout.strip()
                self.root.after(0, lambda: self.log_output(f"STDOUT:\n{stdout_msg}"))
                if target_text_widget:
                    # 使用 log_to_shell_output 處理獨立輸出
                    self.root.after(0, lambda: self.log_to_shell_output(f"STDOUT:\n{stdout_msg}", target_text_widget))
            
            if 'reboot' in command:
                 self.root.after(2000, self.check_device_status)

        except subprocess.CalledProcessError as e:
            error_msg = f"命令執行失敗: {description}\nSTDERR:\n{e.stderr.strip()}\n返回代碼: {e.returncode}"
            self.root.after(0, lambda: self.log_output(error_msg))
            if target_text_widget:
                self.root.after(0, lambda: self.log_to_shell_output(error_msg, target_text_widget))
        
        except subprocess.TimeoutExpired:
            timeout_msg = f"命令執行超時 (5分鐘): {description}"
            self.root.after(0, lambda: self.log_output(timeout_msg))
            if target_text_widget:
                self.root.after(0, lambda: self.log_to_shell_output(timeout_msg, target_text_widget))

        except FileNotFoundError:
            file_not_found_msg = f"錯誤: 找不到命令 '{command.split()[0]}'. 請確認相關工具已安裝且在 PATH 中."
            self.root.after(0, lambda: self.log_output(file_not_found_msg))
            if target_text_widget:
                self.root.after(0, lambda: self.log_to_shell_output(file_not_found_msg, target_text_widget))
        
        except Exception as e:
            unexpected_error_msg = f"發生意外錯誤: {e}"
            self.root.after(0, lambda: self.log_output(unexpected_error_msg))
            if target_text_widget:
                self.root.after(0, lambda: self.log_to_shell_output(unexpected_error_msg, target_text_widget))


    # --- ADB 文件與應用程式功能 ---

    def install_apk(self):
        """安裝 APK 檔案"""
        if not self.device_serial or not self.device_selection_combobox.get().startswith('ADB:'):
            messagebox.showerror("錯誤", "請先選擇一台處於 ADB 模式的設備。")
            return
        if self.selected_device_details and self.selected_device_details.get('status') != 'device':
            messagebox.showerror("錯誤", f"設備狀態為 '{self.selected_device_details.get('status')}'，請先在設備上授權 USB 偵錯。")
            return
            
        apk_path = filedialog.askopenfilename(title="選擇要安裝的 APK 檔案", filetypes=[("APK 檔案", "*.apk")])
        if apk_path:
            # 使用 -r 參數允許重新安裝
            command = f'adb install -r "{apk_path}"'
            self.run_command(command, f"安裝 APK: {os.path.basename(apk_path)}")

    def push_file(self):
        """推送本地文件到設備"""
        if not self.device_serial or not self.device_selection_combobox.get().startswith('ADB:'):
            messagebox.showerror("錯誤", "請先選擇一台處於 ADB 模式的設備。")
            return
        if self.selected_device_details and self.selected_device_details.get('status') != 'device':
            messagebox.showerror("錯誤", f"設備狀態為 '{self.selected_device_details.get('status')}'，請先在設備上授權 USB 偵錯。")
            return
            
        local_path = filedialog.askopenfilename(title="選擇要推送的本地文件")
        if local_path:
            remote_path = simpledialog.askstring("目標路徑", "請輸入設備上的目標路徑 (例如: /sdcard/temp/)", parent=self.root)
            if remote_path:
                command = f'adb push "{local_path}" "{remote_path}"'
                self.run_command(command, f"推送文件: {os.path.basename(local_path)} -> {remote_path}")

    def pull_file(self):
        """從設備拉取文件到本地"""
        if not self.device_serial or not self.device_selection_combobox.get().startswith('ADB:'):
            messagebox.showerror("錯誤", "請先選擇一台處於 ADB 模式的設備。")
            return
        if self.selected_device_details and self.selected_device_details.get('status') != 'device':
            messagebox.showerror("錯誤", f"設備狀態為 '{self.selected_device_details.get('status')}'，請先在設備上授權 USB 偵錯。")
            return

        remote_path = simpledialog.askstring("源路徑", "請輸入設備上的源文件路徑 (例如: /sdcard/file.txt)", parent=self.root)
        if remote_path:
            local_dir = filedialog.askdirectory(title="選擇本地保存目錄")
            if local_dir:
                command = f'adb pull "{remote_path}" "{local_dir}"'
                self.run_command(command, f"拉取文件: {remote_path} -> {local_dir}")


    def take_screenshot(self):
        """一鍵截圖 (screencap -> pull -> delete)"""
        
        if not self.device_serial or not self.device_selection_combobox.get().startswith('ADB:'):
            self.log_output("錯誤: 請先選擇一台處於 ADB 模式的設備。")
            return
        if self.selected_device_details and self.selected_device_details.get('status') != 'device':
            self.log_output(f"錯誤: 設備狀態為 '{self.selected_device_details.get('status')}'，請先在設備上授權 USB 偵錯。")
            return

        def capture():
            remote_tmp_path = "/sdcard/screenshot_tmp.png"
            # 嘗試使用用戶的桌面或當前工作目錄
            local_dir = os.path.join(os.path.expanduser("~"), "Desktop")
            if not os.path.exists(local_dir): local_dir = os.getcwd()
            filename = f"Screenshot_{time.strftime('%Y%m%d_%H%M%S')}.png"
            local_path = os.path.join(local_dir, filename)

            try:
                self.log_output("-> 步驟 1/3: 執行截圖...")
                # 這裡的命令是簡單的，不需要複雜轉義
                subprocess.run(f"adb -s {self.device_serial} shell screencap -p {remote_tmp_path}", shell=True, check=True, capture_output=True, text=True, encoding='utf-8')
                
                self.log_output(f"-> 步驟 2/3: 拉取文件至本地: {local_path}...")
                subprocess.run(f'adb -s {self.device_serial} pull "{remote_tmp_path}" "{local_path}"', shell=True, check=True, capture_output=True, text=True, encoding='utf-8')
                
                self.log_output("-> 步驟 3/3: 刪除設備上的暫存文件...")
                subprocess.run(f"adb -s {self.device_serial} shell rm {remote_tmp_path}", shell=True, check=True, capture_output=True, text=True, encoding='utf-8')
                
                self.root.after(0, lambda: self.log_output(f"!!! 截圖成功: 文件已保存到 {local_path} !!!"))
                
            except subprocess.CalledProcessError as e:
                self.root.after(0, lambda: self.log_output(f"截圖失敗. STDERR:\n{e.stderr.strip()}"))
            except Exception as e:
                self.root.after(0, lambda: self.log_output(f"截圖過程中發生錯誤: {e}"))
                
        self.log_output("\n--- 正在執行: 設備截圖 ---")
        thread = threading.Thread(target=capture, daemon=True)
        thread.start()


    # --- Logcat 視窗與讀取 ---
    def show_logcat_window(self):
        """在新視窗中顯示即時 Logcat 輸出"""
        if not self.device_serial or not self.device_selection_combobox.get().startswith('ADB:'):
            messagebox.showerror("錯誤", "請先選擇一台處於 ADB 模式的設備。")
            return
        if self.selected_device_details and self.selected_device_details.get('status') != 'device':
            messagebox.showerror("錯誤", f"設備狀態為 '{self.selected_device_details.get('status')}'，Logcat 無法運行。請先在設備上授權 USB 偵錯。")
            return
            
        if self.logcat_process and self.logcat_process.poll() is None:
            messagebox.showinfo("Logcat 正在運行", "Logcat 視窗已經開啟，請先關閉現有的 Logcat 視窗或進程。")
            return

        # 創建 Logcat 頂級視窗
        logcat_window = tk.Toplevel(self.root)
        logcat_window.title(f"即時 Logcat - 設備: {self.device_serial}")
        logcat_window.geometry("800x400")

        logcat_frame = ttk.Frame(logcat_window, padding="10")
        logcat_frame.pack(expand=True, fill='both')
        logcat_frame.columnconfigure(0, weight=1)
        logcat_frame.rowconfigure(0, weight=1)

        scrollbar = ttk.Scrollbar(logcat_frame)
        scrollbar.grid(row=0, column=1, sticky='ns')
        
        logcat_text = tk.Text(logcat_frame, wrap='none', yscrollcommand=scrollbar.set, font=('Courier', 9), background='#212121', foreground='#ffffff')
        logcat_text.grid(row=0, column=0, sticky='nsew')
        scrollbar.config(command=logcat_text.yview)

        # 啟動 Logcat 命令
        logcat_command = f'adb -s {self.device_serial} logcat'
        try:
            self.log_output(f"啟動 Logcat 命令: {logcat_command}")
            self.logcat_process = subprocess.Popen(
                logcat_command, 
                shell=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True, 
                encoding='utf-8',
                bufsize=1
            )

            # 啟動執行緒來讀取 Logcat 輸出
            threading.Thread(target=self.logcat_output_reader, args=(logcat_text,), daemon=True).start()
            
            # 視窗關閉時停止 Logcat 進程
            logcat_window.protocol("WM_DELETE_WINDOW", lambda: self.on_logcat_close(logcat_window))

        except Exception as e:
            messagebox.showerror("Logcat 錯誤", f"無法啟動 Logcat 進程: {e}")
            self.log_output(f"Logcat 啟動失敗: {e}")
            logcat_window.destroy()

    def logcat_output_reader(self, text_widget):
        """Logcat 輸出讀取執行緒"""
        try:
            for line in iter(self.logcat_process.stdout.readline, ''):
                if not self.logcat_process:
                    break
                self.root.after(0, lambda t=text_widget, l=line: self._append_logcat_line(t, l))
        except ValueError:
             # 當進程被終止時，stdout.readline 會拋出 ValueError
             pass
        finally:
            self.root.after(0, lambda: self.log_output("Logcat 讀取執行緒已停止。"))
            if self.logcat_process and self.logcat_process.poll() is None:
                self.logcat_process.terminate()

    def _append_logcat_line(self, text_widget, line):
        """在主執行緒中安全地更新 Logcat 文本區域"""
        text_widget.insert(tk.END, line)
        text_widget.see(tk.END)

    def on_logcat_close(self, window):
        """處理 Logcat 視窗關閉事件"""
        if self.logcat_process and self.logcat_process.poll() is None:
            self.logcat_process.terminate()
            self.logcat_process.wait()
            self.logcat_process = None
            self.log_output("Logcat 進程已停止。")
        window.destroy()


    # --- Fastboot 高風險功能 (強制確認邏輯) ---
    def fastboot_confirm_and_run(self, command, description):
        """執行 Fastboot 命令前的強制確認彈窗"""
        
        selected_device = self.device_selection_combobox.get()
        if not selected_device.startswith('Fastboot:'):
            messagebox.showerror("操作被阻止", "請先在下拉選單中選擇一台處於 Fastboot 模式的設備。")
            return

        confirmation_text = "我了解風險並確認"
        
        user_input = simpledialog.askstring(
            "Fastboot 高風險操作確認", 
            f"!!! 警告: 此操作具有高風險性 !!!\n\n執行此命令 ({description}) 前，請準確輸入以下文字：\n\n『{confirmation_text}』",
            parent=self.root
        )

        if user_input == confirmation_text:
            self.run_command(command, description)
        elif user_input is not None:
            messagebox.showerror("確認失敗", "輸入文字不符，操作已取消。")
            
    def unlock_bootloader(self):
        self.fastboot_confirm_and_run("fastboot flashing unlock", "解鎖 Bootloader (!!!清除數據!!!)")

    def lock_bootloader(self):
        self.fastboot_confirm_and_run("fastboot flashing lock", "鎖定 Bootloader (!!!高風險!!!)")


    # --- 輸出與清理 ---
    def log_output(self, message):
        """在主界面日誌區域輸出消息"""
        self.output_text.config(state=tk.NORMAL)
        self.output_text.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.output_text.see(tk.END)
        self.output_text.config(state=tk.DISABLED)

    def on_closing(self):
        """應用程式關閉時的清理工作"""
        if hasattr(self, 'logcat_process') and self.logcat_process and self.logcat_process.poll() is None:
            self.logcat_process.terminate()
        self.log_output("應用程式關閉。")
        self.root.destroy()


# --- 程式入口點 ---
if __name__ == "__main__":
    try:
        # 簡單檢查 adb 和 fastboot 是否在 PATH 中
        subprocess.run(['adb', '--version'], check=True, capture_output=True, text=True, timeout=5)
        subprocess.run(['fastboot', '--version'], check=True, capture_output=True, text=True, timeout=5)
    except FileNotFoundError:
        print("警告: 找不到 'adb' 或 'fastboot' 命令。請確保它們已安裝並在系統 PATH 中。", file=sys.stderr)
    except subprocess.TimeoutExpired:
        print("警告: adb/fastboot 檢查超時，可能在運行中。", file=sys.stderr)
        
    root = tk.Tk()
    app = ADBFastbootToolApp(root)
    root.mainloop()
