import { botKnowledge, defaultBotReply } from "../data/botKnowledge.js";

// Simulates what a backend classifier would return for a given question.
// It looks for the first knowledge entry whose keyword appears inside the
// student's message, and falls back to a generic response otherwise.
export const getBotReply = (messageText) => {
  const normalizedMessage = messageText.toLowerCase();

  const matchedEntry = botKnowledge.find((entry) => {
    return entry.keywords.some((keyword) => normalizedMessage.includes(keyword));
  });

  if (matchedEntry) {
    return {
      reply: matchedEntry.reply,
      chips: matchedEntry.chips,
    };
  }

  return defaultBotReply;
};
