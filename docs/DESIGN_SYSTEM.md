# MemTrace Design System — 色彩系統規範

> **版本：** 1.0  
> **適用範圍：** `packages/ui/src/index.css`、所有 React 元件、SVG 資產  
> **此文件由設計決策驅動，修改前請先與負責人確認。**

---

## 設計原則

1. **單一主色** — 整個系統只有一個品牌色 `#4F46E5`，不引入第二品牌色
2. **無漸層** — 所有元件一律使用平色（flat color），全面禁止 `linear-gradient` / `radial-gradient`
3. **主色不隨模式改變** — `#4F46E5` 在亮色與暗色模式下完全一致
4. **深淺傳達語意** — 用同色族深淺差異表達層次與狀態，不引入新顏色
5. **硬編碼為零** — 所有顏色必須透過 CSS Token 引用，禁止直接寫色碼

---

## 品牌色族（Indigo Scale）

| Token                    | Hex       | 用途                            |
|--------------------------|-----------|---------------------------------|
| `--color-primary-900`    | `#1E1B4B` | 暗色模式強調邊框                |
| `--color-primary-700`    | `#4338CA` | Hover / 按壓狀態                |
| `--color-primary-600`    | `#4F46E5` | **主色 — 按鈕、Logo、互動元件** |
| `--color-primary-400`    | `#818CF8` | Icon active、次要強調           |
| `--color-primary-300`    | `#A5B4FC` | 圖譜次要節點、說明文字強調      |
| `--color-primary-200`    | `#C7D2FE` | 圖譜葉節點、Tag 背景            |
| `--color-primary-100`    | `#E0E7FF` | 亮色模式選中背景                |
| `--color-primary-50`     | `#EEF2FF` | 亮色模式 hover 背景             |

---

## CSS Token 定義

將以下內容完整取代 `index.css` 的 `:root` 區塊。

### 暗色模式（預設）

```css
:root,
:root[data-theme="dark"] {
  /* ── 背景層次 ────────────────────────────────────── */
  --bg-base:        #0F1115;               /* 頁面底層背景 */
  --bg-surface:     #1A1D24;               /* 卡片、面板、Modal */
  --bg-elevated:    #22262F;               /* Dropdown、Tooltip */
  --bg-overlay:     rgba(0, 0, 0, 0.60);  /* Modal 遮罩 */

  /* ── 邊框 ────────────────────────────────────────── */
  --border-subtle:  rgba(255, 255, 255, 0.06);
  --border-default: rgba(255, 255, 255, 0.10);
  --border-strong:  rgba(255, 255, 255, 0.18);

  /* ── 文字 ────────────────────────────────────────── */
  --text-primary:    #F3F4F6;
  --text-secondary:  #9CA3AF;
  --text-muted:      #6B7280;
  --text-disabled:   #374151;
  --text-on-primary: #FFFFFF;

  /* ── 主色 ────────────────────────────────────────── */
  --color-primary:        #4F46E5;
  --color-primary-hover:  #4338CA;
  --color-primary-subtle: rgba(79, 70, 229, 0.15);

  /* ── 語意色（僅用於狀態提示） ────────────────────── */
  --color-success:        #4ADE80;
  --color-success-subtle: rgba(74, 222, 128, 0.12);
  --color-warning:        #FBBF24;
  --color-warning-subtle: rgba(251, 191, 36, 0.12);
  --color-error:          #F87171;
  --color-error-subtle:   rgba(248, 113, 113, 0.12);
  --color-info:           #60A5FA;
  --color-info-subtle:    rgba(96, 165, 250, 0.12);

  /* ── 圖譜節點（對應 trust_score） ───────────────── */
  --node-core:      #4F46E5;               /* 中心節點 / 高信任度 ≥ 0.8 */
  --node-secondary: #A5B4FC;               /* 次要節點 ≥ 0.5 */
  --node-leaf:      #C7D2FE;               /* 葉節點 ≥ 0.2 */
  --node-faded:     #374151;               /* 已封存節點 */
  --edge-default:   rgba(165, 180, 252, 0.35);
  --edge-strong:    rgba(79, 70, 229, 0.70);
  --edge-faded:     rgba(55, 65, 81, 0.40);

  /* ── 陰影 ────────────────────────────────────────── */
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.40);
  --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.50);
  --shadow-lg: 0 8px 32px rgba(0, 0, 0, 0.60);
}
```

### 亮色模式

