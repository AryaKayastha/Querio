import { useState } from "react";
import { getBotReply } from "./utils/getBotReply.js";

const createMessage = (sender, text, sources = []) => ({
  id: `${sender}-${Date.now()}-${Math.random()}`,
  sender,
  text,
  sources,
});

const Citation = ({ source, children }) => {
  if (source?.source_url) {
    return <a href={source.source_url} target="_blank" rel="noreferrer">{children}</a>;
  }
  return <button type="button" onClick={() => window.alert(`${source?.source_name || "Source"}${source?.source_section ? ` — ${source.source_section}` : ""}`)}>{children}</button>;
};

const renderAnswer = (text, sources) => {
  if (!sources.length) return text;
  return text.split(/(\[[^\]]+\]|\([^()]+?\))/gu).map((part, index) => {
    if (!part || !/^(\[[^\]]+\]|\([^()]+?\))$/u.test(part)) return part;
    const citation = part.slice(1, -1).toLowerCase();
    const source = sources.find((item) => {
      const label = `${item.source_name} — ${item.source_section}`.toLowerCase();
      return citation === label || citation.includes(item.source_name.toLowerCase());
    });
    return source ? <Citation key={`${part}-${index}`} source={source}>{part}</Citation> : part;
  });
};

export default function App() {
  const [messages, setMessages] = useState([
    createMessage("bot", "Hi 👋 How can I help you today?"),
  ]);
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState(false);

  const send = async (event) => {
    event.preventDefault();
    const value = query.trim();
    if (!value || busy) return;

    setQuery("");
    setMessages((current) => [...current, createMessage("user", value)]);
    setBusy(true);
    const reply = await getBotReply(value);
    setMessages((current) => [...current, createMessage("bot", reply.reply, reply.sources || [])]);
    setBusy(false);
  };

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand"><span>Q</span><strong>Querio</strong></div>
        <button className="new-query" type="button" onClick={() => setMessages([createMessage("bot", "Hi 👋 How can I help you today?")])}>＋ New query</button>
        <p className="section-label">Recent chats</p>
      </aside>
      <section className="chat-panel">
        <header><strong>Student Query Assistant</strong><span>● Bot online</span></header>
        <div className="messages" aria-live="polite">
          {messages.map((message) => (
            <div className={`message-row ${message.sender}`} key={message.id}>
              <div className="avatar">{message.sender === "bot" ? "Q" : "You"}</div>
              <div className="message-bubble">
                {message.sender === "bot" ? renderAnswer(message.text, message.sources) : message.text}
                {message.sources.length > 0 && <small>Sources: {message.sources.map((source) => `${source.source_name} — ${source.source_section}`).join(" · ")}</small>}
              </div>
            </div>
          ))}
          {busy && <div className="message-bubble typing">Querio is checking the sources…</div>}
        </div>
        <form className="composer" onSubmit={send}>
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Type your question…" aria-label="Question" />
          <button type="submit" disabled={busy || !query.trim()}>➤</button>
        </form>
      </section>
    </main>
  );
}
