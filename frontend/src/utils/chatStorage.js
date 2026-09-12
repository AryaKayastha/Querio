const RECENT_CHATS_KEY = "querio.chatPage.recentChats.v1";
const ACTIVE_CHAT_ID_KEY = "querio.chatPage.activeChatId.v1";

const isValidChat = (chat) =>
  chat &&
  typeof chat.id === "string" &&
  typeof chat.title === "string" &&
  Array.isArray(chat.messages);

export const loadStoredChats = () => {
  try {
    const raw = window.localStorage.getItem(RECENT_CHATS_KEY);
    if (!raw) {
      return [];
    }

    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter(isValidChat) : [];
  } catch {
    return [];
  }
};

export const saveStoredChats = (recentChats) => {
  try {
    window.localStorage.setItem(RECENT_CHATS_KEY, JSON.stringify(recentChats));
  } catch {
    // localStorage may be unavailable (private browsing, quota exceeded) -- chat still
    // works in-memory for the current tab, it just won't survive a refresh.
  }
};

export const loadStoredActiveChatId = () => {
  try {
    return window.localStorage.getItem(ACTIVE_CHAT_ID_KEY) || null;
  } catch {
    return null;
  }
};

export const saveStoredActiveChatId = (activeChatId) => {
  try {
    if (activeChatId) {
      window.localStorage.setItem(ACTIVE_CHAT_ID_KEY, activeChatId);
    } else {
      window.localStorage.removeItem(ACTIVE_CHAT_ID_KEY);
    }
  } catch {
    // Same as above -- fail silently and keep working in-memory.
  }
};
