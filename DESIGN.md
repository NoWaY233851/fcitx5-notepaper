# 便箋 Notepaper：設計說明

這份文件說明主題的設計意圖、設計 token、各元件的做法，以及 fcitx5 classic UI 的限制和對應的處理方式。安裝與使用方式請看 [README.md](README.md)。

---

## 1. 設計意圖

候選窗是一張放在紙上的小便條：暖白底、細邊框，只有一個陶土色作點綴。

輸入法一天要看幾千次，所以這個主題刻意做到「低刺激」：

- **安靜**：沒有漸層、沒有材質、沒有模糊、沒有動畫，陰影只淡到剛好讓便條浮在底下內容上。
- **單一點綴**：陶土色在整個主題中只出現在一個地方，就是「目前選中的候選字」的序號位置。其他地方（選單、箭頭、邊框）一律不用陶土色。
- **用字體分層次，不用顏色**：候選字用明體，序號、拼音、註解用無襯線體，讓閱讀的焦點自然落在漢字上。
- **淺色、深色是同一張紙**：深色版不是反色，是「同一張便條在暗處」，保留相同的溫度和層次。

### 範圍

- 只支援 fcitx5 的 classic UI，不做鼠鬚管（Squirrel）、小狼毫（Weasel）、ibus 的版本。
- 只做橫排候選。
- 不做背景模糊（只有 KDE 支援）。
- 不修改 RIME 輸入方案本身（例如每頁候選數、序號樣式）。

---

## 2. fcitx5 classic UI 的限制與對策

以下根據 fcitx5 5.1.x 的 `src/ui/classic/` 原始碼整理。

| 限制 | 說明 | 對策 |
|---|---|---|
| **5.1.18 以前不能單獨設定序號、註解的顏色** | `CandidateLabelColor`、`HighlightCandidateLabelColor`、`CandidateCommentColor` 等鍵要到 5.1.18 才有。更早的版本裡，序號、候選字、註解都共用 `NormalColor`，選中時都共用 `HighlightCandidateColor` | 在選中底上疊一條陶土色短線，代替陶土色序號（§5.3）。升級到 5.1.18 以上後，可以改成真正的陶土色序號（§8） |
| **沒有圖片就沒有圓角** | `Image` 留空時只會畫直角矩形加邊框 | 面板和選中底都用 SVG 圖片，以九宮格（`Margin`）拉伸 |
| **字體是全域設定，不屬於主題** | 字體在 `classicui.conf` 的 `Font`，只能設一個，主題的 theme.conf 管不到 | 產生一個 fontconfig 別名字族 `Notepaper`：先用 Fira Sans，缺字再用 Noto Serif CJK TC Medium，並設定 `Font="Notepaper 11"`。數字和拉丁字母會用 Fira Sans，漢字會用明體。用別名而不是 `Fira Sans,Noto Serif CJK TC` 這種字族清單，是因為字族清單在 fcitx5 裡不一定會退到第二個字族，而且別名在設定介面裡只是一個名字，比較不容易被改壞。這個別名只影響指名要 `Notepaper` 的程式 |
| **fcitx5 只在啟動時讀一次 fontconfig** | 新增或修改字型別名之後，執行中的 fcitx5 看不到，會默默退回預設字型 | `install.sh` 比較別名檔和 fcitx5 程序的時間，別名比較新就重啟 fcitx5，否則只重新載入 classic UI |
| **`fcitx5-remote -r` 不會重新載入 classic UI** | 改了 `classicui.conf` 之後主題不會變 | 改用 DBus 的 `Controller1.ReloadAddonConfig classicui` |
| **系統強調色可能蓋掉配色** | `UseAccentColor` 預設為 True，主題裡列在 `AccentColorField` 的欄位會被換成系統強調色 | 主題完全不宣告 `[AccentColorField]`，陶土色就不會被取代。面板和選中底本來就是固定的 SVG，也不受強調色影響 |
| **程式自己畫的候選窗不認深色設定** | 在沒有 `zwp_input_panel_v1` 的 Wayland 桌面（例如 COSMIC）上，透過 fcitx5-gtk / fcitx5-qt 輸入的程式會在程式內自己畫候選窗。它們只讀 `Theme=`，不讀 `DarkTheme` / `UseDarkTheme` | 用背景服務在系統切換深淺色時改寫 `Theme=`（§6） |
| **圖片以原尺寸點陣化** | SVG 會以原始像素尺寸載入，縮放大於 1 時會被放大而變糊 | 目前只針對 100% 縮放設計（§7） |

