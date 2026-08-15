import { useNavigate } from "react-router-dom";
import Avatar from "../../components/Avatar/Avatar.jsx";
import ChatInput from "../../components/ChatInput/ChatInput.jsx";
import styles from "./LandingPage.module.css";

const LandingPage = () => {
  const navigate = useNavigate();

  const goToChatWithMessage = (messageText) => {
    navigate("/chat", { state: { initialMessage: messageText } });
  };

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <div className={styles.greetingIcon}>
          <Avatar label="Q" size={44} variant="gold" />
        </div>

        <h1 className={styles.title}>Hi, I&apos;m Querio 👋</h1>
        <p className={styles.subtitle}>What do you need help with today?</p>

        <div className={styles.inputSection}>
          <ChatInput
            onSend={goToChatWithMessage}
            placeholder="Type your question…"
          />
        </div>
      </div>
    </div>
  );
};

export default LandingPage;
