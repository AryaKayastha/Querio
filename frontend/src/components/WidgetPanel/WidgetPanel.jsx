import { useState } from "react";
import Avatar from "../Avatar/Avatar.jsx";
import ChatWindow from "../ChatWindow/ChatWindow.jsx";
import ChatInput from "../ChatInput/ChatInput.jsx";
import { CloseIcon } from "../../assets/icons/index.js";
import { getBotReply } from "../../utils/getBotReply.js";
import { generateId } from "../../utils/generateId.js";
import styles from "./WidgetPanel.module.css";

const initialMessages = [
  {
    id: "widget-greeting",
    sender: "bot",
    text: "Hi 👋 How can I help you today?",
  },
];

const WidgetPanel = ({ onClose }) => {
  const [messages, setMessages] = useState(initialMessages);
  const [isBotTyping, setIsBotTyping] = useState(false);

  const respondToMessage = (userMessageText) => {
    setIsBotTyping(true);

    window.setTimeout(async () => {
      const botReply = await getBotReply(userMessageText);

      const botMessage = {
        id: generateId("bot-message"),
        sender: "bot",
        text: botReply.reply,
        sources: botReply.sources,
        chips: botReply.chips,
      };

      setMessages((previousMessages) => [...previousMessages, botMessage]);
      setIsBotTyping(false);
    }, 900);
  };

  const handleSend = (messageText) => {
    const userMessage = {
      id: generateId("user-message"),
      sender: "user",
      text: messageText,
    };

    setMessages((previousMessages) => [...previousMessages, userMessage]);
    respondToMessage(messageText);
  };

  return (
    <div className={styles.panel}>
      <div className={styles.panelHeader}>
        <div className={styles.headerLeft}>
          <Avatar label="Q" size={26} variant="gold" />
          <div>
            <div className={styles.botName}>Querio</div>
            <div className={styles.botStatus}>● Online now</div>
          </div>
        </div>

        <button
          type="button"
          className={styles.closeButton}
          onClick={onClose}
          aria-label="Close chat widget"
        >
          <CloseIcon size={18} />
        </button>
      </div>

      <ChatWindow messages={messages} isBotTyping={isBotTyping} onChipSelect={handleSend} />

      <div className={styles.inputWrapper}>
        <ChatInput onSend={handleSend} placeholder="Type a message…" />
      </div>
    </div>
  );
};

export default WidgetPanel;
