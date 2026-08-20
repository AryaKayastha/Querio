import { ChatBubbleIcon, CloseIcon } from "../../assets/icons/index.js";
import styles from "./WidgetBubble.module.css";

const WidgetBubble = ({ isOpen, hasUnread, onToggle }) => {
  return (
    <button
      type="button"
      className={styles.bubble}
      onClick={onToggle}
      aria-label={isOpen ? "Close chat widget" : "Open chat widget"}
    >
      {isOpen ? <CloseIcon size={20} /> : <ChatBubbleIcon size={22} />}

      {!isOpen && hasUnread && <span className={styles.notificationDot} />}
    </button>
  );
};

export default WidgetBubble;
