import { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import Sidebar from "../../components/Sidebar/Sidebar.jsx";
import ChatHeader from "../../components/ChatHeader/ChatHeader.jsx";
import ChatWindow from "../../components/ChatWindow/ChatWindow.jsx";
import ChatInput from "../../components/ChatInput/ChatInput.jsx";
import { greetingMessage } from "../../data/recentChats.js";
import { getBotReply } from "../../utils/getBotReply.js";
import { generateId } from "../../utils/generateId.js";
import styles from "./ChatPage.module.css";

const BOT_REPLY_DELAY_MS = 900;
const TITLE_MAX_LENGTH = 42;

const buildTitleFromMessage = (messageText) => {
  if (messageText.length <= TITLE_MAX_LENGTH) {
    return messageText;
  }

  return `${messageText.slice(0, TITLE_MAX_LENGTH)}…`;
};

const ChatPage = () => {
  const location = useLocation();
  const hasHandledInitialMessage = useRef(false);

  const [recentChats, setRecentChats] = useState([]);
  const [activeChatId, setActiveChatId] = useState(null);
  const [draftMessages, setDraftMessages] = useState([greetingMessage]);
  const [isBotTyping, setIsBotTyping] = useState(false);

  const activeChat = recentChats.find((chat) => chat.id === activeChatId);
  const activeMessages = activeChat ? activeChat.messages : draftMessages;
  const activeTitle = activeChat ? activeChat.title : "New conversation";

  const appendMessageToChat = (chatId, message) => {
    setRecentChats((previousChats) =>
      previousChats.map((chat) =>
        chat.id === chatId
          ? { ...chat, messages: [...chat.messages, message] }
          : chat
      )
    );
  };

  const startBotReply = (chatId, userMessageText) => {
    setIsBotTyping(true);

    window.setTimeout(() => {
      const botReply = getBotReply(userMessageText);

      const botMessage = {
        id: generateId("bot-message"),
        sender: "bot",
        text: botReply.reply,
        chips: botReply.chips,
      };

      appendMessageToChat(chatId, botMessage);
      setIsBotTyping(false);
    }, BOT_REPLY_DELAY_MS);
  };

  useEffect(() => {
    const initialMessage = location.state && location.state.initialMessage;

    if (!initialMessage || hasHandledInitialMessage.current) {
      return;
    }

    hasHandledInitialMessage.current = true;

    const newChatId = generateId("chat");
    const userMessage = {
      id: generateId("user-message"),
      sender: "user",
      text: initialMessage,
    };

    const newChat = {
      id: newChatId,
      title: buildTitleFromMessage(initialMessage),
      messages: [greetingMessage, userMessage],
    };

    setRecentChats((previousChats) => [newChat, ...previousChats]);
    setActiveChatId(newChatId);
    startBotReply(newChatId, initialMessage);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.state]);

  const handleNewQuery = () => {
    setActiveChatId(null);
    setDraftMessages([greetingMessage]);
    setIsBotTyping(false);
  };

  const handleSelectRecentChat = (chatId) => {
    setActiveChatId(chatId);
    setIsBotTyping(false);
  };

  const handleSend = (messageText) => {
    const userMessage = {
      id: generateId("user-message"),
      sender: "user",
      text: messageText,
    };

    if (activeChatId) {
      appendMessageToChat(activeChatId, userMessage);
      startBotReply(activeChatId, messageText);
      return;
    }

    const newChatId = generateId("chat");
    const newChat = {
      id: newChatId,
      title: buildTitleFromMessage(messageText),
      messages: [...draftMessages, userMessage],
    };

    setRecentChats((previousChats) => [newChat, ...previousChats]);
    setActiveChatId(newChatId);
    startBotReply(newChatId, messageText);
  };

  return (
    <div className={styles.page}>
      <Sidebar
        recentChats={recentChats}
        activeChatId={activeChatId}
        onSelectRecentChat={handleSelectRecentChat}
        onNewQuery={handleNewQuery}
      />

      <div className={styles.mainColumn}>
        <ChatHeader title={activeTitle} subtitle="Querio" />

        <ChatWindow
          messages={activeMessages}
          isBotTyping={isBotTyping}
          onChipSelect={handleSend}
        />

        <div className={styles.inputWrapper}>
          <ChatInput onSend={handleSend} />
        </div>
      </div>
    </div>
  );
};

export default ChatPage;
