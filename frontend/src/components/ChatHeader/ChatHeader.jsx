import { useEffect, useState } from "react";
import StatusPill from "../StatusPill/StatusPill.jsx";
import { getHealthStatus } from "../../api/backend.js";
import styles from "./ChatHeader.module.css";

const STATUS_POLL_MS = 30_000;

const HEALTH_LABELS = {
  online: "Bot online",
  degraded: "Chatbot unavailable",
  offline: "Bot offline",
};

const ChatHeader = ({ title, subtitle }) => {
  const [health, setHealth] = useState({ label: "Checking…", status: "degraded" });

  useEffect(() => {
    let cancelled = false;

    const refreshHealth = async () => {
      const status = await getHealthStatus();
      if (cancelled) {
        return;
      }

      setHealth({
        status,
        label: HEALTH_LABELS[status] || HEALTH_LABELS.offline,
      });
    };

    refreshHealth();
    const intervalId = window.setInterval(refreshHealth, STATUS_POLL_MS);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, []);

  return (
    <div className={styles.header}>
      <div className={styles.titleBlock}>
        <div className={styles.title}>{title}</div>
        <div className={styles.subtitle}>{subtitle}</div>
      </div>

      <StatusPill label={health.label} status={health.status} />
    </div>
  );
};

export default ChatHeader;
