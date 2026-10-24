import { useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
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

// Links in answers (club websites, official certification pages) open in a new tab so the chat
// stays put. remark-gfm also turns bare https:// URLs into links and renders tables.
const markdownComponents = {
  a: ({ href, children }) => (
    <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>
  ),
};

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

  // Only tidy gaps inside a line: leading indentation is what makes a markdown sub-list, and
  // stripping it flattened nested lists (headings and their details rendered as siblings).
  return result
    .replace(/[ \t]+([.,;:!?])/gu, "$1") // drop the space left behind before punctuation
    .replace(/(\S)[ \t]{2,}/gu, "$1 ")
    .replace(/[ \t]+\n/gu, "\n")
    .trim();
};

// Students only need to know which documents an answer came from -- not the retrieved chunk
// ("NSS activities (part 5 of 7)", "Page 12") -- so show one chip per document, by name.
const toDocuments = (sources) => {
  const documents = new Map();
  sources.forEach((source) => {
    const name = (source.source_name || "").replace(/_/gu, " ").replace(/\s+/gu, " ").trim();
    if (!name) {
      return;
    }
    const existing = documents.get(name);
    if (!existing) {
      documents.set(name, { name, url: source.source_url });
    } else if (!isSafeUrl(existing.url) && isSafeUrl(source.source_url)) {
      existing.url = source.source_url;
    }
  });
  return [...documents.values()];
};

const MessageBubble = ({ message, onChipSelect }) => {
  const isBot = message.sender === "bot";
  const sources = useMemo(
    () => (Array.isArray(message.sources) ? message.sources : []),
    [message.sources]
  );
  const documents = useMemo(() => toDocuments(sources), [sources]);
  const hasChips = Boolean(message.chips && message.chips.length > 0);
  const [selectedSource, setSelectedSource] = useState(null);

  // Citation matching needs each chunk's section, so it uses the full source list. The knowledge
  // base separates names from details with " -- ", which answers echo; show it as a dash.
  const displayText = useMemo(() => {
    if (!isBot) {
      return message.text;
    }
    const text = sources.length > 0 ? stripCitations(message.text, sources) : message.text;
    return text.replace(/ -- /gu, " – ");
  }, [isBot, message.text, sources]);

  return (
    <div className={`${styles.messageRow} ${isBot ? "" : styles.user}`}>
      {isBot && <Avatar label="Q" size={24} />}

      <div className={styles.bubbleColumn}>
        <div className={`${styles.bubble} ${isBot ? styles.bot : styles.user}`}>
          {isBot ? (
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>{displayText}</ReactMarkdown>
          ) : message.text}
        </div>

        {isBot && documents.length > 0 && (
          <div className={styles.sources} aria-label="Sources">
            <span className={styles.sourcesLabel}>Sources</span>
            {documents.map((document) => (isSafeUrl(document.url) ? (
              <a
                key={document.name}
                className={styles.sourceLink}
                href={document.url}
                target="_blank"
                rel="noreferrer"
              >
                {document.name}
              </a>
            ) : (
              <button
                key={document.name}
                type="button"
                className={styles.sourceLink}
                onClick={() => setSelectedSource(document)}
              >
                {document.name}
              </button>
            )))}
          </div>
        )}

        {selectedSource && (
          <div className={styles.sourceDetails} role="status">
            <strong>{selectedSource.name}</strong>
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
