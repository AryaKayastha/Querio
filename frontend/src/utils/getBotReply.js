import { sendChatMessage } from "../api/backend.js";

const DEFAULT_REPLY =
  "I’m sorry — I can’t get a reliable answer right now. Please try again in a moment.";

const CONNECTIVITY_REPLY =
  "I couldn’t reach the Querio server just now. Please check your connection or try again shortly.";

const EMPTY_QUERY_REPLY = "Please type a question before sending.";

const normalizeSourcesToChips = (sources) => {
  if (!Array.isArray(sources)) {
    return [];
  }

  const uniqueSourceNames = new Set();

  sources.forEach((source) => {
    const sourceName = source && typeof source.source_name === "string" ? source.source_name.trim() : "";

    if (sourceName.length > 0) {
      uniqueSourceNames.add(sourceName);
    }
  });

  return [...uniqueSourceNames];
};

export const getBotReply = async (messageText) => {
  try {
    const response = await sendChatMessage(messageText);

    const reply = typeof response.answer === "string" && response.answer.trim().length > 0
      ? response.answer
      : DEFAULT_REPLY;

    const chips = normalizeSourcesToChips(response.sources);

    const confidenceValue = Number(response.confidence);
    const confidence = Number.isFinite(confidenceValue) ? confidenceValue : 0;

    return {
      reply,
      chips,
      meta: {
        domain: typeof response.domain === "string" ? response.domain : "",
        confidence,
        guidance_only: Boolean(response.guidance_only),
      },
    };
  } catch (error) {
    if (error && error.type === "empty_query") {
      return {
        reply: EMPTY_QUERY_REPLY,
        chips: [],
      };
    }

    if (error && (error.type === "timeout" || error.type === "network_error")) {
      return {
        reply: CONNECTIVITY_REPLY,
        chips: [],
      };
    }

    return {
      reply: DEFAULT_REPLY,
      chips: [],
    };
  }
};