---

## 3. 設計 token

所有顏色、尺寸和字型都在 [tokens.toml](tokens.toml)，淺色和深色各一組，由 `tools/build.py` 輸出成主題檔。

### 3.1 顏色

| token | 用途 | 淺色 | 深色 |
|---|---|---|---|
| `paper` | 面板底色 | `#FAF9F5` | `#262624` |
| `border` | 面板細邊框、選單分隔線 | `#DAD6CA` | `#42413B` |
| `ink` | 候選字、序號、註解、預編輯文字 | `#2D2B26` | `#E6E4DB` |
| `muted` | 翻頁箭頭、子選單箭頭 | `#6F6C63` | `#9C998F` |
| `hl` | 選中候選的淡暖灰底、選單的懸停底色 | `#EDE9DF` | `#383732` |
| `accent` | 唯一的陶土色，只用在選中候選的標記 | `#C15F3C` | `#D97757` |
| `shadow` | 便條陰影 | `#281E14` @ 7% | `#000000` @ 30% |

### 3.2 對比度（WCAG）

| 組合 | 淺色 | 深色 | 目標 |
|---|---|---|---|
| `ink` / `paper` | 13.4 | 11.9 | ≥ 7 |
| `ink` / `hl` | 11.7 | 9.4 | ≥ 7 |
| `muted` / `paper` | 5.0 | 5.3 | ≥ 4.5 |
| `accent` / `hl` | 3.5 | 3.8 | ≥ 3（非文字標記，而且還有底色和位置兩個提示） |
| `hl` / `paper` | 1.15 | 1.27 | 刻意壓得很低，要靠陶土色標記才能一眼找到 |

### 3.3 尺寸（以 1x 像素計）

| token | 值 | 說明 |
|---|---|---|
| 字型 | `Notepaper 11`（Fira Sans → Noto Serif CJK TC Medium） | 11pt，在 100% 縮放下漢字約 15px |
| `panel_radius` | 8 | 便條圓角 |
| `panel_border` | 1 | 細邊框 |
| `panel_inset` | 3 | 邊框內側到選中底邊緣的距離。8 − 3 = 5，剛好讓面板和選中底的圓角同心 |
| `shadow_spread` / `shadow_blur` / `shadow_offset_y` | 8 / 3 / 2 | 陰影範圍、高斯模糊標準差、向下偏移，也是 `ShadowMargin` 的依據（左右 8、上 6、下 10） |
| `cell_padding` | 上下 5、左右 7 | 單一候選（序號、候選字、註解）的內距，也就是 `TextMargin`。選中底剛好填滿整格，所以上下內距不能小於 `hl_radius` |
| `hl_radius` | 5 | 選中底的圓角 |
| `mark` | 7 × 2，圓頭，距選中底底邊 4 | 陶土色短線，寬度約等於 11pt Fira Sans 一個數字的字寬 |
| `arrow` | 4 × 8，線寬 1.5，四周留 4（下一頁箭頭右側留 7） | 翻頁箭頭，四周的留白同時當作點擊範圍 |
| `menu_padding` | 上下 5、左右 10 | 選單項目的內距 |

---

## 4. 版面

橫排，一列顯示所有候選。預編輯只有在**沒有**內嵌到應用程式時才會出現在面板上方。

```
╭──────────────────────────────────────────────────╮
│  ni hao                                          │ ← 預編輯（ink，Fira Sans）
│ ╭──────────╮                                     │
│ │ 1  你好  │  2  擬好   3  你   4  尼   5  妳  ‹ ›│ ← 候選列
│ ╰──────────╯                                     │
│    ‾‾                                            │ ← 陶土色短線，對齊序號正下方
╰──────────────────────────────────────────────────╯
   ↑ 細邊框 border＋極淡陰影，圓角 8
```

- 序號、拼音、註解用 Fira Sans，候選字用 Noto Serif CJK TC Medium。字型分工靠 Pango 依字元自動挑字型，不需要額外設定。
- 翻頁箭頭放在候選列最右邊，用 `muted` 色的細線 V 形箭頭。

---

## 5. 元件

### 5.1 面板（`[InputPanel/Background]`）

