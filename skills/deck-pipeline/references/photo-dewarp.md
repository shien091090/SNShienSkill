# 照片轉正: EXIF 與透視校正

`@photo` 標籤的素材在 build 前要過兩關: **EXIF 轉向**與**透視校正**。兩者都是會場拍講座投影片時的常態問題。

## 1. EXIF 轉向 (自動)

手機直拍的照片常帶 `EXIF orientation` tag — 檔案存成橫式 4032x3024 再附一個「請轉 90 度」的標記。**PowerPoint 不吃這個標記**, 圖會貼成轉向的。

`build_pptx.py` 的 `validate()` 會擋下來並提示。修法:

```python
from PIL import Image, ImageOps
import io as _io

with Image.open(f) as im:
    if im.getexif().get(274) in (None, 1):
        pass                      # 已經是正的
    else:
        fixed = ImageOps.exif_transpose(im)
        ex = fixed.getexif(); ex.pop(274, None)
        buf = _io.BytesIO()
        fixed.save(buf, "JPEG", quality=95, exif=ex.tobytes(), optimize=True)
data = buf.getvalue()
assert len(data) > 100_000        # 轉檔結果異常小就是出事了
open(f, "wb").write(data)
```

⚠️ **一定要先寫進記憶體緩衝再覆蓋原檔。** 直接 `im.save(f, ...)` 覆蓋時, 若 save 中途拋錯 (例如對非 JPEG 來源用 `subsampling="keep"`), PIL 已經先清空了目標檔, 原圖就變成 0 bytes。這次實際踩過, 靠 git 才救回來 — 這也是**素材一進資料夾就該進版控**的理由之一。

## 2. 透視校正 (半自動)

會場照片的簡報畫面都是斜的。目標是把畫面四角拉成正矩形。

### 自動偵測不可靠, 不要浪費時間

實測四張典型會場照片, 兩種主流做法全都失敗:

| 做法 | 結果 |
|---|---|
| Otsu 二值化 + 找最大四邊形輪廓 | 1 張完全找不到四邊形, 2 張抓到「投影幕 + 溢出亮區」而不是畫面本身, 1 張勉強 |
| Canny + HoughLinesP 找四條主邊求交點 | 1 張四角退化成兩點, 2 張抓到幾乎整張照片 |

原因是同一個: 投影畫面與投影幕、與牆面之間的**亮度邊界不夠乾淨**。側面環境光、畫面本身偏亮偏白、投影幕邊框反光, 對傳統 CV 都是雜訊。

### 可靠做法: AI 當那個人眼

1. **產帶網格的預覽圖** — 原圖疊 10% 格線與刻度, 存成 `_校正預覽/預覽_<檔名>.jpg`
2. **AI 自己讀預覽圖**, 判斷簡報畫面四角的百分比座標 (不是叫使用者讀座標報給你 — 你看得懂圖, 自己讀)
3. **`getPerspectiveTransform` + `warpPerspective`** 校正, 輸出到 `_校正預覽/正_<檔名>.jpg`
4. **AI 再看一次校正結果**, 邊緣殘留暗邊就把該邊往內縮 0.5~1%, 重跑
5. 使用者確認後才覆蓋原檔, 並刪掉 `_校正預覽/`

```python
import cv2, numpy as np

def warp_pct(src_file, corners_pct, out_file):
    """corners_pct: [(TL),(TR),(BR),(BL)] 各為 (x%, y%)"""
    img = cv2.imdecode(np.fromfile(str(src_file), np.uint8), cv2.IMREAD_COLOR)
    h, w = img.shape[:2]
    src = np.array([[x/100*w, y/100*h] for x, y in corners_pct], "float32")
    tl, tr, br, bl = src
    W = int(max(np.linalg.norm(tr-tl), np.linalg.norm(br-bl)))
    H = int(max(np.linalg.norm(bl-tl), np.linalg.norm(br-tr)))
    dst = np.array([[0,0],[W-1,0],[W-1,H-1],[0,H-1]], "float32")
    out = cv2.warpPerspective(img, cv2.getPerspectiveTransform(src, dst), (W, H))
    cv2.imencode(".jpg", out, [cv2.IMWRITE_JPEG_QUALITY, 94])[1].tofile(str(out_file))
```

產預覽圖的格線 (原圖尺寸大, 線寬與字級要按比例放大, 否則縮圖後看不見):

```python
for i in range(1, 10):
    x, y = int(w*i/10), int(h*i/10)
    cv2.line(prev, (x,0), (x,h), (0,220,255), 3)
    cv2.line(prev, (0,y), (w,y), (0,220,255), 3)
    cv2.putText(prev, str(i*10), (x+8, 70), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0,220,255), 5)
    cv2.putText(prev, str(i*10), (14, y-14), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0,220,255), 5)
```

**中文路徑**要用 `cv2.imdecode(np.fromfile(...))` / `cv2.imencode(...).tofile(...)`, `cv2.imread` / `imwrite` 吃不了。

### 讀角點的幾個判斷

- **包含 macOS / Windows 選單列**。它是畫面的一部分, 而且是判斷上邊界最好用的參考線 — 那條深色橫帶的傾斜度就是透視的傾斜度
- **左右邊界超出照片範圍時就用 0 或 100**。這次有兩張照片的畫面左緣根本沒拍進去, 損失 2~3%, 接受
- **不強制 16:9**。讀角點必然有誤差, 這次四張輸出比例 1.42~1.81。硬拉成 16:9 會讓內容變形, 不如留著

## 3. 現成工具 (使用者自己動手更快時)

- **Microsoft Lens / Adobe Scan** (手機, 免費) — 可從相簿匯入既有照片, 自動抓四角 + 手動拖曳修正。模型是專門為這個場景訓練的, **比自己寫的準很多, 最推薦**
- **GIMP** 的透視變換 (免費桌面) 或 Photoshop 的透視裁切
- GitHub `DocAligner` — 深度學習版的文件四角偵測, 準度高但要裝 PyTorch, 為了幾張圖不值得

## 4. 相依

```
py -3 -m pip install opencv-python-headless
```

**不在 git 裡, 換機器要重裝。** 只有處理 `@photo` 素材時才需要, 其他階段用不到。
