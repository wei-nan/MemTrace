# MemTrace Design System — 色彩系統規範

> **版本：** 2.0
> **最後同步：** 2026-04-27（與 `packages/ui/src/index.css` 對齊）
> **適用範圍：** `packages/ui/src/index.css`、所有 React 元件、SVG 資產
> **此文件以實際 CSS 為準，修改前請與 UI 負責人確認。**

---

## 設計原則

1. **單一品牌色** — 整個系統只有一個品牌色族（葉綠 Green），不引入第二品牌色
2. **無漸層** — 所有元件一律使用平色（flat color），全面禁止 `linear-gradient` / `radial-gradient`
3. **主色隨模式調整明度** — 暗色模式用亮綠 `#4ade80`、亮色模式用深綠 `#16a34a`，確保兩模式下都有足夠對比
4. **語意色僅限狀態** — success / warning / error / info 只用在狀態提示，不能挪做品牌色
5. **硬編碼為零** — 所有顏色必須透過 CSS Token 引用，禁止直接寫色碼

---

## 主色族（Green）

| 模式 | `--color-primary` | `--color-primary-hover` | `--text-on-primary` |
|------|-------------------|-------------------------|---------------------|
| 暗色（預設） | `#4ade80` | `#22c55e` | `#FFFFFF` |
| 亮色 | `#16a34a` | `#15803d` | `#0a2e18` |

> 暗色模式採亮綠是為了在深色底上有足夠亮度；亮色模式改為深綠避免在白底刺眼。`--text-on-primary` 對應變動，避免按鈕文字過淺/過深。

---

## 語意色（兩模式都用）

| Token | 暗色 | 亮色 | 用途 |
|-------|------|------|------|
| `--color-success` | `#4ADE80` | `#16A34A` | 成功訊息、驗證通過 |
| `--color-warning` | `#FBBF24` | `#D97706` | 警告、待處理 |
| `--color-error` | `#F87171` | `#DC2626` | 錯誤、危險操作 |
| `--color-info` | `#60A5FA` | `#2563EB` | 中性資訊提示 |

每個語意色都有對應 `*-subtle` 變體（用於背景底色）。

---

## 圖譜節點與邊（GraphView）

節點顏色對應 `trust_score`（與規格 §4.1 trust 維度連動）：

| Token | 暗色 | 亮色 | 觸發條件 |
|-------|------|------|---------|
| `--node-core` | `#4ade80` | `#16a34a` | 中心節點 / `trust_score ≥ 0.8` |
| `--node-secondary` | `#86efac` | `#4ade80` | `trust_score ≥ 0.5` |
| `--node-leaf` | `#bbf7d0` | `#86efac` | `trust_score ≥ 0.2` |
| `--node-faded` | `#374151` | `#D1D5DB` | `status = 'archived'` 或 faded |

邊則用 RGBA 透明度區分強弱：

| Token | 用途 |
|-------|------|
| `--edge-default` | 一般邊（weight 中等） |
| `--edge-strong` | 高權重 / hover 中 |
| `--edge-faded` | weight < min_weight 已 faded |

---

## AI Provider 識別色

每個第三方 AI 供應商有專屬色，用於 Provider 選單與用量卡片：

| Provider | 暗色 | 亮色 |
|----------|------|------|
| OpenAI | `#10A37F` | `#0E8A6B` |
| Anthropic | `#D97757` | `#C2410C` |
| Gemini | `#8E75FF` | `#16a34a`（暫對齊主色）|

每個都有 `*-subtle` 變體。

---

## 背景 / 邊框 / 文字 token

完整 token 表以 `packages/ui/src/index.css` 的 `:root` 區塊為準。摘要如下：

### 暗色模式（預設）

```css
:root,
:root[data-theme="dark"] {
  /* 背景層次 */
  --bg-base:        #0F1115;               /* 頁面底層 */
  --bg-surface:     #1A1D24;               /* 卡片、面板、Modal */
  --bg-elevated:    #22262F;               /* Dropdown、Tooltip */
  --bg-overlay:     rgba(0, 0, 0, 0.60);   /* Modal 遮罩 */

  /* 邊框（三層） */
  --border-subtle:  rgba(255, 255, 255, 0.06);
  --border-default: rgba(255, 255, 255, 0.10);
  --border-strong:  rgba(255, 255, 255, 0.18);

  /* 文字（五層） */
  --text-primary:    #F3F4F6;
  --text-secondary:  #9CA3AF;
  --text-muted:      #6B7280;
  --text-disabled:   #374151;
  --text-on-primary: #FFFFFF;

  /* 主色族（葉綠） */
  --color-primary:        #4ade80;
  --color-primary-hover:  #22c55e;
  --color-primary-subtle: rgba(74, 222, 128, 0.15);

  /* 陰影 */
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.40);
  --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.50);
  --shadow-lg: 0 8px 32px rgba(0, 0, 0, 0.60);
}
```

