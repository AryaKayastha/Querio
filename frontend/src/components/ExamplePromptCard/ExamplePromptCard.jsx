import { QuestionIcon } from "../../assets/icons/index.js";
import styles from "./ExamplePromptCard.module.css";

const ExamplePromptCard = ({ promptText, onSelect }) => {
  return (
    <button type="button" className={styles.card} onClick={() => onSelect(promptText)}>
      <span className={styles.icon}>
        <QuestionIcon size={16} />
      </span>
      <span className={styles.text}>{promptText}</span>
    </button>
  );
};

export default ExamplePromptCard;
