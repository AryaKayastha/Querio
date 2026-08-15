import { useState } from "react";
import { useNavigate } from "react-router-dom";
import WidgetBubble from "../../components/WidgetBubble/WidgetBubble.jsx";
import WidgetPanel from "../../components/WidgetPanel/WidgetPanel.jsx";
import { ArrowLeftIcon } from "../../assets/icons/index.js";
import styles from "./WidgetDemoPage.module.css";

const WidgetDemoPage = () => {
  const navigate = useNavigate();
  const [isWidgetOpen, setIsWidgetOpen] = useState(false);

  const handleToggleWidget = () => {
    setIsWidgetOpen((previousValue) => !previousValue);
  };

  const handleExitDemo = () => {
    navigate("/");
  };

  return (
    <div className={styles.page}>
      <div className={styles.exitBar}>
        <button type="button" className={styles.exitLink} onClick={handleExitDemo}>
          <ArrowLeftIcon size={14} />
          Exit widget demo
        </button>
      </div>

      <nav className={styles.siteNav}>
        <span className={styles.siteBrand}>Dept. of Computer Science</span>
        <div className={styles.siteLinks}>
          <span>About</span>
          <span>Academics</span>
          <span>Notices</span>
          <span>Contact</span>
        </div>
      </nav>

      <main className={styles.siteBody}>
        <div className={styles.pageHeading} />
        <div className={styles.pageLine} />
        <div className={`${styles.pageLine} ${styles.short}`} />

        <div className={styles.cardGrid}>
          <div className={styles.placeholderCard} />
          <div className={styles.placeholderCard} />
          <div className={styles.placeholderCard} />
        </div>

        <p className={styles.hintText}>
          This page stands in for the existing department website. The chat bubble in the
          bottom-right corner is the same assistant, embedded as a widget.
        </p>
      </main>

      <WidgetBubble isOpen={isWidgetOpen} hasUnread={!isWidgetOpen} onToggle={handleToggleWidget} />

      {isWidgetOpen && <WidgetPanel onClose={handleToggleWidget} />}
    </div>
  );
};

export default WidgetDemoPage;
