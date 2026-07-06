import { useEffect, useState } from 'react';
import { RefreshCw, Search, ShieldCheck, ShieldOff, Users } from 'lucide-react';
import { system, type SystemUser } from './api';
import { useModal } from './components/ModalContext';
import { Button, Card } from './components/ui';

const PAGE_SIZE = 50;

function fmtDate(value?: string | null) {
  if (!value) return '-';
  return new Date(value).toLocaleString();
}

export default function SystemUsersPage() {
  const { toast, confirm } = useModal();
  const [users, setUsers] = useState<SystemUser[]>([]);
  const [q, setQ] = useState('');
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [busyUser, setBusyUser] = useState<string | null>(null);

  const loadUsers = async (nextOffset = offset) => {
    setLoading(true);
    try {
      const page = await system.users({ q: q.trim() || undefined, limit: PAGE_SIZE, offset: nextOffset });
      setUsers(page.users);
      setTotal(page.total);
      setOffset(page.offset);
    } catch (e) {
      toast({ message: e instanceof Error ? e.message : String(e), variant: 'error' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadUsers(0);
  }, []);

  const toggleAdmin = async (user: SystemUser) => {
    const ok = await confirm({
      title: user.is_platform_admin ? 'Remove platform admin?' : 'Grant platform admin?',
      message: user.email,
      variant: user.is_platform_admin ? 'warning' : 'info',
      confirmLabel: user.is_platform_admin ? 'Remove' : 'Grant',
    });
    if (!ok) return;
    setBusyUser(user.id);
    try {
      if (user.is_platform_admin) await system.demoteUser(user.id);
      else await system.promoteUser(user.id);
      await loadUsers(offset);
      toast({ message: 'User role updated', variant: 'success' });
    } catch (e) {
      toast({ message: e instanceof Error ? e.message : String(e), variant: 'error' });
    } finally {
      setBusyUser(null);
    }
  };

  const pageEnd = Math.min(offset + PAGE_SIZE, total);

  return (
    <div style={{ padding: '32px 24px', maxWidth: 1120, margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 16, marginBottom: 20 }}>
        <div>
          <h1 style={{ fontSize: 20, margin: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
            <Users size={20} /> System Users
          </h1>
          <div style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 6 }}>
            Review accounts, platform-admin status, and workspace participation.
          </div>
        </div>
        <Button variant="secondary" onClick={() => loadUsers(offset)} loading={loading} leftIcon={<RefreshCw size={14} />}>
          Refresh
        </Button>
      </div>

      <Card variant="surface" padding="md" style={{ border: '1px solid var(--border-default)', marginBottom: 16 }}>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            loadUsers(0);
          }}
          style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) auto', gap: 10 }}
        >
          <div style={{ position: 'relative' }}>
            <Search size={15} style={{ position: 'absolute', left: 12, top: 12, color: 'var(--text-muted)' }} />
            <input
              className="mt-input"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search email, name, or user id"
              style={{ width: '100%', paddingLeft: 36 }}
            />
          </div>
          <Button variant="primary" type="submit" leftIcon={<Search size={14} />}>
            Search
          </Button>
        </form>
      </Card>

      <div style={{ border: '1px solid var(--border-default)', borderRadius: 8, overflow: 'hidden', background: 'var(--bg-surface)' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(220px, 1.5fr) 110px 110px 170px 150px', gap: 12, padding: '10px 14px', fontSize: 12, fontWeight: 700, color: 'var(--text-muted)', background: 'var(--bg-elevated)' }}>
          <div>User</div>
          <div>Verified</div>
          <div>Workspaces</div>
          <div>Last Login</div>
          <div>Platform Admin</div>
        </div>
        {users.map((user) => (
          <div key={user.id} style={{ display: 'grid', gridTemplateColumns: 'minmax(220px, 1.5fr) 110px 110px 170px 150px', gap: 12, alignItems: 'center', padding: '12px 14px', borderTop: '1px solid var(--border-subtle)' }}>
            <div style={{ minWidth: 0 }}>
              <div style={{ fontWeight: 650, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{user.display_name}</div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{user.email}</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{user.id}</div>
            </div>
            <div>
              <span className="tag" style={{ background: user.email_verified ? 'var(--color-success-subtle)' : 'var(--bg-elevated)', color: user.email_verified ? 'var(--color-success)' : 'var(--text-muted)' }}>
                {user.email_verified ? 'Yes' : 'No'}
              </span>
            </div>
            <div style={{ fontWeight: 600 }}>{user.workspace_count}</div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{fmtDate(user.last_login_at)}</div>
            <Button
              variant={user.is_platform_admin ? 'secondary' : 'primary'}
              size="sm"
              loading={busyUser === user.id}
              onClick={() => toggleAdmin(user)}
              leftIcon={user.is_platform_admin ? <ShieldOff size={13} /> : <ShieldCheck size={13} />}
            >
              {user.is_platform_admin ? 'Demote' : 'Promote'}
            </Button>
          </div>
        ))}
        {!loading && users.length === 0 && (
          <div style={{ padding: 28, color: 'var(--text-muted)', textAlign: 'center' }}>
            No users found
          </div>
        )}
        {loading && users.length === 0 && (
          <div style={{ padding: 28, color: 'var(--text-muted)', display: 'flex', justifyContent: 'center' }}>
            <RefreshCw className="animate-spin" />
          </div>
        )}
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 14, color: 'var(--text-muted)', fontSize: 12 }}>
        <span>{total === 0 ? '0 / 0' : `${offset + 1}-${pageEnd} / ${total}`}</span>
        <div style={{ display: 'flex', gap: 8 }}>
          <Button variant="secondary" size="sm" disabled={offset === 0 || loading} onClick={() => loadUsers(Math.max(0, offset - PAGE_SIZE))}>
            Previous
          </Button>
          <Button variant="secondary" size="sm" disabled={pageEnd >= total || loading} onClick={() => loadUsers(offset + PAGE_SIZE)}>
            Next
          </Button>
        </div>
      </div>
    </div>
  );
}
