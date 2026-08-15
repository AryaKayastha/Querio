import styles from "./RecentChatItem.module.css";

const RecentChatItem = ({ title, isActive, onSelect }) => {
  return (
    <button
      type="button"
      className={`${styles.item} ${isActive ? styles.active : ""}`}
      onClick={onSelect}
      title={title}
    >
      {title}
    </button>
  );
};

export default RecentChatItem;
