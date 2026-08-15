import { useRef, useState } from "react";
import { PaperclipIcon, MicIcon, SendIcon } from "../../assets/icons/index.js";
import styles from "./ChatInput.module.css";

const ChatInput = ({ onSend, placeholder = "Type your question…", disabled = false }) => {
  const [textValue, setTextValue] = useState("");
  const [isListening, setIsListening] = useState(false);
  const fileInputRef = useRef(null);

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

  const handleAttachClick = () => {
    fileInputRef.current.click();
  };

  const handleFileSelected = (event) => {
    const selectedFile = event.target.files[0];

    if (selectedFile) {
      setTextValue((previousValue) =>
        previousValue.length > 0
          ? `${previousValue} [attached: ${selectedFile.name}]`
          : `[attached: ${selectedFile.name}]`
      );
    }

    event.target.value = "";
  };

  const handleMicClick = () => {
    setIsListening(true);

    window.setTimeout(() => {
      setIsListening(false);
    }, 1500);
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

      <input
        type="file"
        ref={fileInputRef}
        style={{ display: "none" }}
        onChange={handleFileSelected}
      />

      <button
        type="button"
        className={styles.iconButton}
        onClick={handleAttachClick}
        aria-label="Attach a file"
        title="Attach a file"
      >
        <PaperclipIcon size={16} />
      </button>

      <button
        type="button"
        className={styles.iconButton}
        onClick={handleMicClick}
        aria-label="Use voice input"
        title="Use voice input"
        style={{ color: isListening ? "var(--color-highlight)" : undefined }}
      >
        <MicIcon size={16} />
      </button>

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
