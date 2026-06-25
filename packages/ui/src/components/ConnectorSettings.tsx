import { useCallback, useEffect, useMemo, useState } from "react";
import { Link2, Pause, Play, Plus, Trash2 } from "lucide-react";
import {
  connectors,
  type ConnectorAccount,
  type ConnectorBinding,
  type ConnectorDirection,
  type ConnectorProvider,
} from "../api";
import { useModal } from "./ModalContext";
import { Button, Card, Input } from "./ui";

const PROVIDERS: Array<{ value: ConnectorProvider; label: string }> = [
  { value: "google_drive", label: "Google Drive" },
  { value: "asana", label: "Asana" },
  { value: "github", label: "GitHub" },
  { value: "gitlab", label: "GitLab" },
];

const CONTAINER_LABELS: Record<ConnectorProvider, string> = {
  google_drive: "Folder ID",
  asana: "Project GID",
  github: "owner/repository",
  gitlab: "Project ID or path",
};

const CONTAINER_TYPES: Record<ConnectorProvider, string> = {
  google_drive: "folder",
  asana: "project",
  github: "repository",
  gitlab: "project",
};

export default function ConnectorSettings({ wsId, zh }: { wsId: string; zh: boolean }) {
  const { confirm, toast } = useModal();
  const [accounts, setAccounts] = useState<ConnectorAccount[]>([]);
  const [bindings, setBindings] = useState<ConnectorBinding[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [provider, setProvider] = useState<ConnectorProvider>("google_drive");
  const [accountId, setAccountId] = useState("");
  const [accountName, setAccountName] = useState("");
  const [credential, setCredential] = useState("");
  const [selectedAccountId, setSelectedAccountId] = useState("");
  const [containerId, setContainerId] = useState("");
  const [containerName, setContainerName] = useState("");
  const [direction, setDirection] = useState<ConnectorDirection>("inbound");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [nextAccounts, nextBindings] = await Promise.all([
        connectors.listAccounts(),
        connectors.listBindings(wsId),
      ]);
      setAccounts(nextAccounts);
      setBindings(nextBindings);
      setSelectedAccountId((current) => (
        nextAccounts.some((account) => account.id === current)
          ? current
          : nextAccounts.find((account) => account.status === "active")?.id ?? ""
      ));
    } catch (error) {
      toast({ message: String(error), variant: "error" });
    } finally {
      setLoading(false);
    }
  }, [toast, wsId]);

  useEffect(() => {
    void load();
  }, [load]);

  const selectedAccount = useMemo(
    () => accounts.find((account) => account.id === selectedAccountId),
    [accounts, selectedAccountId],
  );

  const addAccount = async () => {
    if (!accountId.trim()) return;
    setSaving(true);
    try {
      await connectors.createAccount({
        provider,
        provider_account_id: accountId.trim(),
        display_name: accountName.trim() || undefined,
        auth_type: credential ? "token" : "oauth",
        credential: credential || undefined,
      });
      setAccountId("");
      setAccountName("");
      setCredential("");
      await load();
      toast({ message: zh ? "Connector 帳號已新增" : "Connector account added", variant: "success" });
    } catch (error) {
      toast({ message: String(error), variant: "error" });
    } finally {
      setSaving(false);
    }
  };

  const addBinding = async () => {
    if (!selectedAccount || !containerId.trim()) return;
    setSaving(true);
    try {
      await connectors.createBinding(wsId, {
        connector_account_id: selectedAccount.id,
        external_container_type: CONTAINER_TYPES[selectedAccount.provider],
        external_container_id: containerId.trim(),
        external_container_name: containerName.trim() || undefined,
        sync_direction: direction,
      });
      setContainerId("");
      setContainerName("");
      await load();
      toast({ message: zh ? "Workspace 綁定已建立" : "Workspace binding created", variant: "success" });
    } catch (error) {
      toast({ message: String(error), variant: "error" });
    } finally {
      setSaving(false);
    }
  };

  const removeAccount = async (account: ConnectorAccount) => {
    const accepted = await confirm({
      title: zh ? "撤銷 Connector 帳號？" : "Revoke connector account?",
      message: account.display_name || account.provider_account_id,
      confirmLabel: zh ? "撤銷" : "Revoke",
      variant: "danger",
    });
    if (!accepted) return;
    await connectors.revokeAccount(account.id);
    await load();
  };

  const removeBinding = async (binding: ConnectorBinding) => {
    const accepted = await confirm({
      title: zh ? "刪除 Workspace 綁定？" : "Delete workspace binding?",
      message: binding.external_container_name || binding.external_container_id,
      confirmLabel: zh ? "刪除" : "Delete",
      variant: "danger",
    });
    if (!accepted) return;
    await connectors.deleteBinding(wsId, binding.id);
    await load();
  };

  const toggleBinding = async (binding: ConnectorBinding) => {
    await connectors.updateBinding(wsId, binding.id, { enabled: !binding.enabled });
    await load();
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <Card>
        <div style={{ padding: 20, display: "flex", flexDirection: "column", gap: 14 }}>
          <div>
            <h3 style={{ margin: 0, fontSize: 14 }}>{zh ? "個人 Connector 帳號" : "Personal connector accounts"}</h3>
            <p style={{ margin: "6px 0 0", color: "var(--text-muted)", fontSize: 12 }}>
              {zh ? "帳號與憑證屬於個人；同一帳號可明確綁定多個知識庫。" : "Accounts and credentials are personal; bindings to each knowledge base are explicit."}
            </p>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 10 }}>
            <select value={provider} onChange={(event) => setProvider(event.target.value as ConnectorProvider)} className="input">
              {PROVIDERS.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
            </select>
            <Input value={accountId} onChange={(event) => setAccountId(event.target.value)} placeholder={zh ? "外部帳號 ID / email" : "External account ID / email"} />
            <Input value={accountName} onChange={(event) => setAccountName(event.target.value)} placeholder={zh ? "顯示名稱（選填）" : "Display name (optional)"} />
            <Input type="password" value={credential} onChange={(event) => setCredential(event.target.value)} placeholder={zh ? "Token（OAuth 可留空）" : "Token (leave blank for OAuth)"} />
          </div>
          <Button onClick={addAccount} loading={saving} disabled={!accountId.trim()} leftIcon={<Plus size={14} />}>
            {zh ? "新增帳號" : "Add account"}
          </Button>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {accounts.map((account) => (
              <div key={account.id} style={{ display: "flex", alignItems: "center", gap: 12, padding: 12, border: "1px solid var(--border-default)", borderRadius: 8 }}>
                <Link2 size={16} color="var(--color-primary)" />
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, fontSize: 13 }}>{PROVIDERS.find((item) => item.value === account.provider)?.label} · {account.display_name || account.provider_account_id}</div>
                  <div style={{ fontSize: 11, color: "var(--text-muted)" }}>{account.status} · {account.auth_type}</div>
                </div>
                {account.status === "active" && <Button variant="secondary" onClick={() => void removeAccount(account)} leftIcon={<Trash2 size={14} />} />}
              </div>
            ))}
            {!loading && accounts.length === 0 && <div style={{ color: "var(--text-muted)", fontSize: 12 }}>{zh ? "尚未新增 Connector 帳號。" : "No connector accounts yet."}</div>}
          </div>
        </div>
      </Card>

      <Card>
        <div style={{ padding: 20, display: "flex", flexDirection: "column", gap: 14 }}>
          <div>
            <h3 style={{ margin: 0, fontSize: 14 }}>{zh ? "Workspace 綁定" : "Workspace bindings"}</h3>
            <p style={{ margin: "6px 0 0", color: "var(--text-muted)", fontSize: 12 }}>
              {zh ? "每個綁定指定外部資料範圍與同步方向，避免不同知識庫意外混用。" : "Each binding defines its external scope and sync direction to prevent accidental cross-KB mixing."}
            </p>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 10 }}>
            <select value={selectedAccountId} onChange={(event) => setSelectedAccountId(event.target.value)} className="input">
              <option value="">{zh ? "選擇帳號" : "Select account"}</option>
              {accounts.filter((account) => account.status === "active").map((account) => (
                <option key={account.id} value={account.id}>{account.display_name || account.provider_account_id}</option>
              ))}
            </select>
            <Input value={containerId} onChange={(event) => setContainerId(event.target.value)} placeholder={selectedAccount ? CONTAINER_LABELS[selectedAccount.provider] : (zh ? "外部容器 ID" : "External container ID")} />
            <Input value={containerName} onChange={(event) => setContainerName(event.target.value)} placeholder={zh ? "容器名稱（選填）" : "Container name (optional)"} />
            <select value={direction} onChange={(event) => setDirection(event.target.value as ConnectorDirection)} className="input">
              <option value="inbound">{zh ? "匯入 MemTrace" : "Inbound"}</option>
              <option value="outbound">{zh ? "匯出至外部" : "Outbound"}</option>
              <option value="bidirectional">{zh ? "雙向同步" : "Bidirectional"}</option>
            </select>
          </div>
          <Button onClick={addBinding} loading={saving} disabled={!selectedAccountId || !containerId.trim()} leftIcon={<Plus size={14} />}>
            {zh ? "建立綁定" : "Create binding"}
          </Button>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {bindings.map((binding) => (
              <div key={binding.id} style={{ display: "flex", alignItems: "center", gap: 12, padding: 12, border: "1px solid var(--border-default)", borderRadius: 8, opacity: binding.enabled ? 1 : 0.6 }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, fontSize: 13 }}>{binding.external_container_name || binding.external_container_id}</div>
                  <div style={{ fontSize: 11, color: "var(--text-muted)" }}>{binding.provider} · {binding.sync_direction} · {binding.account_display_name || binding.provider_account_id}</div>
                </div>
                <Button variant="secondary" onClick={() => void toggleBinding(binding)} leftIcon={binding.enabled ? <Pause size={14} /> : <Play size={14} />} />
                <Button variant="secondary" onClick={() => void removeBinding(binding)} leftIcon={<Trash2 size={14} />} />
              </div>
            ))}
            {!loading && bindings.length === 0 && <div style={{ color: "var(--text-muted)", fontSize: 12 }}>{zh ? "此 Workspace 尚未建立外部綁定。" : "No external bindings for this workspace."}</div>}
          </div>
        </div>
      </Card>
    </div>
  );
}
