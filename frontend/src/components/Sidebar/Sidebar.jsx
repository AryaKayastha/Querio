import { useNavigate } from "react-router-dom";
import Avatar from "../Avatar/Avatar.jsx";
import RecentChatItem from "../RecentChatItem/RecentChatItem.jsx";
import { PlusIcon } from "../../assets/icons/index.js";
import styles from "./Sidebar.module.css";

const Sidebar = ({ recentChats, activeChatId, onSelectRecentChat, onNewQuery }) => {
  const navigate = useNavigate();

  const handleBrandClick = () => {
    navigate("/");
  };

  return (
    <aside className={styles.sidebar}>
      <button type="button" className={styles.brandRow} onClick={handleBrandClick}>
        <Avatar label="Q" size={26} variant="gold" />
        <span className={styles.brandName}>Querio</span>
      </button>

      <div className={styles.newQuerySection}>
        <button type="button" className={styles.newQueryButton} onClick={onNewQuery}>
          <PlusIcon size={13} />
          New query
        </button>
      </div>

      {recentChats.length > 0 && (
        <>
          <div className={styles.sectionLabel}>RECENT CHATS</div>

          <div className={styles.recentList}>
            {recentChats.map((chat) => (
              <RecentChatItem
                key={chat.id}
                title={chat.title}
                isActive={chat.id === activeChatId}
                onSelect={() => onSelectRecentChat(chat.id)}
              />
            ))}
          </div>
        </>
      )}

      <div className={styles.spacer} />

      <div className={styles.profileRow}>
        <Avatar label="R" size={24} variant="person" />
        <span>Riya · 3rd yr CS</span>
      </div>
    </aside>
  );
};

export default Sidebar;