- `panel.svg`：`paper` 填色、1px `border` 描邊、圓角 8，外圍加上極淡的 `shadow` 陰影。
- 九宮格 `Margin` = 陰影範圍 + 圓角 + 邊框，確保拉伸時圓角和陰影不變形。
- `ShadowMargin` 設成陰影範圍，讓 fcitx5 定位時以便條本體、而不是陰影外緣對齊游標，滑鼠事件也不會落在陰影上。
- `ContentMargin` = `ShadowMargin` + `panel_border` + `panel_inset`（左右 12、上 10、下 14）。
- 如果某個環境畫不出透明的圓角，備用做法是 `Image` 留空，改用 `Color=paper`、`BorderColor=border`、`BorderWidth=1`，變成直角、沒有陰影的面板。

### 5.2 文字（`[InputPanel]`）

| 鍵 | 值 |
|---|---|
| `NormalColor` | `ink` |
| `HighlightCandidateColor` | `ink`（選中時字不變色） |
| `HighlightColor`（預編輯中被選取的片段文字） | `ink` |
| `HighlightBackgroundColor`（預編輯中被選取的片段底色） | `hl` |

在 fcitx5 5.1.18 以前，序號和註解只能跟候選字同色，層次只能靠字型（無襯線對明體）來區分。

### 5.3 選中狀態（`[InputPanel/Highlight]`）

- `highlight.svg`：`hl` 填色的圓角 5 矩形，沒有邊框。選中時字色不變。
- 陶土色短線：在選中底上疊一張 `mark.svg`（7×2 圓頭短線，`accent` 色）。
  - `Overlay=mark.svg`、`Gravity=Bottom Left`。
  - Highlight 的 `Margin` 同時決定九宮格切法和選中底比文字多出來的範圍，所以設成和 `TextMargin` 一樣（上下 5、左右 7），讓選中底剛好填滿整格。
  - 序號從選中底左緣往右 `Margin.Left` 的位置開始畫，所以 `OverlayOffsetX` = 7，短線就會落在序號正下方。`OverlayOffsetY` = 4，讓短線貼近序號但不碰到。
  - 另一個可行的位置是選中底左側的垂直短線（`Gravity=Center Left`，2×9）。它不受字寬影響，比較穩，但離「陶土色序號」的意象比較遠。

### 5.4 翻頁箭頭（`[InputPanel/PrevPage]`、`[InputPanel/NextPage]`）

- `prev.svg`：4×8 的 V 形，線寬 1.5，`muted` 色，不加底，四周留白 4（12×16）。
- `next.svg`：fcitx5 會把它貼齊內容區右緣，所以右側留白和候選格的 `cell_padding_x` 一樣是 7（15×16）。這樣箭頭到右邊框是 10px，跟左邊框到第一個序號的距離相同。
- `ClickMargin` 是從圖片往內縮的量，所以設成 0，讓整張圖片（含留白）都可以點。
- `PageButtonAlignment=Last Candidate`：箭頭和候選列垂直置中。用 `Center` 的話，面板上方有預編輯時箭頭會卡在兩列中間。
- 不能翻頁的箭頭由 fcitx5 以 30% 不透明度畫出，滑鼠移上去時是 70%。

### 5.5 右鍵選單（`[Menu]`）

只有用 XEmbed 托盤的桌面才會用到 fcitx5 自己畫的選單；托盤走 StatusNotifierItem 的桌面（例如 COSMIC）是由桌面自己畫選單。

- 底色、邊框、圓角和面板相同，但不加陰影。
- 文字 `ink`，懸停底色 `hl`，懸停時字色不變，不用陶土色。
- 分隔線用 `border` 色，1px。勾選標記用 `ink` 色，子選單箭頭用 `muted` 色。

### 5.6 字型（`classicui.conf` 與 fontconfig 別名）

```ini
Font="Notepaper 11"
MenuFont="Fira Sans 10"
```

搭配 `~/.config/fontconfig/conf.d/60-notepaper.conf`：

```xml
<match target="pattern">
  <test name="family"><string>Notepaper</string></test>
  <edit name="family" mode="assign" binding="strong">
    <string>Fira Sans</string>
    <string>Noto Serif CJK TC Medium</string>
  </edit>
</match>
```

明體用 Medium，是因為 11pt 的 Regular 橫筆只有一像素寬，會畫成很淡的灰線，深色底上最明顯，淺色底上也偏虛。Medium 的橫筆清楚，跟 Fira Sans Regular 的序號份量相當；SemiBold 則太重，會比序號搶眼。

