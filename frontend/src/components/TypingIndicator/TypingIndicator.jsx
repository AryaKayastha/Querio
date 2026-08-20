import Avatar from "../Avatar/Avatar.jsx";
import styles from "./TypingIndicator.module.css";

const TypingIndicator = () => {
  return (
    <div className={styles.messageRow}>
      <Avatar label="Q" size={24} />
      <div className={styles.bubble}>
        <span className={styles.dot} />
        <span className={styles.dot} />
        <span className={styles.dot} />
      </div>
    </div>
  );
};

export default TypingIndicator;
