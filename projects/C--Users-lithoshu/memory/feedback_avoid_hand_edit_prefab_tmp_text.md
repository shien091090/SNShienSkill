---
name: feedback-avoid-hand-edit-prefab-tmp-text
description: 直接用文字編輯工具改 Unity prefab YAML 裡的 TextMeshProUGUI m_text 欄位，可能觸發 Unity 重新載入時對整份 prefab 做 TMP 子網格(TMP SubMeshUI)重建，造成大量無關 GameObject 被刪除/新增，diff 異常龐大
metadata: 
  node_type: memory
  type: feedback
  originSessionId: b6f2efea-627f-42c6-b58d-a72ca12f2c44
  modified: 2026-08-05T06:53:13.813Z
---

在 `D:\Git\808_Lobby_6000\Slot_Lobby` 修 LOBBYTW-4990 時，因為 Unity MCP 的 `manage_prefabs modify_contents` 無法可靠地設定內部物件引用欄位（headless 模式下 instanceID 每次呼叫都不同，無法跨呼叫穩定引用同一份 prefab 內的其他物件），改用 Edit 工具直接修改 prefab YAML 文字（清空一個 `TextMeshProUGUI` 元件的 `m_text` 寫死值，並手動加入新的欄位引用行），結果 Unity 重新整理/重新載入該 prefab 後，diff 從預期的兩行小改動暴增到 **158,729 行**，其中 246 個 GameObject 被刪除、223 個被新增——高度懷疑是文字被外部修改觸發 TMP 系統對整份 prefab 的多圖集子網格(`TMP SubMeshUI`)重新生成，導致大量物件內部 ID 重新分配。

**Why：** 使用者發現 commit 後的 diff 異常巨大，要求先停下不繼續動這個 prefab，改由使用者自己在 Unity Editor 裡處理（用 Inspector 手動拖拉欄位引用、直接在 Editor 內清空文字），避免透過外部文字編輯觸發非預期的結構性重建。

**How to apply：**
- 需要修改 prefab 裡 `TextMeshProUGUI`（或其他容易觸發 Unity 內部重建機制的元件，如有 SubMesh/Atlas 概念的元件）的**文字內容**時，優先用 Unity MCP 的 `manage_gameobject`/`manage_components` 等在真正開啟的 scene/prefab stage 中操作，或提醒使用者在 Editor Inspector 手動修改，**不要**直接用文字編輯工具改 prefab YAML 裡的 `m_text` 等 TMP 相關欄位
- 若需要新增/修改 prefab 裡「指向同一份 prefab內其他物件」的欄位引用（例如 SerializeField 存另一個子物件的元件），`manage_prefabs modify_contents` 的 `instanceID` 參數在 headless 模式下每次呼叫產生的 ID 不穩定、無法跨呼叫使用；退而求其次直接編輯 YAML 文字加入 `{fileID: ...}` 引用行本身是可行的（因為 fileID 是該 prefab 檔案內穩定的序列化身份），但風險在於這類編輯完成後 Unity 重新載入該檔案時，仍可能因為檔案裡其他部分（尤其是 TMP 文字）被同一次編輯連動修改而觸發非預期的重新序列化
- 修改後務必比對 `git diff --stat` 的變動規模是否合理（一個小改動理論上只會是個位數行差異），若發現變動量遠超預期，要主動停下告知使用者，而不是逕自認為「測試過了、console沒錯誤」就沒事直接送出
- 相關教訓見 [[feedback_batch_compile_checks]]（同樣是「等真的需要才驗證，不要每步都做」的反向提醒：這裡是「做完更動要主動檢查影響範圍，不要因為表面驗證通過就掉以輕心」）
