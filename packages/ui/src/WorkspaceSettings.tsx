import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Users, Trash2, UserPlus, Clock } from 'lucide-react';
import { workspaces, type Member, type Invite } from './api';
import { useModal } from './components/ModalContext';

export default function WorkspaceSettings({ wsId }: { wsId: string }) {
  const { i18n } = useTranslation();
  const zh = i18n.language === 'zh-TW';
  const { confirm, toast } = useModal();

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
      toast({ message: zh ? '邀請已送出' : 'Invite sent', variant: 'success' });
    } catch (e: any) {
      toast({ message: e.message, variant: 'error' });
    } finally { setSending(false); }
  };

  const handleDeleteInvite = async (id: string) => {
    const ok = await confirm({
      title: zh ? '撤回邀請' : 'Revoke Invite',
      message: zh ? '確定要撤回此邀請？' : 'Revoke this invite?',
      variant: 'warning',
      confirmLabel: zh ? '撤回' : 'Revoke',
    });
    if (!ok) return;
    try {
      await workspaces.deleteInvite(id);
      loadData();
      toast({ message: zh ? '邀請已撤回' : 'Invite revoked', variant: 'info' });
    } catch (e: any) {
      toast({ message: e.message, variant: 'error' });
    }
  };

  const handleUpdateRole = async (userId: string, role: string) => {
    try {
      await workspaces.updateMember(wsId, userId, role);
      loadData();
      toast({ message: zh ? '角色已更新' : 'Role updated', variant: 'success' });
    } catch (e: any) {
      toast({ message: e.message, variant: 'error' });
    }
  };

  const handleRemoveMember = async (userId: string) => {
    const ok = await confirm({
      title: zh ? '移除成員' : 'Remove Member',
      message: zh ? '確定要移除此成員？移除後將失去工作區存取權。' : 'Remove this member? They will lose access to the workspace.',
      variant: 'danger',
      confirmLabel: zh ? '移除' : 'Remove',
    });
    if (!ok) return;
    try {
      await workspaces.removeMember(wsId, userId);
      loadData();
      toast({ message: zh ? '成員已移除' : 'Member removed', variant: 'info' });
    } catch (e: any) {
      toast({ message: e.message, variant: 'error' });
    }
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
