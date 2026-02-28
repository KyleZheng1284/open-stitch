import { useState } from "react";

interface Message {
  role: "agent" | "user";
  text: string;
}

const INITIAL_QUESTIONS = [
  "How long should the final video be? (Short: 15-60s, or Long: 1-10min)",
  "What style are you going for? (Vlog, Tutorial, Highlights, Cinematic, Story)",
];

export default function ClarifyChat({
  summariesReady,
  onDone,
}: {
  summariesReady: boolean;
  onDone: (answers: Record<string, string>) => void;
}) {
  const [messages, setMessages] = useState<Message[]>([
    { role: "agent", text: INITIAL_QUESTIONS[0] },
  ]);
  const [input, setInput] = useState("");
  const [questionIdx, setQuestionIdx] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [done, setDone] = useState(false);

  const send = () => {
    if (!input.trim() || done) return;

    const answer = input.trim();
    const key = `q${questionIdx}`;

    setMessages((prev) => [...prev, { role: "user", text: answer }]);
    setAnswers((prev) => ({ ...prev, [key]: answer }));
    setInput("");

    const nextIdx = questionIdx + 1;
    if (nextIdx < INITIAL_QUESTIONS.length) {
      setQuestionIdx(nextIdx);
      setTimeout(() => {
        setMessages((prev) => [
          ...prev,
          { role: "agent", text: INITIAL_QUESTIONS[nextIdx] },
        ]);
      }, 500);
    } else {
      setDone(true);
      const finalAnswers = { ...answers, [key]: answer };
      setTimeout(() => {
        setMessages((prev) => [
          ...prev,
          {
            role: "agent",
            text: "Got it! I have everything I need. Click 'Generate Edit Plan' when ready.",
          },
        ]);
        onDone(finalAnswers);
      }, 500);
    }
  };

  return (
    <div className="bg-neutral-900 border border-neutral-800 rounded-xl flex flex-col h-[400px]">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {!summariesReady && (
          <div className="text-sm text-neutral-500 italic mb-2">
            Waiting for video analysis to complete...
          </div>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] px-4 py-2 rounded-2xl text-sm ${
                m.role === "user"
                  ? "bg-blue-600 text-white"
                  : "bg-neutral-800 text-neutral-200"
              }`}
            >
              {m.text}
            </div>
          </div>
        ))}
      </div>

      {/* Input */}
      <div className="border-t border-neutral-800 p-3 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder={done ? "All questions answered" : "Type your answer..."}
          disabled={done || !summariesReady}
          className="flex-1 bg-neutral-800 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-40"
        />
        <button
          onClick={send}
          disabled={done || !input.trim() || !summariesReady}
          className="px-4 py-2 bg-blue-600 rounded-lg text-sm font-semibold disabled:opacity-40 hover:bg-blue-500 transition"
        >
          Send
        </button>
      </div>
    </div>
  );
}
