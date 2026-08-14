---
name: reference-808-lobby-repo-structure
description: "D:\\Git\\808_Lobby_6000 本身就是主要git repo(remote lobbygroup/Lobby.git),Slot_Lobby子目錄沒有自己的.git,只有特定子目錄(ThirdParty/aiToolLib/各遊戲Scripts等)是真正的submodule"
metadata: 
  node_type: memory
  type: reference
  originSessionId: a495df67-c8b9-4ad1-98f3-c857a64a04ce
  modified: 2026-08-11T01:10:45.271Z
---

`D:\Git\808_Lobby_6000` 本身就是一個完整的 git repo（`git remote -v` 顯示 `origin https://git-game.yile808.com/lobbygroup/Lobby.git`），不是單純的資料夾容器。

**關鍵事實**：`Slot_Lobby` 子目錄底下**沒有自己的 `.git`**，所以在 `Slot_Lobby/` 或更深層路徑下執行的 `git status`/`git commit` 等指令，實際上都是 git 自動往上層走訪找到 `808_Lobby_6000/.git` 之後在那個 repo 上操作（只是顯示的檔案路徑會相對於 cwd 顯示）——這跟直接在 `808_Lobby_6000` 根目錄執行指令是**完全相同的 repo、相同的 commit**，不是兩個獨立的東西。

真正被登記為獨立 git submodule（在 `808_Lobby_6000/.gitmodules` 裡）的只有特定子目錄：
- `Slot_Lobby/Assets/ThirdParty`（簡寫 `3P`，develop branch）
- `aiToolLib`（develop branch）
- `Slot_Lobby/Assets/Scripts/Slot`、`Fishing`、`H5Scripts`、`TableGame`、`Mahjong`、`MonarchBlackjack`、`YileFishing`、`Fish3D`、`Slot2`、`PachiSlot`（各遊戲腳本）
- `Slot_Lobby/Assets/Plugins/Lobby/SourceGenerator`

**這代表**：`Tools/Math_Data/~Localization/*.xlsx`（字表來源檔）跟 `Slot_Lobby/Assets/...` 底下的程式碼異動，**其實是同一個 repo 裡的檔案**，可以一起 git add + commit（不需要像 submodule 那樣分開 commit 拿 SHA 再回填）。之前誤以為 `Slot_Lobby` 是獨立 repo，只是因為在該目錄下操作的指令碰巧也能正常運作（git 自動往上找 `.git`），沒有實際出錯，但概念上要修正。

**How to apply：** 之後若同時異動 `Tools/` 底下的字表檔跟 `Slot_Lobby/Assets/` 底下的程式碼（例如新增字表Key配合程式功能），可以直接一次 `git add` 兩邊的檔案再一起 commit，不需要當成跨 repo 操作處理。若要確認某個子目錄是否為獨立 submodule，用 `git submodule status` 或查 `808_Lobby_6000/.gitmodules` 最準確，不要用「該目錄底下有沒有 `.git` 資料夾」以外的方式猜測。
