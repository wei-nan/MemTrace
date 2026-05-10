import { useState, useEffect } from 'react';
import { HardDrive } from 'lucide-react';
import { system } from '../api';
import { useModal } from './ModalContext';

const SCHEDULE_OPTIONS = [
  { value: 1,   labelZh: '每小時',    labelEn: 'Hourly' },
  { value: 6,   labelZh: '每 6 小時', labelEn: 'Every 6 hours' },
  { value: 12,  labelZh: '每 12 小時',labelEn: 'Every 12 hours' },
  { value: 24,  labelZh: '每天',      labelEn: 'Daily' },
  { value: 168, labelZh: '每週',      labelEn: 'Weekly' },
];

export default function BackupSettings({ zh }: { zh: boolean }) {
  const { toast } = useModal();
  const [enabled, setEnabled] = useState(false);
  const [path, setPath] = useState('/backups');
  const [intervalHours, setIntervalHours] = useState(24);
  const [keepCount, setKeepCount] = useState(7);
  const [saving, setSaving] = useState(false);
  const [running, setRunning] = useState(false);

  const load = async () => {
    try {
      const c = await system.getBackupConfig();
      setEnabled(c.enabled);
      setPath(c.path);
      setIntervalHours(c.interval_hours);
      setKeepCount(c.keep_count);
    } catch { }
  };

  useEffect(() => { load(); }, []);

  const save = async () => {
    setSaving(true);
    try {
      await system.updateBackupConfig({ enabled, path, interval_hours: intervalHours, keep_count: keepCount });
      toast({ message: zh ? '備份設定已儲存' : 'Backup settings saved', variant: 'success' });
      await load();
    } catch (e) {
      toast({ message: e instanceof Error ? e.message : String(e), variant: 'error' });
    } finally {
      setSaving(false);
    }
  };

  const runNow = async () => {
    setRunning(true);
    try {
      await system.runBackup();
      toast({ message: zh ? '備份已啟動，稍後查看狀態' : 'Backup started — check status shortly', variant: 'success' });
      setTimeout(load, 4000);
    } catch (e) {
      toast({ message: e instanceof Error ? e.message : String(e), variant: 'error' });
    } finally {
      setRunning(false);
    }
  };



  return (
    <section style={{ marginBottom: 40 }}>
      <h3 style={{ fontSize: 15, marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
        <HardDrive size={16} style={{ color: 'var(--color-primary)' }} />
        {zh ? '資料備份' : 'Data Backup'}
      </h3>
      <div style={{
        background: 'var(--bg-surface)', border: '1px solid var(--border-default)',
        borderRadius: 12, padding: 20, display: 'flex', flexDirection: 'column', gap: 16,
      }}>
        <label style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: 14 }}>{zh ? '啟用自動備份' : 'Enable automatic backup'}</span>
          <input type="checkbox" checked={enabled} onChange={e => setEnabled(e.target.checked)} />
        </label>

        <div>
          <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
            {zh ? '備份路徑（伺服器本機絕對路徑）' : 'Backup path (absolute path on server)'}
          </label>
          <input className="mt-input" value={path} onChange={e => setPath(e.target.value)} placeholder="/backups" />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 12 }}>
          <div>
            <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
              {zh ? '備份週期' : 'Backup interval'}
            </label>
            <select
              className="mt-input"
              value={intervalHours}
              onChange={e => setIntervalHours(Number(e.target.value))}
            >
              {SCHEDULE_OPTIONS.map(o => (
                <option key={o.value} value={o.value}>{zh ? o.labelZh : o.labelEn}</option>
              ))}
            </select>
          </div>
          <div>
            <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
              {zh ? '保留數量' : 'Keep last N'}
            </label>
            <input
              className="mt-input"
              type="number" min={1} max={30} value={keepCount}
              onChange={e => setKeepCount(Math.max(1, Number(e.target.value)))}
              style={{ width: 72 }}
            />
          </div>
        </div>

        <div style={{ display: 'flex', gap: 10 }}>
          <button className="btn-primary" onClick={save} disabled={saving}>
            {saving ? (zh ? '儲存中…' : 'Saving…') : (zh ? '儲存設定' : 'Save Settings')}
          </button>
          <button className="btn-secondary" onClick={runNow} disabled={running}>
            {running ? (zh ? '備份中…' : 'Running…') : (zh ? '立即備份' : 'Backup Now')}
          </button>
        </div>
      </div>
    </section>
  );
}
