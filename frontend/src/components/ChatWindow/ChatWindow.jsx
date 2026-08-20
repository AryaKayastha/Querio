import { useEffect, useRef } from "react";
import MessageBubble from "../MessageBubble/MessageBubble.jsx";
import TypingIndicator from "../TypingIndicator/TypingIndicator.jsx";
import styles from "./ChatWindow.module.css";

const ChatWindow = ({ messages, isBotTyping, onChipSelect }) => {
  const bottomAnchorRef = useRef(null);

  useEffect(() => {
    if (bottomAnchorRef.current) {
      bottomAnchorRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isBotTyping]);

  return (
    <div className={styles.window}>
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} onChipSelect={onChipSelect} />
      ))}

      {isBotTyping && <TypingIndicator />}

      <div ref={bottomAnchorRef} />
    </div>
  );
};

export default ChatWindow;
