import { useEffect, useRef, useState } from "react";
import { getQuestions } from "../lib/api";

interface Question {
  id: string;
  text: string;
  options?: string[] | null;
}

interface Message {
  role: "agent" | "user";
  text: string;
}

export default function ClarifyChat({
  projectId,
  summariesReady,
  onDone,
}: {
  projectId: string;
  summariesReady: boolean;
  onDone: (answers: Record<string, string>) => void;
}) {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [questionIdx, setQuestionIdx] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [questionsComplete, setQuestionsComplete] = useState(false);
  const [loading, setLoading] = useState(false);
  const [extraCount, setExtraCount] = useState(0);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const [fetchedFromServer, setFetchedFromServer] = useState(false);

  useEffect(() => {
    if (!summariesReady || fetchedFromServer) return;
    setLoading(true);
    getQuestions(projectId)
      .then((data) => {
        const qs: Question[] = data.questions || [];
        setQuestions(qs);
        setFetchedFromServer(true);
        const msgs: Message[] = [];
        if (data.intro) {
          msgs.push({ role: "agent", text: data.intro });
        }
        if (qs.length > 0) {
          msgs.push({ role: "agent", text: qs[0].text });
        }
        setMessages(
          msgs.length > 0
            ? msgs
            : [{ role: "agent", text: "Tell me about your video." }],
        );
      })
      .catch((e) => {
        console.error("Failed to get questions:", e);
      })
      .finally(() => setLoading(false));
  }, [summariesReady, projectId, fetchedFromServer]);

  const selectOption = (option: string) => {
    handleAnswer(option);
  };

  const send = () => {
    if (!input.trim()) return;
    handleAnswer(input.trim());
    setInput("");
  };

  const handleAnswer = (answer: string) => {
    if (!questionsComplete) {
      const q = questions[questionIdx];
      if (!q) return;

      setMessages((prev) => [...prev, { role: "user", text: answer }]);
      const newAnswers = { ...answers, [q.id]: answer };
      setAnswers(newAnswers);

      const nextIdx = questionIdx + 1;
      if (nextIdx < questions.length) {
        setQuestionIdx(nextIdx);
        setTimeout(() => {
          setMessages((prev) => [
            ...prev,
            { role: "agent", text: questions[nextIdx].text },
          ]);
        }, 400);
      } else {
        setQuestionsComplete(true);
        setTimeout(() => {
          setMessages((prev) => [
            ...prev,
            {
              role: "agent",
              text: "Got it! You can add any extra instructions below, or click 'Generate Edit Plan' when ready.",
            },
          ]);
          onDone(newAnswers);
        }, 400);
      }
    } else {
      const newCount = extraCount + 1;
      setExtraCount(newCount);
      setMessages((prev) => [...prev, { role: "user", text: answer }]);

      const newAnswers = { ...answers, [`extra_${newCount}`]: answer };
      setAnswers(newAnswers);

      setTimeout(() => {
        setMessages((prev) => [
          ...prev,
          { role: "agent", text: "Noted! Anything else, or hit 'Generate Edit Plan' to start." },
        ]);
        onDone(newAnswers);
      }, 300);
    }
  };

  const currentQuestion = !questionsComplete ? questions[questionIdx] : null;

  return (
    <div className="bg-neutral-900 border border-neutral-800 rounded-xl flex flex-col h-[450px]">
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-3">
        {!summariesReady && (
          <div className="text-sm text-neutral-500 italic mb-2">
            Analyzing your videos (summaries first, deep analysis continues in background)...
          </div>
        )}
        {loading && (
          <div className="text-sm text-neutral-500 italic">
            Generating questions based on your videos...
          </div>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] px-4 py-2 rounded-2xl text-sm whitespace-pre-wrap ${
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

      {currentQuestion?.options && summariesReady && (
        <div className="px-4 pb-2 flex flex-wrap gap-2">
          {currentQuestion.options.map((opt) => (
            <button
              key={opt}
              onClick={() => selectOption(opt)}
              className="px-3 py-1.5 bg-neutral-800 border border-neutral-700 rounded-lg text-sm hover:bg-neutral-700 transition"
            >
              {opt}
            </button>
          ))}
        </div>
      )}

      <div className="border-t border-neutral-800 p-3 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder={
            questionsComplete
              ? "Add more instructions (optional)..."
              : "Type your answer..."
          }
          disabled={!summariesReady || loading}
          className="flex-1 bg-neutral-800 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-40"
        />
        <button
          onClick={send}
          disabled={!input.trim() || !summariesReady}
          className="px-4 py-2 bg-blue-600 rounded-lg text-sm font-semibold disabled:opacity-40 hover:bg-blue-500 transition"
        >
          Send
        </button>
      </div>
    </div>
  );
}
