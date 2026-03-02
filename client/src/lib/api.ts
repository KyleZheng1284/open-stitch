const BASE = "/api";

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem("access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function exchangeAuthCode(code: string) {
  const res = await fetch(`${BASE}/auth/google`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code }),
  });
  if (!res.ok) throw new Error("Auth exchange failed");
  return res.json();
}

export async function listDriveFiles(pageToken?: string) {
  const url = new URL(`${window.location.origin}${BASE}/drive/files`);
  if (pageToken) url.searchParams.set("page_token", pageToken);
  const res = await fetch(url.toString(), {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("List Drive files failed");
  return res.json();
}

export async function downloadFiles(ids: string[]) {
  const res = await fetch(`${BASE}/drive/download`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ file_ids: ids }),
  });
  if (!res.ok) throw new Error("Drive download failed");
  return res.json();
}

export async function createProject(fileIds: string[]) {
  const res = await fetch(`${BASE}/projects/from-drive`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ file_ids: fileIds }),
  });
  if (!res.ok) throw new Error("Create project failed");
  return res.json();
}

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
