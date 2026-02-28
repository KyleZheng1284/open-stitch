const BASE = "/api";

export async function uploadFiles(files: File[]) {
  const form = new FormData();
  for (const f of files) {
    form.append("files", f);
  }
  const res = await fetch(`${BASE}/projects/upload`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
  return res.json();
}

export async function getProject(projectId: string) {
  const res = await fetch(`${BASE}/projects/${projectId}`);
  if (!res.ok) throw new Error("Get project failed");
  return res.json();
}

export async function getQuestions(projectId: string) {
  const res = await fetch(`${BASE}/projects/${projectId}/questions`);
  if (!res.ok) throw new Error("Get questions failed");
  return res.json();
}

export async function submitClarifyAnswers(
  projectId: string,
  answers: Record<string, string>
) {
  const res = await fetch(`${BASE}/projects/${projectId}/clarify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ answers }),
  });
  if (!res.ok) throw new Error("Clarify failed");
  return res.json();
}

export async function startEdit(projectId: string, structuredPrompt: string) {
  const res = await fetch(`${BASE}/projects/${projectId}/edit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ structured_prompt: structuredPrompt }),
  });
  if (!res.ok) throw new Error("Start edit failed");
  return res.json();
}

export function createJobSocket(projectId: string): WebSocket {
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  return new WebSocket(
    `${proto}://${window.location.host}/api/jobs/${projectId}/stream`
  );
}
