import StatusPill from "../StatusPill/StatusPill.jsx";
import styles from "./ChatHeader.module.css";

const ChatHeader = ({ title, subtitle }) => {
  return (
    <div className={styles.header}>
      <div className={styles.titleBlock}>
        <div className={styles.title}>{title}</div>
        <div className={styles.subtitle}>{subtitle}</div>
      </div>

      <StatusPill label="Bot online" status="online" />
    </div>
  );
};

export default ChatHeader;
