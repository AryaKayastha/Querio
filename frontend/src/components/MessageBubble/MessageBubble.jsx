import { useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import Avatar from "../Avatar/Avatar.jsx";
import QuickReplyChips from "../QuickReplyChips/QuickReplyChips.jsx";
import styles from "./MessageBubble.module.css";

// Matches inline citation markers the model sometimes emits after individual facts, e.g.
// "...late fee of Rs. 50/- per day. (Source: FeesStructure — Page 1)" or "[FeesStructure — Page 1]".
const CITATION_PATTERN = /\[([^\]]+)\]|\(([^()]+?)\)/gu;

const normalizeCitationText = (value) => value
  .replace(/[âÃ][^\s]*/gu, "—")
  .replace(/[–—−]/gu, "—")
  .trim()
  .toLowerCase();

const isSafeUrl = (value) => /^https?:\/\//iu.test(value || "");

const findSource = (citationText, sources) => {
  const normalizedText = normalizeCitationText(citationText);
  const [namePart, sectionPart = ""] = normalizedText.split(/\s+—\s+/u);
  const name = namePart.trim();
  const section = sectionPart.trim();

  return sources.find((source) => {
    const sourceName = normalizeCitationText(source.source_name || "");
    const sourceSection = normalizeCitationText(source.source_section || "");
    return sourceName === name && (!section || sourceSection === section);
  });
};

// The model cites sources inline after nearly every sentence. Repeating that on every
// line clutters the answer -- strip recognized inline citations from the rendered text
// and rely on the deduplicated Sources footer below for tracing facts back to a source.
const stripCitations = (text, sources) => {
  let result = "";
  let lastIndex = 0;

  for (const match of text.matchAll(CITATION_PATTERN)) {
    const citationText = match[1] || match[2];
    if (!findSource(citationText, sources)) {
      continue;
    }
    result += text.slice(lastIndex, match.index);
    lastIndex = match.index + match[0].length;
  }
  result += text.slice(lastIndex);

  return result
    .replace(/[ \t]+([.,;:!?])/gu, "$1") // drop the space left behind before punctuation
    .replace(/[ \t]{2,}/gu, " ")
    .replace(/\n[ \t]+/gu, "\n")
    .replace(/[ \t]+\n/gu, "\n")
    .trim();
};

const dedupeSources = (sources) => {
  const seen = new Set();
  return sources.filter((source) => {
    const key = `${source.source_name}|${source.source_section}`;
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
};

const MessageBubble = ({ message, onChipSelect }) => {
  const isBot = message.sender === "bot";
  const rawSources = Array.isArray(message.sources) ? message.sources : [];
  const sources = useMemo(() => dedupeSources(rawSources), [rawSources]);
  const hasChips = Boolean(message.chips && message.chips.length > 0);
  const [selectedSource, setSelectedSource] = useState(null);

  const displayText = useMemo(
    () => (isBot && sources.length > 0 ? stripCitations(message.text, sources) : message.text),
    [isBot, message.text, sources]
  );

  return (
    <div className={`${styles.messageRow} ${isBot ? "" : styles.user}`}>
      {isBot && <Avatar label="Q" size={24} />}

      <div className={styles.bubbleColumn}>
        <div className={`${styles.bubble} ${isBot ? styles.bot : styles.user}`}>
          {isBot ? <ReactMarkdown>{displayText}</ReactMarkdown> : message.text}
        </div>

        {isBot && sources.length > 0 && (
          <div className={styles.sources} aria-label="Sources">
            <span className={styles.sourcesLabel}>Sources</span>
            {sources.map((source) => {
              const label = source.source_section
                ? `${source.source_name} · ${source.source_section}`
                : source.source_name;
              const sourceLink = isSafeUrl(source.source_url);

              return sourceLink ? (
                <a
                  key={`${source.source_name}-${source.source_section}`}
                  className={styles.sourceLink}
                  href={source.source_url}
                  target="_blank"
                  rel="noreferrer"
                >
                  {label}
                </a>
              ) : (
                <button
                  key={`${source.source_name}-${source.source_section}`}
                  type="button"
                  className={styles.sourceLink}
                  onClick={() => setSelectedSource(source)}
                >
                  {label}
                </button>
              );
            })}
          </div>
        )}

        {selectedSource && (
          <div className={styles.sourceDetails} role="status">
            <strong>{selectedSource.source_name}</strong>
            {selectedSource.source_section && <span>{selectedSource.source_section}</span>}
            <span>This source is available in Querio’s knowledge base but has no public link yet.</span>
            <button type="button" onClick={() => setSelectedSource(null)}>Close</button>
          </div>
        )}

        {hasChips && (
          <QuickReplyChips chips={message.chips} onChipSelect={onChipSelect} />
        )}
      </div>
    </div>
  );
};

export default MessageBubble;
