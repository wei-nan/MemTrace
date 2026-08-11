import { Maximize2 } from 'lucide-react';

/**
 * Renders AI-generated HTML/Canvas/JS chart blocks inside a sandboxed iframe.
 *
 * Security boundary (see mem_d03293a9 / ws_6aa957c3): `sandbox` grants only
 * `allow-scripts` — no `allow-same-origin`, so the iframe executes in a unique
 * opaque origin with no access to the parent DOM, cookies, or localStorage,
 * and it cannot navigate the top window, open popups, or submit forms. The
 * injected CSP additionally blocks all outbound network requests from inside
 * the sandboxed document. This is a deliberate accepted tradeoff: the AI's
 * HTML/JS is never sanitized or inspected, only isolated.
 */
const CHART_CSP =
  "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline' 'self'; img-src data:; font-src data:";

function buildSrcDoc(html: string): string {
  return `<!DOCTYPE html><html><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="${CHART_CSP}"><style>html,body{margin:0;padding:8px;font-family:system-ui,sans-serif;overflow:auto;}</style></head><body>${html}</body></html>`;
}

/**
 * Opens the same sandboxed content full-page in a new tab. Deliberately does
 * NOT navigate the new tab directly to a blob/data URL of the chart HTML —
 * that would hand the AI's JS the tab's real origin (cookies, localStorage),
 * losing the sandbox entirely. Instead the new tab's own document is built
 * via DOM APIs (no markup string parsing of untrusted content) and still
 * embeds the chart inside the same `sandbox="allow-scripts"` iframe, just
 * sized to fill the window.
 */
function openInNewTab(srcDoc: string) {
  const w = window.open('', '_blank');
  if (!w) return; // popup blocked; silently no-op, the inline chart is still visible
  w.document.title = 'AI Chart';
  const style = w.document.createElement('style');
  style.textContent = 'html,body{margin:0;height:100%;}iframe{width:100%;height:100%;border:0;display:block;}';
  w.document.head.appendChild(style);
  const iframe = w.document.createElement('iframe');
  iframe.setAttribute('sandbox', 'allow-scripts');
  iframe.setAttribute('referrerpolicy', 'no-referrer');
  iframe.srcdoc = srcDoc;
  w.document.body.appendChild(iframe);
}

export default function ChartFrame({ html }: { html: string }) {
  const srcDoc = buildSrcDoc(html);

  return (
    <div style={{ position: 'relative', marginTop: 10 }}>
      <iframe
        srcDoc={srcDoc}
        sandbox="allow-scripts"
        referrerPolicy="no-referrer"
        title="AI-generated chart"
        style={{
          width: '100%',
          height: 420,
          border: '1px solid var(--border-default)',
          borderRadius: 8,
          background: 'white',
          display: 'block',
        }}
      />
      <button
        onClick={() => openInNewTab(srcDoc)}
        title="Open in new tab"
        style={{
          position: 'absolute', top: 8, right: 8,
          width: 26, height: 26, borderRadius: 6,
          border: '1px solid var(--border-default)',
          background: 'var(--bg-surface)', color: 'var(--text-secondary)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          cursor: 'pointer', opacity: 0.85,
        }}
      >
        <Maximize2 size={13} />
      </button>
    </div>
  );
}
