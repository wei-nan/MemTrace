import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Users, Trash2, UserPlus, Clock, ExternalLink } from 'lucide-react';
import { workspaces, type Member, type Invite, type JoinRequest, type Workspace } from './api';
import { useModal } from './components/ModalContext';
import KbExportPanel from './components/KbExportPanel';

export default function WorkspaceSettings({ wsId }: { wsId: string }) {
  const { i18n } = useTranslation();
  const zh = i18n.language === 'zh-TW';
  const { confirm, toast } = useModal();

  const [sending, setSending] = useState(false);
  const [ws, setWs] = useState<Workspace | null>(null);
  const [joinRequests, setJoinRequests] = useState<JoinRequest[]>([]);

  const [members, setMembers] = useState<Member[]>([]);
  const [invites, setInvites] = useState<Invite[]>([]);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('viewer');
  const [associations, setAssociations] = useState<any[]>([]);
  const [assocTargetId, setAssocTargetId] = useState('');
  const [tab, setTab] = useState<'members' | 'export' | 'assoc'>('members');

  const loadData = async () => {
    try {
      const [m, i, w, reqs, as] = await Promise.all([
        workspaces.members(wsId),
        workspaces.invites(wsId),
        workspaces.get(wsId),
        workspaces.joinRequests(wsId),
        workspaces.listAssociations(wsId),
      ]);
      setMembers(m);
      setInvites(i);
      setWs(w);
      setJoinRequests(reqs);
      setAssociations(as);
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

  const handleUpdateVisibility = async (vis: string) => {
    try {
      // Assuming a hypothetical update method exists or we use create with patch logic
      // Actually, we need an updateWorkspace method in api.ts? 
      // Let's check api.ts if it has one. (It doesn't yet).
      // I'll skip the actual update for a second or add it.
    } catch (e) {}
  };

  return (
    <div style={{ padding: '0 20px', display: 'flex', flexDirection: 'column', gap: 24 }}>
      {/* Tabs */}
      <div style={{ display: 'flex', gap: 20, borderBottom: '1px solid var(--border-subtle)', marginBottom: 8 }}>
        <button 
          onClick={() => setTab('members')}
          style={{ 
            padding: '12px 4px', background: 'none', border: 'none', cursor: 'pointer',
            fontSize: 14, fontWeight: 600, color: tab === 'members' ? 'var(--color-primary)' : 'var(--text-muted)',
            borderBottom: tab === 'members' ? '2px solid var(--color-primary)' : '2px solid transparent'
          }}
        >
          {zh ? '成員與權限' : 'Members & Access'}
        </button>
        <button 
          onClick={() => setTab('export')}
          style={{ 
            padding: '12px 4px', background: 'none', border: 'none', cursor: 'pointer',
            fontSize: 14, fontWeight: 600, color: tab === 'export' ? 'var(--color-primary)' : 'var(--text-muted)',
            borderBottom: tab === 'export' ? '2px solid var(--color-primary)' : '2px solid transparent'
          }}
        >
          {zh ? '資料匯出' : 'Data Export'}
        </button>
        <button 
          onClick={() => setTab('assoc')}
          style={{ 
            padding: '12px 4px', background: 'none', border: 'none', cursor: 'pointer',
            fontSize: 14, fontWeight: 600, color: tab === 'assoc' ? 'var(--color-primary)' : 'var(--text-muted)',
            borderBottom: tab === 'assoc' ? '2px solid var(--color-primary)' : '2px solid transparent'
          }}
        >
          {zh ? '館際關聯' : 'KB Associations'}
        </button>
      </div>

      {tab === 'assoc' ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          <section>
            <h3 style={{ fontSize: 16, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
              <ExternalLink size={18} style={{ color: 'var(--color-primary)' }} />
              {zh ? '新增跨庫關聯' : 'Add KB Association'}
            </h3>
            <div style={{ display: 'flex', gap: 10, background: 'var(--bg-surface)', padding: 16, borderRadius: 12, border: '1px solid var(--border-default)' }}>
              <input 
                className="mt-input" 
                placeholder={zh ? "輸入另一個 KB 的 ID" : "Paste target KB ID"} 
                value={assocTargetId} 
                onChange={e => setAssocTargetId(e.target.value)}
                style={{ flex: 1 }}
              />
              <button 
                className="btn-primary" 
                onClick={async () => {
                   try {
                     await workspaces.createAssociation(wsId, assocTargetId);
                     setAssocTargetId('');
                     loadData();
                     toast({ message: zh ? '關聯已建立' : 'Association created', variant: 'success' });
                   } catch (e: any) {
                     toast({ message: e.message, variant: 'error' });
                   }
                }}
              >
                {zh ? '建立關聯' : 'Associate'}
              </button>
            </div>
          </section>

          <section>
             <h3 style={{ fontSize: 14, color: 'var(--text-muted)', marginBottom: 12 }}>
                {zh ? '已關聯的知識庫' : 'Associated Libraries'}
             </h3>
             <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {associations.map(a => (
                  <div key={a.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 16px', background: 'var(--bg-surface)', border: '1px solid var(--border-default)', borderRadius: 12 }}>
                     <div>
                        <div style={{ fontSize: 14, fontWeight: 500 }}>{zh ? a.target_name_zh : a.target_name_en}</div>
                        <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>ID: {a.target_ws_id}</div>
                     </div>
                     <button 
                       onClick={async () => {
                         await workspaces.deleteAssociation(wsId, a.target_ws_id);
                         loadData();
                       }}
                       style={{ background: 'none', border: 'none', color: 'var(--error-color)', cursor: 'pointer' }}
                     >
                       <Trash2 size={16} />
                     </button>
                  </div>
                ))}
             </div>
          </section>
        </div>
      ) : tab === 'export' ? (
        <KbExportPanel wsId={wsId} zh={zh} />
      ) : (
        <>
          {/* Visibility Settings */}
      <section>
        <h3 style={{ fontSize: 16, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
          <Clock size={18} style={{ color: 'var(--color-primary)' }} />
          {zh ? '隱私設定' : 'Visibility Settings'}
        </h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12, background: 'var(--bg-surface)', padding: 16, borderRadius: 12, border: '1px solid var(--border-default)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <div style={{ fontSize: 14, fontWeight: 500 }}>{zh ? '公開程度' : 'Visibility'}</div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{zh ? '控制誰可以看到此知識庫' : 'Control who can access this workspace'}</div>
            </div>
            <select 
               className="mt-input" 
               value={ws?.visibility ?? 'private'} 
               style={{ width: 160 }}
               onChange={async (e) => {
                 try {
                   await workspaces.update(wsId, { visibility: e.target.value });
                   loadData();
                   toast({ message: zh ? '隱私設定已更新' : 'Visibility updated', variant: 'success' });
                 } catch (err: any) {
                   toast({ message: err.message, variant: 'error' });
                 }
               }}
            >
              <option value="private">{zh ? '私有 (Private)' : 'Private'}</option>
              <option value="restricted">{zh ? '限定 (Restricted)' : 'Restricted'}</option>
              <option value="conditional_public">{zh ? '有條件公開 (Conditional)' : 'Conditional Public'}</option>
              <option value="public">{zh ? '公開 (Public)' : 'Public'}</option>
            </select>
          </div>
        </div>
      </section>

      {/* Join Requests */}
      {joinRequests.length > 0 && (
      <section>
        <h3 style={{ fontSize: 16, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
          <UserPlus size={18} style={{ color: 'var(--color-primary)' }} />
          {zh ? '加入申請' : 'Join Requests'}
        </h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {joinRequests.map(req => (
            <div key={req.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 16px', background: 'var(--bg-surface)', border: '1px solid var(--border-default)', borderRadius: 12 }}>
              <div>
                <div style={{ fontSize: 14, fontWeight: 500 }}>User: {req.user_id}</div>
                {req.message && <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>"{req.message}"</div>}
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <button 
                  className="btn-secondary" 
                  style={{ padding: '4px 12px', fontSize: 12 }}
                  onClick={async () => {
                    await workspaces.rejectJoinRequest(wsId, req.id);
                    loadData();
                  }}
                >
                  {zh ? '拒絕' : 'Reject'}
                </button>
                <button 
                  className="btn-primary" 
                  style={{ padding: '4px 12px', fontSize: 12 }}
                  onClick={async () => {
                    await workspaces.approveJoinRequest(wsId, req.id);
                    loadData();
                  }}
                >
                  {zh ? '核准' : 'Approve'}
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>
      )}

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
        </>
      )}
    </div>
  );
}