```css
:root[data-theme="light"] {
  /* ── 背景層次 ────────────────────────────────────── */
  --bg-base:        #F8F9FC;               /* 帶藍灰調，非純白 */
  --bg-surface:     #FFFFFF;
  --bg-elevated:    #FFFFFF;
  --bg-overlay:     rgba(0, 0, 0, 0.40);

  /* ── 邊框 ────────────────────────────────────────── */
  --border-subtle:  #F1F3F9;
  --border-default: #E4E7EF;
  --border-strong:  #C7D0E3;

  /* ── 文字 ────────────────────────────────────────── */
  --text-primary:    #111827;
  --text-secondary:  #374151;
  --text-muted:      #6B7280;
  --text-disabled:   #9CA3AF;
  --text-on-primary: #FFFFFF;

  /* ── 主色（與暗色模式相同） ─────────────────────── */
  --color-primary:        #4F46E5;
  --color-primary-hover:  #4338CA;
  --color-primary-subtle: #EEF2FF;

  /* ── 語意色 ──────────────────────────────────────── */
  --color-success:        #16A34A;
  --color-success-subtle: #F0FDF4;
  --color-warning:        #D97706;
  --color-warning-subtle: #FFFBEB;
  --color-error:          #DC2626;
  --color-error-subtle:   #FEF2F2;
  --color-info:           #2563EB;
  --color-info-subtle:    #EFF6FF;

  /* ── 圖譜節點 ────────────────────────────────────── */
  --node-core:      #4F46E5;
  --node-secondary: #818CF8;
  --node-leaf:      #A5B4FC;
  --node-faded:     #D1D5DB;
  --edge-default:   rgba(79, 70, 229, 0.25);
  --edge-strong:    rgba(79, 70, 229, 0.60);
  --edge-faded:     rgba(156, 163, 175, 0.40);

  /* ── 陰影 ────────────────────────────────────────── */
  --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.08);
  --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.08);
  --shadow-lg: 0 8px 32px rgba(0, 0, 0, 0.10);
}
```

---

## 元件應用規則

### 按鈕

| 種類      | 背景                    | 文字                  | Hover                   |
|-----------|-------------------------|-----------------------|-------------------------|
| Primary   | `--color-primary`       | `--text-on-primary`   | `--color-primary-hover` |
| Secondary | transparent             | `--text-primary`      | `--bg-elevated`         |
| Danger    | `--color-error`         | `#FFFFFF`             | 加深 10%                |
| Ghost     | transparent             | `--color-primary`     | `--color-primary-subtle`|

```css
/* Primary Button — 範例 */
.btn-primary {
  background: var(--color-primary);
  color: var(--text-on-primary);
  border: none;
  border-radius: 8px;
  padding: 10px 20px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.15s;
}
.btn-primary:hover {
  background: var(--color-primary-hover);
}
/* ❌ 禁止：box-shadow: 0 4px 15px var(--accent-glow); */
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
  transition: border-color 0.15s, box-shadow 0.15s;
}
.mt-input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-subtle);
}
```

### 卡片 / 面板

```css
.card {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: 12px;
  box-shadow: var(--shadow-sm);
}
/* 亮色模式下陰影自動切換，無需額外處理 */
```

### Badge / Tag

```css
.tag {
  background: var(--color-primary-subtle);
  color: var(--color-primary);
  border-radius: 20px;
  padding: 2px 10px;
  font-size: 12px;
  font-weight: 500;
}
```

### 圖譜節點（GraphView）

```typescript
// trust_score 對應節點顏色
function nodeColor(trustScore: number, status: string): string {
  if (status === 'archived') return 'var(--node-faded)';
  if (trustScore >= 0.8)     return 'var(--node-core)';
  if (trustScore >= 0.5)     return 'var(--node-secondary)';
  return                            'var(--node-leaf)';
}
```

---

## 需要移除的現有程式碼

以下程式碼分散在 `index.css` 與各元件中，**全部需要清除或替換**：

### 從 `index.css` 移除

```css
/* 移除這些 variables */
--gradient-start: #3b82f6;
--gradient-end:   #8b5cf6;
--accent-color:   #6366f1;
--accent-hover:   #4f46e5;
--accent-glow:    rgba(99, 102, 241, 0.25);

/* 移除這些背景裝飾 */
background-image: radial-gradient(circle at 15% 50%, rgba(59, 130, 246, 0.08) ...);
background-image: radial-gradient(circle at 85% 30%, rgba(139, 92, 246, 0.08) ...);
```

### 從元件中移除

```css
/* ❌ 這類寫法全部移除 */
background: linear-gradient(135deg, var(--gradient-start), var(--gradient-end));
box-shadow: 0 4px 15px var(--accent-glow);
filter: brightness(1.1);   /* hover 效果改用 --color-primary-hover */

/* ✅ 替換為 */
background: var(--color-primary);
/* hover 時 */
background: var(--color-primary-hover);
```

---

## 亮色 / 暗色模式切換實作

在 `main.tsx` 或 `App.tsx` 加入切換邏輯：

```typescript
// 讀取使用者偏好
const savedTheme = localStorage.getItem('mt_theme') ?? 'dark';
document.documentElement.setAttribute('data-theme', savedTheme);

// 切換函式
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
| App 側邊欄（暗色） | `logo-dark.svg` — 主色 `#4F46E5`，輪廓白色 |
| 文件、淺色背景 | `logo-light.svg` — 主色 `#4F46E5`，輪廓 `#374151` |
| Favicon / App Icon | `favicon.svg` — 純圖形，32×32，單色 `#4F46E5` |
| 最小尺寸 | 水平版 Logo 不得小於 **120px 寬**；Icon 不得小於 **16px** |

---

## 禁止事項速查

| 禁止 | 原因 |
|------|------|
| `linear-gradient(...)` | 漸層設計已廢除 |
| `radial-gradient(...)` | 同上（裝飾性背景如需使用，opacity 必須 < 0.05）|
| 直接寫色碼（如 `#6366f1`）| 必須透過 Token 引用 |
| 引入 Indigo 以外的品牌色 | 語意色僅限狀態提示 |
| 在 Logo 或圖譜節點上使用語意色 | 節點只允許 `--node-*` 系列 |
| 修改 `--color-primary` 的色值 | 主色為設計決策，不隨情境調整 |
