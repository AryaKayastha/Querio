import styles from "./StatusPill.module.css";

const StatusPill = ({ label = "Bot online", status = "online" }) => {
  return <span className={`${styles.pill} ${styles[status]}`}>● {label}</span>;
};

export default StatusPill;
