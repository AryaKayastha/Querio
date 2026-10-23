import { useState } from "react";
import { SendIcon } from "../../assets/icons/index.js";
import styles from "./ChatInput.module.css";

const ChatInput = ({ onSend, placeholder = "Type your question…", disabled = false }) => {
  const [textValue, setTextValue] = useState("");

  const handleSubmit = () => {
    const trimmedValue = textValue.trim();

    if (trimmedValue.length === 0 || disabled) {
      return;
    }

    onSend(trimmedValue);
    setTextValue("");
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className={styles.inputBar}>
      <input
        type="text"
        className={styles.textField}
        placeholder={placeholder}
        value={textValue}
        onChange={(event) => setTextValue(event.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled}
      />

      <button
        type="button"
        className={styles.sendButton}
        onClick={handleSubmit}
        disabled={textValue.trim().length === 0 || disabled}
        aria-label="Send message"
        title="Send message"
      >
        <SendIcon size={13} />
      </button>
    </div>
  );
};

export default ChatInput;
