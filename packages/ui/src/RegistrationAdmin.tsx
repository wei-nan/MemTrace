import { useEffect, useState } from "react";
import { UserPlus, Check, X, Clock, Mail } from "lucide-react";
import { system } from "./api";
import { useModal } from "./components/ModalContext";

interface Props {
  zh: boolean;
}

export default function RegistrationAdmin({ zh }: Props) {
  const { toast } = useModal();
  const [registrations, setRegistrations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>("pending");

  const load = async () => {
    setLoading(true);
    try {
      const data = await system.registrations(filter);
      setRegistrations(data);
    } catch (e) {
      toast({ message: String(e), variant: "error" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [filter]);

  const handleApprove = async (id: string) => {
    try {
      await system.approveRegistration(id);
      toast({ message: zh ? "已核准申請" : "Registration approved", variant: "success" });
      load();
    } catch (e) {
      toast({ message: String(e), variant: "error" });
    }
  };

  const handleReject = async (id: string) => {
    try {
      await system.rejectRegistration(id);
      toast({ message: zh ? "已拒絕申請" : "Registration rejected", variant: "success" });
      load();
    } catch (e) {
      toast({ message: String(e), variant: "error" });
    }
  };

  return (
    <section style={{ marginBottom: 40 }}>
      <h3 style={{ fontSize: 15, marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
        <UserPlus size={16} style={{ color: "var(--color-primary)" }} />
        {zh ? "註冊申請管理" : "Registration Management"}
      </h3>

      <div style={{ display: "flex", gap: 10, marginBottom: 16 }}>
        {["pending", "approved", "rejected", ""].map((f) => (
          <button
            key={f}
            className={`tag ${filter === f ? "tag-active" : ""}`}
            onClick={() => setFilter(f)}
          >
            {f === "pending" ? (zh ? "待審核" : "Pending") :
             f === "approved" ? (zh ? "已通過" : "Approved") :
             f === "rejected" ? (zh ? "已拒絕" : "Rejected") :
             (zh ? "全部" : "All")}
          </button>
        ))}
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {registrations.map((reg) => (
          <div
            key={reg.id}
            style={{
              background: "var(--bg-surface)",
              border: "1px solid var(--border-default)",
              borderRadius: 12,
              padding: "16px 20px",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              animation: "fade-in 0.3s ease-out"
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
              <div style={{ 
                width: 40, height: 40, borderRadius: 10, background: "var(--bg-app)", 
                display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-muted)" 
              }}>
                <Mail size={18} />
              </div>
              <div>
                <div style={{ fontWeight: 600, fontSize: 14 }}>{reg.email}</div>
                <div style={{ fontSize: 12, color: "var(--text-muted)", display: "flex", alignItems: "center", gap: 6 }}>
                  <Clock size={12} />
                  {new Date(reg.created_at).toLocaleString()}
                </div>
                {reg.purpose_note && (
                  <div style={{ 
                    marginTop: 8, padding: "6px 10px", background: "var(--bg-app)", 
                    borderRadius: 6, fontSize: 12, color: "var(--text-secondary)",
                    borderLeft: "2px solid var(--color-primary-subtle)"
                  }}>
                    {reg.purpose_note}
                  </div>
                )}
              </div>
            </div>

            {reg.status === "pending" ? (
              <div style={{ display: "flex", gap: 10 }}>
                <button
                  className="btn-primary"
                  onClick={() => handleApprove(reg.id)}
                  style={{ padding: "6px 14px", height: 32, fontSize: 13, background: "#10b981", border: "none" }}
                >
                  <Check size={14} style={{ marginRight: 6 }} /> {zh ? "核准" : "Approve"}
                </button>
                <button
                  className="btn-secondary"
                  onClick={() => handleReject(reg.id)}
                  style={{ padding: "6px 14px", height: 32, fontSize: 13, color: "#ef4444" }}
                >
                  <X size={14} style={{ marginRight: 6 }} /> {zh ? "拒絕" : "Reject"}
                </button>
              </div>
            ) : (
              <div style={{ 
                fontSize: 12, fontWeight: 600, padding: "4px 10px", borderRadius: 8,
                background: reg.status === "approved" ? "rgba(16, 185, 129, 0.1)" : "rgba(239, 68, 68, 0.1)",
                color: reg.status === "approved" ? "#10b981" : "#ef4444"
              }}>
                {reg.status.toUpperCase()}
              </div>
            )}
          </div>
        ))}
        {!loading && registrations.length === 0 && (
          <div style={{ padding: 40, textAlign: "center", color: "var(--text-muted)", fontSize: 14 }}>
            {zh ? "目前無註冊申請" : "No registration requests found"}
          </div>
        )}
      </div>
    </section>
  );
}
