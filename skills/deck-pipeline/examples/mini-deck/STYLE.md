# mini-deck 版型

## 人讀描述

白底深灰字, 藍色強調。六種版型:
- title: 大標居中偏上, 副標在下
- section: 章節名置中
- text: 標題在上, 條列佔中間大區
- image: 標題在上, 圖佔中間, 底部一行註解
- image-text: 左圖右文
- compare: 標題在上, 左右兩欄

## 腳本設定

```yaml
slide: {w: 13.333, h: 7.5}
theme:
  bg: "#FFFFFF"
  fg: "#1F2937"
  accent: "#2563EB"
  font_title: "Noto Sans TC"
  font_body: "Noto Sans TC"
layouts:
  title:
    - {role: title,    box: [1.0, 2.4, 11.3, 1.4], size: 40, bold: true}
    - {role: subtitle, box: [1.0, 4.0, 11.3, 1.0], size: 22}
  section:
    - {role: title,    box: [1.0, 3.0, 11.3, 1.4], size: 36, bold: true, color: "#2563EB"}
  text:
    - {role: title,    box: [0.8, 0.6, 11.7, 1.2], size: 32, bold: true}
    - {role: body,     box: [0.8, 2.2, 11.7, 4.5], size: 20}
  image:
    - {role: title,    box: [0.8, 0.5, 11.7, 1.0], size: 28, bold: true}
    - {role: image,    box: [0.8, 1.8, 11.7, 4.6]}
    - {role: body,     box: [0.8, 6.6, 11.7, 0.6], size: 16}
  image-text:
    - {role: title,    box: [0.8, 0.5, 11.7, 1.0], size: 28, bold: true}
    - {role: image,    box: [0.8, 1.8, 6.0, 4.8]}
    - {role: body,     box: [7.2, 1.8, 5.3, 4.8], size: 20}
  compare:
    - {role: title,    box: [0.8, 0.5, 11.7, 1.0], size: 28, bold: true}
    - {role: left,     box: [0.8, 1.8, 5.6, 4.8], size: 20}
    - {role: right,    box: [6.9, 1.8, 5.6, 4.8], size: 20}
```
