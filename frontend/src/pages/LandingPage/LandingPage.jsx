import { useNavigate } from "react-router-dom";
import Avatar from "../../components/Avatar/Avatar.jsx";
import ChatInput from "../../components/ChatInput/ChatInput.jsx";
import ExamplePromptCard from "../../components/ExamplePromptCard/ExamplePromptCard.jsx";
import styles from "./LandingPage.module.css";

const EXAMPLE_PROMPTS = [
  "What is the NOC process?",
  "How do I apply for leave?",
  "Tell me about placement stats",
  "What's the exam schedule?",
];

const LandingPage = () => {
  const navigate = useNavigate();

  const goToChatWithMessage = (messageText) => {
    navigate("/chat", { state: { initialMessage: messageText } });
  };

  return (
    <div className={styles.page}>
      <div className={styles.card}>
        <div className={styles.greetingIcon}>
          <Avatar label="Q" size={56} variant="gold" />
        </div>

        <h1 className={styles.title}>Hi, I&apos;m Querio 👋</h1>
        <p className={styles.subtitle}>
          Your AI-powered campus assistant. Ask me anything about
          academics, placements, leaves &amp; more.
        </p>

        <div className={styles.inputSection}>
          <ChatInput
            onSend={goToChatWithMessage}
            placeholder="Type your question…"
          />
        </div>

        <div className={styles.exampleSection}>
          <div className={styles.exampleLabel}>Try asking</div>
          <div className={styles.exampleGrid}>
            {EXAMPLE_PROMPTS.map((prompt) => (
              <ExamplePromptCard
                key={prompt}
                promptText={prompt}
                onSelect={goToChatWithMessage}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default LandingPage;
