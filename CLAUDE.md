# CLAUDE.md

便箋 Notepaper 是 fcitx5 classic UI 的候選窗主題（淺色 `notepaper`、深色 `notepaper-dark`）。使用方式見 README.md，設計與限制見 DESIGN.md。

## 指令

```bash
python3 tools/build.py                 # tokens.toml + templates/ → dist/
./install.sh                           # 連結主題與字型別名、合併 classicui.conf、啟動同步服務、重新載入 fcitx5
./install.sh --uninstall               # 全部還原
python3 tools/snapshot.py --keys 5k4g4 --zoom 2 -o /tmp/panel.png   # 拍 fcitx5 畫的候選窗（--keys 依 RIME 方案：注音 5k4g4、拼音 nihao）
systemctl --user status notepaper-theme-sync                        # 深淺色同步服務
journalctl --user -u notepaper-theme-sync
gdbus call --session --dest org.fcitx.Fcitx5 --object-path /controller \
  --method org.fcitx.Fcitx.Controller1.ReloadAddonConfig classicui  # 只重新載入 classic UI
```

沒有測試套件；驗證靠 `snapshot.py` 截圖和在真實程式裡打字。

發佈新版本：

```bash
git tag -a v1.2.3 -m "v1.2.3"           # dist/ 必須已經重新產生並 commit
tools/package.sh v1.2.3                  # → build/fcitx5-notepaper-1.2.3.tar.gz 和 .sha256
git push origin main v1.2.3
gh release create v1.2.3 build/fcitx5-notepaper-1.2.3.tar.gz build/fcitx5-notepaper-1.2.3.tar.gz.sha256
```

## 架構

- `tokens.toml` 是唯一的事實來源：顏色（淺色、深色各一組）、尺寸、字型。
- `tools/build.py` 用 `string.Template` 把 `templates/` 填成 `dist/`：兩套主題（theme.conf + SVG）、fontconfig 別名 `dist/fontconfig/60-notepaper.conf`、要合併進使用者設定的 `dist/classicui.conf`。
- `install.sh` 用符號連結把 `dist/` 接到 `~/.local/share/fcitx5/themes/` 和 `~/.config/fontconfig/conf.d/`。在 git checkout 裡執行時連結到 checkout 本身（專案資料夾不能搬動）；在其他地方執行（Release 下載的 tar.gz）時，會先把自己、`dist/`、`tools/sync_theme.py` 複製到 `~/.local/share/fcitx5-notepaper/` 再從那裡安裝。
- `tools/package.sh` 用 `git archive` 從 tag 打包 Release，內容只有執行時需要的檔案加上文件，不含產生器和模板。
- `tools/sync_theme.py` 以 systemd 使用者服務常駐，系統切換深淺色時改寫 `classicui.conf` 的 `Theme=`。這是給程式內自己畫候選窗的 fcitx5-gtk / fcitx5-qt 用的，它們不認 `DarkTheme`。

## 規則

- **不要手改 `dist/`。** 改 `tokens.toml` 或 `templates/`，執行 `build.py`，然後把 `dist/` 跟原始碼一起 commit。
- **只有一個陶土色。** `accent` 只用在選中候選的標記（`mark.svg`）。選單、箭頭、邊框都不能用。
- **不要宣告 `[AccentColorField]`**，否則系統強調色會蓋掉配色。
- **以 fcitx5 5.1.7 為基準。** 加任何 theme.conf 鍵之前，先查對應版本的 `src/ui/classic/theme.h`；舊版會默默忽略不認得的鍵。`CandidateLabelColor`、`CommentTextSizeFactor` 等鍵要 5.1.18 才有（DESIGN.md §8）。
- **Highlight 的 `Margin` 同時是九宮格切法**，所以 `cell_padding_x/y` 不能小於 `hl_radius`（`build.py` 會檢查）。
- **fcitx5 只在啟動時讀一次 fontconfig。** 改了 `[font]` 就要重啟 fcitx5；`install.sh` 會比較別名檔和 fcitx5 程序的時間自動處理，`build.py` 也只在內容改變時才重寫檔案，避免不必要的重啟。
- **`fcitx5-remote -r` 不會重新載入 classic UI**，要用上面的 `ReloadAddonConfig classicui`。

## 驗證時的注意事項

- fcitx5-rime 預設讓所有視窗共用同一個 RIME 狀態（`InputState=All`）。`snapshot.py` 打的字會進入使用者目前的組字：使用者可能正在打字時不要執行，RIME 也必須在中文模式。
- 比較字型時，一定要放一個已知字族當對照組（例如 `Noto Sans CJK TC 11`）。別名沒生效時，fcitx5 會默默退回預設字型。
- `snapshot.py` 只拍得到 fcitx5 在 X11 路徑畫的候選窗。Wayland popup（Chrome、cosmic-term）和程式內模組（Firefox、Qt）畫的候選窗，要請使用者在真實程式裡打字確認。
- 看淺色版時，不要切換系統外觀：暫時把 `classicui.conf` 的 `DarkTheme=` 改成 `notepaper`，重新載入、截圖，再改回 `notepaper-dark`。

## 風格

- Python 只用標準函式庫和 `gi`（PyGObject），不加其他依賴；用 `python3 -I` 執行。
- Shell 腳本用 `set -euo pipefail`。
- 程式碼註解用英文，而且要精簡；文件（README、DESIGN）用繁體中文。

## 個人設定

個人偏好與私人筆記不納入版本控制：@CLAUDE.local.md
