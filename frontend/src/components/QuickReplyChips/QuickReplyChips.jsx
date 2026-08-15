import styles from "./QuickReplyChips.module.css";

const QuickReplyChips = ({ chips, onChipSelect }) => {
  const handleChipClick = (chipText) => {
    if (onChipSelect) {
      onChipSelect(chipText);
    }
  };

  return (
    <div className={styles.chipRow}>
      {chips.map((chipText) => (
        <button
          key={chipText}
          type="button"
          className={styles.chip}
          onClick={() => handleChipClick(chipText)}
        >
          {chipText}
        </button>
      ))}
    </div>
  );
};

export default QuickReplyChips;
