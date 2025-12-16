專案說明文件 (README)
=

ADB/Fastboot GUI 主要功能
-

本專案是一個簡潔高效的 ADB/Fastboot 圖形化使用者介面工具，旨在協助使用者輕鬆執行 Android 設備的調試和系統操作，無需記憶複雜的命令。


1. 設備狀態與連線管理
---

即時狀態顯示： 自動偵測並顯示所有連接的 ADB (device/unauthorized) 和 Fastboot 設備。

設備選擇： 透過下拉選單精確選擇要操作的單一設備。

Server 控制： 一鍵啟動或停止 ADB Server 服務。

2. ADB 設備操作 (ADB 模式)
---

設備重啟： 支援正常重啟、重啟到 Recovery 模式、重啟到 Bootloader 模式。

文件管理： 安裝 APK： 選擇本地 APK 文件進行安裝 (支援覆蓋安裝 -r)。

推送 (Push)： 將本地文件傳輸至設備指定路徑。

拉取 (Pull)： 將設備文件拉取到本地目錄。

調試工具：

螢幕截圖： 一鍵截圖並自動拉取到本地目錄。

Logcat 顯示： 彈出新視窗，即時顯示 Logcat 輸出流。

螢幕鏡像： 啟動 Scrcpy（需要外部依賴）。

3. 設備資訊與診斷
---

系統屬性 (getprop)： 顯示設備型號、Android 版本、API 等級、CPU 資訊、內核版本等核心系統屬性。

硬體/服務狀態 (dumpsys)： 獲取詳細的硬體和服務狀態，包括：

Wi-Fi 連接狀態

藍牙服務狀態

電池電量、溫度與充電狀態

螢幕/顯示狀態

定位服務提供者

內存使用概況

4. ADB Shell Console
---

提供獨立的分頁和輸出區域，供使用者輸入並執行自定義的 adb shell 命令。

5. Fastboot 核心功能 (Fastboot 模式)
---

高風險操作確認： Fastboot 命令執行前強制要求使用者進行文字確認，以防止誤操作。

Bootloader 控制：

執行 Fastboot 解鎖 (fastboot flashing unlock)。

執行 Fastboot 鎖定 (fastboot flashing lock)。

獨立製作聲明
---

本專案的所有功能、程式碼和設計，皆由 ***Lifer_Lighdow*** 獨立製作與完成。

本文件將作為專案的起始說明，供使用者參考。

版本: v1.0
日期: 2025年12月
