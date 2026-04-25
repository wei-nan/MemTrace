import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Archive, ArrowUpRight, Boxes, Ghost, TimerReset } from "lucide-react";
import { nodes, workspaces, type Node } from "./api";
import { useTranslation } from "react-i18next";
import { useModal } from "./components/ModalContext";

type HealthTab = "orphan" | "faded" | "never_traversed";

const TAB_META: Record<HealthTab, { label: string; icon: ReactNode }> = {
  orphan: { label: "孤立節點", icon: <Ghost size={15} /> },
  faded: { label: "淡忘節點", icon: <Boxes size={15} /> },
  never_traversed: { label: "從未使用", icon: <TimerReset size={15} /> },
};

export default function NodeHealthManager({
  wsId,
  onEditNode,
}: {
  wsId: string;
  onEditNode: (node: Node) => void;
}) {
  const { t } = useTranslation();
  const { toast } = useModal();
  const [tab, setTab] = useState<HealthTab>("orphan");
  const [items, setItems] = useState<Record<HealthTab, Node[]>>({
    orphan: [],
    faded: [],
    never_traversed: [],
  });
  const [selected, setSelected] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(false);
  const [kbType, setKbType] = useState<string>("evergreen");

  const load = async () => {
    setLoading(true);
    try {
      const [workspace, orphan, faded, neverTraversed] = await Promise.all([
        workspaces.get(wsId),
        nodes.list(wsId, { filter: "orphan" }),
        nodes.list(wsId, { filter: "faded" }),
        nodes.list(wsId, { filter: "never_traversed" }),
      ]);
      setKbType(workspace.kb_type);
      setItems({
        orphan,
        faded,
        never_traversed: neverTraversed,
      });
    } catch (e) {
      toast({ message: e instanceof Error ? e.message : String(e), variant: "error" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [wsId]);

  const visibleTabs = useMemo(
    () => (kbType === "evergreen" ? (["orphan", "faded"] as HealthTab[]) : (["orphan", "faded", "never_traversed"] as HealthTab[])),
    [kbType],
  );
  const currentItems = items[tab];
  const selectedIds = Object.entries(selected).filter(([, checked]) => checked).map(([id]) => id);

  const toggleAll = () => {
    const allSelected = currentItems.every((item) => selected[item.id]);
    const next = { ...selected };
    currentItems.forEach((item) => {
      next[item.id] = !allSelected;
    });
    setSelected(next);
  };

  const handleBulkArchive = async () => {
    if (!selectedIds.length) return;
    try {
      const result = await nodes.bulkArchive(wsId, selectedIds);
      toast({ message: `${t('health.archiveSuccess')} ${result.archived_count}`, variant: "success" });
      setSelected({});
      await load();
    } catch (e) {
      toast({ message: e instanceof Error ? e.message : String(e), variant: "error" });
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        {visibleTabs.map((item) => (
          <button
            key={item}
            className={`tag ${tab === item ? "tag-active" : ""}`}
            onClick={() => setTab(item)}
            style={{ display: "flex", alignItems: "center", gap: 6 }}
          >
            {TAB_META[item].icon}
            {TAB_META[item].label}
          </button>
        ))}
      </div>

      <div style={{ background: "var(--bg-surface)", border: "1px solid var(--border-default)", borderRadius: 16, overflow: "hidden" }}>
        <div style={{ display: "grid", gridTemplateColumns: "48px 1.5fr 120px 120px", padding: "12px 16px", fontSize: 12, color: "var(--text-muted)", borderBottom: "1px solid var(--border-default)" }}>
          <div><input type="checkbox" checked={currentItems.length > 0 && currentItems.every((item) => selected[item.id])} onChange={toggleAll} /></div>
          <div>{t('health.node')}</div>
          <div>{t('health.type')}</div>
          <div>{t('health.action')}</div>
        </div>

        {loading ? (
          <div style={{ padding: 20, color: "var(--text-muted)" }}>{t('health.loading')}</div>
        ) : currentItems.length === 0 ? (
          <div style={{ padding: 20, color: "var(--text-muted)" }}>{t('health.noData')}</div>
        ) : (
          currentItems.map((item) => (
            <div key={item.id} style={{ display: "grid", gridTemplateColumns: "48px 1.5fr 120px 120px", padding: "14px 16px", alignItems: "center", borderTop: "1px solid var(--border-subtle)" }}>
              <div>
                <input
                  type="checkbox"
                  checked={Boolean(selected[item.id])}
                  onChange={(e) => setSelected((prev) => ({ ...prev, [item.id]: e.target.checked }))}
                />
              </div>
              <div style={{ minWidth: 0 }}>
                <div style={{ fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{item.title_zh || item.title_en}</div>
                <div style={{ fontSize: 12, color: "var(--text-muted)" }}>{item.id}</div>
              </div>
              <div style={{ fontSize: 13 }}>{t(`content_type.${item.content_type}`, { defaultValue: item.content_type })}</div>
              <div>
                <button className="btn-secondary" onClick={() => onEditNode(item)} style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                  <ArrowUpRight size={14} /> 編輯
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
        <div style={{ fontSize: 13, color: "var(--text-muted)" }}>{selectedIds.length} {t('health.selected')}</div>
        <button className="btn-primary" onClick={handleBulkArchive} disabled={!selectedIds.length} style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
          <Archive size={15} /> {t('health.bulkArchive')}
        </button>
      </div>
    </div>
  );
}
