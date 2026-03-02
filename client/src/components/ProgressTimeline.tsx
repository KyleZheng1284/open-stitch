interface Step {
  name: string;
  status: "pending" | "running" | "done" | "error";
  elapsed?: number;
}

export default function ProgressTimeline({ steps }: { steps: Step[] }) {
  return (
    <div className="space-y-0">
      {steps.map((step, i) => (
        <div key={i} className="flex items-start gap-4">
          {/* Indicator */}
          <div className="flex flex-col items-center">
            <div
              className={`w-10 h-10 rounded-full flex items-center justify-center border-2 ${
                step.status === "done"
                  ? "bg-green-600 border-green-600"
                  : step.status === "running"
                  ? "border-blue-500 bg-blue-500/20"
                  : step.status === "error"
                  ? "border-red-500 bg-red-500/20"
                  : "border-neutral-700 bg-neutral-900"
              }`}
            >
              {step.status === "done" ? (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              ) : step.status === "running" ? (
                <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              ) : step.status === "error" ? (
                <span className="text-red-400 text-sm font-bold">!</span>
              ) : (
                <span className="text-neutral-600 text-sm">{i + 1}</span>
              )}
            </div>
            {i < steps.length - 1 && (
              <div
                className={`w-0.5 h-12 ${
                  step.status === "done" ? "bg-green-600" : "bg-neutral-800"
                }`}
              />
            )}
          </div>

          {/* Label */}
          <div className="pt-2">
            <p
              className={`font-medium ${
                step.status === "running"
                  ? "text-blue-400"
                  : step.status === "done"
                  ? "text-neutral-300"
                  : step.status === "error"
                  ? "text-red-400"
                  : "text-neutral-600"
              }`}
            >
              {step.name}
            </p>
            {step.elapsed && (
              <p className="text-sm text-neutral-500">{step.elapsed.toFixed(1)}s</p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
