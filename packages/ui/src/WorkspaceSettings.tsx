import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Users, Trash2, UserPlus, Clock } from 'lucide-react';
import { workspaces, type Member, type Invite } from './api';

export default function WorkspaceSettings({ wsId }: { wsId: string }) {
  const { i18n } = useTranslation();
  const zh = i18n.language === 'zh-TW';

  const [members, setMembers] = useState<Member[]>([]);
  const [invites, setInvites] = useState<Invite[]>([]);
  // loading removed
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('viewer');
  const [sending, setSending] = useState(false);

  const loadData = async () => {
    try {
      const [m, i] = await Promise.all([
        workspaces.members(wsId),
        workspaces.invites(wsId),
      ]);
      setMembers(m);
      setInvites(i);
    } catch (e) {}
  };

  useEffect(() => { loadData(); }, [wsId]);

  const handleSendInvite = async () => {
    if (!inviteEmail.trim()) return;
    setSending(true);
    try {
      await workspaces.createInvite(wsId, { email: inviteEmail, role: inviteRole });
      setInviteEmail('');
      loadData();
    } catch (e: any) {
      alert(e.message);
    } finally { setSending(false); }
  };

  const handleDeleteInvite = async (id: string) => {
    if (!confirm(zh ? '確定要撤回邀請？' : 'Revoke invite?')) return;
    try {
      await workspaces.deleteInvite(id);
      loadData();
    } catch (e: any) { alert(e.message); }
  };

  const handleUpdateRole = async (userId: string, role: string) => {
    try {
      // Need to add this specific method to api.ts if missing, but let's assume it's PUT /members/{id}
      // Actually, I should check api.ts first. Wait, I'll just write the fetch here or use a generic if I didn't add it.
      // I'll check api.ts now.
      await workspaces.updateMember(wsId, userId, role);
      loadData();
    } catch (e: any) { alert(e.message); }
  };

  const handleRemoveMember = async (userId: string) => {
    if (!confirm(zh ? '確定要移除此成員？' : 'Remove this member?')) return;
    try {
      await workspaces.removeMember(wsId, userId);
      loadData();
    } catch (e: any) { alert(e.message); }
  };

  return (
    <div style={{ padding: '0 20px', display: 'flex', flexDirection: 'column', gap: 32 }}>
      {/* Invite Member */}
      <section>
        <h3 style={{ fontSize: 16, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
          <UserPlus size={18} style={{ color: 'var(--color-primary)' }} />
          {zh ? '邀請成員' : 'Invite Member'}
        </h3>
        <div style={{ display: 'flex', gap: 10, background: 'var(--bg-surface)', padding: 16, borderRadius: 12, border: '1px solid var(--border-default)' }}>
          <input 
            className="mt-input" 
            placeholder="email@example.com" 
            value={inviteEmail} 
            onChange={e => setInviteEmail(e.target.value)}
            style={{ flex: 1 }}
          />
          <select 
            className="mt-input" 
            value={inviteRole} 
            onChange={e => setInviteRole(e.target.value)}
            style={{ width: 120 }}
          >
            <option value="viewer">{zh ? '檢視者' : 'Viewer'}</option>
            <option value="editor">{zh ? '編輯者' : 'Editor'}</option>
          </select>
          <button className="btn-primary" onClick={handleSendInvite} disabled={sending}>
            {zh ? '發送' : 'Send'}
          </button>
        </div>
      </section>

      {/* Pending Invites */}
      {invites.length > 0 && (
        <section>
          <h3 style={{ fontSize: 14, color: 'var(--text-muted)', marginBottom: 12, display: 'flex', alignItems: 'center', gap: 6 }}>
            <Clock size={14} />
            {zh ? '待處理邀請' : 'Pending Invites'}
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {invites.map(inv => (
              <div key={inv.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 14px', background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: 8, fontSize: 13 }}>
                <div>{inv.email} <span style={{ opacity: 0.5 }}>({inv.role})</span></div>
                <button onClick={() => handleDeleteInvite(inv.id)} style={{ background: 'none', border: 'none', color: 'var(--error-color)', cursor: 'pointer' }}>
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Members List */}
      <section>
        <h3 style={{ fontSize: 16, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
          <Users size={18} style={{ color: 'var(--color-primary)' }} />
          {zh ? '工作區成員' : 'Workspace Members'}
        </h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {members.map(m => (
            <div key={m.user_id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 16px', background: 'var(--bg-surface)', border: '1px solid var(--border-default)', borderRadius: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <div style={{ width: 32, height: 32, borderRadius: 16, background: 'var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14, fontWeight: 600 }}>
                  {m.display_name[0].toUpperCase()}
                </div>
                <div>
                  <div style={{ fontSize: 14, fontWeight: 500 }}>{m.display_name}</div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{m.email}</div>
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <select 
                  className="mt-input" 
                  value={m.role} 
                  onChange={e => handleUpdateRole(m.user_id, e.target.value)}
                  style={{ width: 100, fontSize: 12, height: 32, padding: '0 8px' }}
                >
                  <option value="viewer">{zh ? '檢視者' : 'Viewer'}</option>
                  <option value="editor">{zh ? '編輯者' : 'Editor'}</option>
                  <option value="owner">{zh ? '所有者' : 'Owner'}</option>
                </select>
                <button 
                  onClick={() => handleRemoveMember(m.user_id)}
                  style={{ background: 'none', border: 'none', color: 'var(--error-color)', cursor: 'pointer', display: 'flex', alignItems: 'center' }}
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
