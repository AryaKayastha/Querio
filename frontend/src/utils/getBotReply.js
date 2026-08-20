import { sendChatMessage } from "../api/backend.js";

const DEFAULT_REPLY =
  "I’m sorry — I can’t get a reliable answer right now. Please try again in a moment.";

const CONNECTIVITY_REPLY =
  "I couldn’t reach the Querio server just now. Please check your connection or try again shortly.";

const EMPTY_QUERY_REPLY = "Please type a question before sending.";

const normalizeSources = (sources) => {
  if (!Array.isArray(sources)) {
    return [];
  }

  const uniqueSources = new Map();

  sources.forEach((source) => {
    const sourceName = source && typeof source.source_name === "string" ? source.source_name.trim() : "";

    if (sourceName.length > 0) {
      const sourceSection = typeof source.source_section === "string" ? source.source_section.trim() : "";
      const sourceUrl = typeof source.source_url === "string" ? source.source_url.trim() : "";
      const key = `${sourceName}|${sourceSection}`;
      uniqueSources.set(key, {
        source_name: sourceName,
        source_section: sourceSection,
        source_url: sourceUrl,
      });
    }
  });

  return [...uniqueSources.values()];
};

const sourcesToChips = (sources) =>
  [...new Set(sources.map((source) => source.source_name).filter(Boolean))];

export const getBotReply = async (messageText) => {
  try {
    const response = await sendChatMessage(messageText);

    const reply = typeof response.answer === "string" && response.answer.trim().length > 0
      ? response.answer
      : DEFAULT_REPLY;

    const sources = normalizeSources(response.sources);
    const chips = sourcesToChips(sources);

    const confidenceValue = Number(response.confidence);
    const confidence = Number.isFinite(confidenceValue) ? confidenceValue : 0;

    return {
      reply,
      sources,
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
        sources: [],
        chips: [],
      };
    }

    if (error && (error.type === "timeout" || error.type === "network_error")) {
      return {
        reply: CONNECTIVITY_REPLY,
        sources: [],
        chips: [],
      };
    }

    if (error && error.type === "http_error") {
      return {
        reply: "The Querio backend is online, but the chatbot service could not answer this request. Please try again shortly.",
        sources: [],
        chips: [],
      };
    }

    return {
      reply: DEFAULT_REPLY,
      sources: [],
      chips: [],
    };
  }
};