---

## 6. 深淺色切換

候選窗有兩條繪製路徑，深淺色的處理方式不同：

| 路徑 | 例子 | 誰畫候選窗 | 怎麼切換深淺色 |
|---|---|---|---|
| Wayland text-input-v3、X11 | Chrome、Electron 程式、cosmic-term、XWayland 程式 | fcitx5 本身 | `UseDarkTheme=True`，fcitx5 透過 portal 的 `org.freedesktop.appearance color-scheme` 自己切換 |
| fcitx5-gtk / fcitx5-qt 模組，且桌面沒有 `zwp_input_panel_v1` | Firefox、Qt 程式 | 程式內的模組 | 模組只讀 `Theme=`，所以由 `tools/sync_theme.py` 在系統切換時改寫 `Theme=` |

`tools/sync_theme.py` 以 systemd 使用者服務 `notepaper-theme-sync` 常駐：

- 監看 portal 的 `color-scheme`：偏好深色時把 `Theme=` 改成 `notepaper-dark`，否則改回 `notepaper`，然後請 fcitx5 重新載入 classic UI。
- 整檔一次替換。fcitx5-gtk 監看設定檔所在的目錄，fcitx5-qt 每次變更後都會重新監看，所以兩者都會立刻重新載入。
- 平常在等 DBus 通知，不輪詢。
- `UseDarkTheme=True` 保留，服務沒在跑時，fcitx5 自己畫的候選窗仍然會切換。

---

## 7. 已知限制

- **Wayland popup 的候選窗會往右下偏移。** fcitx5 5.1.x 的 Wayland 視窗不會扣掉 `ShadowMargin`，所以走 input-method-v2 popup 的程式裡，便條本體會比游標往右偏 8px、往下偏 6px。X11 路徑會正確扣掉陰影。把 `shadow_spread` 調小可以縮短偏移，代價是陰影比較硬。
- **5.1.18 以前，註解和候選字同色同大。** 中間只靠一個空格分開，像倉頡反查的「你 人弓火」有可能被看成一個詞。
- **HiDPI。** SVG 以原尺寸點陣化，縮放大於 1 時會糊。屆時需要以 2 倍尺寸輸出 SVG，並把九宮格的值加倍。
- **字型選擇器會換掉別名。** 在 fcitx5 設定工具裡重新選字型並存檔，`Notepaper` 就會被換掉，漢字變回黑體。重新執行 `./install.sh` 可以改回來。
- **短線不會跟著字號縮放。** 改了字號之後，要手動確認 `mark_width`、`mark_nudge_x`、`mark_offset_y` 還對得上序號。

---

## 8. 未來：陶土色序號（fcitx5 5.1.18 以上）

升級到 fcitx5 5.1.18 以上之後，可以在產生器加上這個變體：

| 鍵 | 值 |
|---|---|
| `CandidateLabelColor` | `muted` |
| `HighlightCandidateLabelColor` | `accent` |
| `CandidateCommentColor` / `HighlightCandidateCommentColor` | `muted` |
| `CommentTextSizeFactor` | 90（11pt 已經偏小，不宜再縮太多） |

同時要拿掉 `[InputPanel/Highlight]` 的 `Overlay`。短線和陶土色序號不能同時存在，否則會出現兩個陶土色。

---

## 9. 開發工具

- **`tools/build.py`**：每個色值都會同時出現在 theme.conf 和好幾個 SVG 裡，所以用產生器從 token 輸出，不手動維護。它只在內容真的改變時才重寫檔案，這樣只改顏色時，`install.sh` 不會為了字型別名去重啟 fcitx5。
- **`tools/snapshot.py`**：透過 DBus 建立一個假的輸入上下文、打字，然後只擷取 fcitx5 候選窗本身的 X11 視窗，再鋪到指定的底色上。它驗證的是 fcitx5 畫出來的結果，不包含合成器怎麼處理透明，也拍不到 Wayland popup 和程式內模組畫的候選窗。
  - fcitx5-rime 預設讓所有視窗共用同一個 RIME 狀態，所以 RIME 必須在中文模式，`--keys` 也要配合目前的方案。
  - 比較字型時，一定要放一個已知字族當對照組（例如 `Noto Sans CJK TC 11`）。字型別名沒生效時，fcitx5 會默默退回預設字型，沒有對照組很容易看錯。
