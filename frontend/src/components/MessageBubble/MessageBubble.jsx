import { useState } from "react";
import Avatar from "../Avatar/Avatar.jsx";
import styles from "./MessageBubble.module.css";

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

const MessageBubble = ({ message }) => {
  const isBot = message.sender === "bot";
  const sources = Array.isArray(message.sources) ? message.sources : [];
  const [selectedSource, setSelectedSource] = useState(null);

  const renderText = () => {
    if (!isBot || sources.length === 0) {
      return message.text;
    }

    const parts = [];
    let lastIndex = 0;

    for (const match of message.text.matchAll(CITATION_PATTERN)) {
      const citationText = match[1] || match[2];
      const source = findSource(citationText, sources);
      if (!source) {
        continue;
      }

      parts.push(message.text.slice(lastIndex, match.index));
      const label = citationText;
      if (isSafeUrl(source.source_url)) {
        parts.push(
          <a
            key={`${label}-${match.index}`}
            className={styles.citation}
            href={source.source_url}
            target="_blank"
            rel="noreferrer"
            title={`Open ${source.source_name}`}
          >
            [{label}]
          </a>
        );
      } else {
        parts.push(
          <button
            key={`${label}-${match.index}`}
            type="button"
            className={styles.citation}
            onClick={() => setSelectedSource(source)}
            title="View source details"
          >
            [{label}]
          </button>
        );
      }
      lastIndex = match.index + match[0].length;
    }

    if (parts.length === 0) {
      return message.text;
    }

    parts.push(message.text.slice(lastIndex));
    return parts;
  };

  return (
    <div className={`${styles.messageRow} ${isBot ? "" : styles.user}`}>
      {isBot && <Avatar label="Q" size={24} />}

      <div className={styles.bubbleColumn}>
        <div className={`${styles.bubble} ${isBot ? styles.bot : styles.user}`}>
          {renderText()}
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
      </div>
    </div>
  );
};

export default MessageBubble;
