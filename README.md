# 📸 使用 Google Photos API 的用戶端註冊與設定教學

本文件說明如何在 Google Cloud Console 建立一個可以操作 **Google Photos API** 的 OAuth 用戶端憑證，並取得存取授權以呼叫相關 API。

---

## ✅ 前置條件

- Google 帳戶（Gmail）

---

## 🧭 步驟一：建立 Google Cloud 專案

1. 前往 [Google Cloud Console](https://console.cloud.google.com/)
2. 點選左上角的「專案選擇器」 → `建立專案`
3. 輸入專案名稱並點選「建立」

---

## 🔓 步驟二：啟用 Google Photos API

1. 在左側選單中點選「API 與服務」 → 「程式庫」
2. 搜尋 **Google Photos Library API**
3. 點擊該服務 → 點選「啟用」

---

## 🔐 步驟三：設定 OAuth 同意畫面

1. 左側選單選擇「API 與服務」 → 「OAuth 同意畫面」
2. 選擇「外部」應用類型（若應用公開）
3. 輸入：
   - 應用名稱（例如：My Photos App）
   - 支援電子郵件
   - 開發人員聯絡資訊
4. 儲存並繼續，其他欄位可先略過或視情況補充

---

## 🧾 步驟四：建立 OAuth 2.0 用戶端 ID

1. 左側選單 → 「認證」 → 點選「建立憑證」 → 選擇「OAuth 用戶端 ID」
2. 選擇應用程式類型（常見為「網頁應用程式」或「電腦應用程式」）
3. 輸入名稱，例如 `Google Photos OAuth Client`

5. 點選「建立」，系統會提供：
   - `Client ID`
   - `Client Secret`

---

## 📥 步驟五：下載 JSON 憑證

1. 在「認證」頁面，找到剛才建立的用戶端
2. 點選右側「下載」圖示 → 儲存 JSON 檔案（例如：`client_secret.json`）

請將此檔案保存於應用程式目錄，並 **切勿上傳至公開儲存庫！**

---

## 🔑 Google Photos API 權限範圍（Scopes）

在發出授權請求時，需指定所需範圍。以下是常用的 Google Photos 權限範圍：

```text
https://www.googleapis.com/auth/photoslibrary.readonly
https://www.googleapis.com/auth/photoslibrary.appendonly
https://www.googleapis.com/auth/photoslibrary.readonly.appcreateddata
https://www.googleapis.com/auth/photoslibrary.edit.appcreateddata

延伸閱讀
Google Photos API 官方文件
(https://developers.google.com/photos)
