import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { exchangeAuthCode } from "../lib/api";

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || "";
const REDIRECT_URI = `${window.location.origin}/auth/callback`;
const SCOPES = "https://www.googleapis.com/auth/drive.readonly openid email profile";

function buildAuthUrl() {
  const params = new URLSearchParams({
    client_id: GOOGLE_CLIENT_ID,
    redirect_uri: REDIRECT_URI,
    response_type: "code",
    scope: SCOPES,
    access_type: "offline",
    prompt: "consent",
  });
  return `https://accounts.google.com/o/oauth2/v2/auth?${params}`;
}

export default function Login() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const code = searchParams.get("code");

  useEffect(() => {
    if (code) {
      exchangeAuthCode(code).then((data) => {
        localStorage.setItem("access_token", data.access_token);
        if (data.refresh_token) {
          localStorage.setItem("refresh_token", data.refresh_token);
        }
        navigate("/select");
      });
    }
  }, [code, navigate]);

  if (code) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-neutral-400">Signing in...</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen gap-8">
      <div className="text-center">
        <h1 className="text-5xl font-bold tracking-tight">Auto-Vid</h1>
        <p className="mt-3 text-neutral-400 text-lg">
          AI-powered video editing from your Google Drive
        </p>
      </div>
      <a
        href={buildAuthUrl()}
        className="px-8 py-3 bg-white text-neutral-900 font-semibold rounded-lg hover:bg-neutral-200 transition"
      >
        Sign in with Google
      </a>
    </div>
  );
}