### 亮色模式

```css
:root[data-theme="light"] {
  --bg-base:        #F8F9FC;               /* 帶藍灰調，非純白 */
  --bg-surface:     #FFFFFF;
  --bg-elevated:    #FFFFFF;
  --bg-overlay:     rgba(0, 0, 0, 0.40);

  --border-subtle:  #F1F3F9;
  --border-default: #E4E7EF;
  --border-strong:  #C7D0E3;

  --text-primary:    #111827;
  --text-secondary:  #374151;
  --text-muted:      #6B7280;
  --text-disabled:   #9CA3AF;
  --text-on-primary: #0a2e18;

  --color-primary:        #16a34a;
  --color-primary-hover:  #15803d;
  --color-primary-subtle: rgba(22, 163, 74, 0.10);

  --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.08);
  --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.08);
  --shadow-lg: 0 8px 32px rgba(0, 0, 0, 0.10);
}
```

> 完整版（含所有語意色、節點色、AI provider 色）見 `packages/ui/src/index.css`。

---

## 元件應用規則

### 按鈕

| 種類      | 背景                    | 文字                  | Hover                   |
|-----------|-------------------------|-----------------------|-------------------------|
| Primary   | `--color-primary`       | `--text-on-primary`   | `--color-primary-hover` |
| Secondary | transparent             | `--text-primary`      | `--bg-elevated`         |
| Danger    | `--color-error-subtle`  | `--color-error`       | `--color-error`（背景全填）|
| Icon      | transparent             | `--text-secondary`    | `--bg-elevated`         |

```css
.btn-primary {
  background: var(--color-primary);
  color: var(--text-on-primary);
  border: none;
  border-radius: 8px;
  padding: 10px 20px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}
.btn-primary:hover {
  background: var(--color-primary-hover);
  transform: translateY(-1px);
}
```

### 輸入框

```css
.mt-input {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  color: var(--text-primary);
  border-radius: 8px;
  padding: 9px 12px;
  font-size: 14px;
}
.mt-input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-subtle);
}
```

### 卡片 / 面板（glass-panel）

```css
.glass-panel {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 16px;
  box-shadow: var(--shadow-md);
}
```

### Tag

```css
.tag {
  background: var(--color-primary-subtle);
  color: var(--color-primary);
  border-radius: 100px;
  padding: 4px 12px;
  font-size: 0.8rem;
  font-weight: 500;
}
```

### 圖譜節點顏色函式

```typescript
function nodeColor(trustScore: number, status: string): string {
  if (status === 'archived') return 'var(--node-faded)';
  if (trustScore >= 0.8)     return 'var(--node-core)';
  if (trustScore >= 0.5)     return 'var(--node-secondary)';
  return                            'var(--node-leaf)';
}
```

---

## 字型

| 用途 | 字型 |
|------|------|
| 正文 | `Inter`（300–700） |
| 標題（h1–h6） | `Outfit`（400–700）— `font-weight: 600`、`letter-spacing: -0.02em` |

兩者由 `index.css` 透過 Google Fonts 載入。

---

## 亮色 / 暗色模式切換

切換邏輯放在 `App.tsx`：

```typescript
const savedTheme = localStorage.getItem('mt_theme') ?? 'dark';
document.documentElement.setAttribute('data-theme', savedTheme);

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme');
  const next = current === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('mt_theme', next);
}
```

---

## Logo 使用規範

| 場景 | 規格 |
|------|------|
| App 側邊欄（暗色） | 主色 `#4ade80`，輪廓白色 |
| 文件、淺色背景 | 主色 `#16a34a`，輪廓 `#374151` |
| Favicon / App Icon | 純圖形，32×32，單色採當前模式主色 |
| 最小尺寸 | 水平版 Logo 不得小於 **120px 寬**；Icon 不得小於 **16px** |

---

## 禁止事項速查

| 禁止 | 原因 |
|------|------|
| `linear-gradient(...)` | 漸層設計已廢除 |
| `radial-gradient(...)` | 同上 |
| 直接寫色碼（如 `#4ade80`）| 必須透過 Token 引用 |
| 引入綠色以外的品牌色 | 語意色僅限狀態提示 |
| 在 Logo 或圖譜節點上使用語意色 | 節點只能用 `--node-*` 系列 |
| 在元件層覆寫 `--color-primary` | 主色為設計決策，不隨情境調整 |

---

## 變更歷程

| 版本 | 日期 | 主要變更 |
|------|------|---------|
| 1.0 | 2026-04-11 | 首版，採 Indigo `#4F46E5`，主色不隨模式改變 |
| **2.0** | **2026-04-27** | 改為葉綠主色族，主色隨模式調整明度；移除 `--color-primary-50/100/.../900` 數字階；新增 AI Provider 與圖譜節點 token |
