import Avatar from "../Avatar/Avatar.jsx";
import QuickReplyChips from "../QuickReplyChips/QuickReplyChips.jsx";
import styles from "./MessageBubble.module.css";

const MessageBubble = ({ message, onChipSelect }) => {
  const isBot = message.sender === "bot";
  const hasChips = Boolean(message.chips && message.chips.length > 0);

  return (
    <div className={`${styles.messageRow} ${isBot ? "" : styles.user}`}>
      {isBot && <Avatar label="Q" size={24} />}

      <div className={styles.bubbleColumn}>
        <div className={`${styles.bubble} ${isBot ? styles.bot : styles.user}`}>
          {message.text}
        </div>

        {hasChips && (
          <QuickReplyChips chips={message.chips} onChipSelect={onChipSelect} />
        )}
      </div>
    </div>
  );
};

export default MessageBubble;
