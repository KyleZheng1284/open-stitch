# Google Drive Upload — Integration Notes

## Prerequisites

### 1. Environment variable

Create a `.env.local` file in the `client/` directory:

```
VITE_GOOGLE_CLIENT_ID=<your-oauth2-client-id>.apps.googleusercontent.com
```

Obtain the client ID from the [Google Cloud Console](https://console.cloud.google.com/) under
**APIs & Services → Credentials → OAuth 2.0 Client IDs**.
The authorised JavaScript origin must include your dev origin (e.g. `http://localhost:3000`).

### 2. GIS script tag

Add the Google Identity Services loader to your `index.html` **before** your app bundle:

```html
<script src="https://accounts.google.com/gsi/client" async></script>
```

The `async` attribute is safe here: `useGoogleDriveAuth` initialises the token
client lazily on the first `getAccessToken()` call, giving the script time to load.

---

## Usage

### Step 1 — Acquire an OAuth token (React)

```tsx
import { useGoogleDriveAuth } from './hooks/useGoogleDriveAuth';

function MyComponent() {
  const { getAccessToken } = useGoogleDriveAuth();

  const handleSignIn = async () => {
    const token = await getAccessToken(); // triggers GIS consent / sign-in popup
    // store token for use in uploadFilesToDrive
  };
}
```

`getAccessToken()` returns a `Promise<string>` that resolves with a short-lived
OAuth access token scoped to `https://www.googleapis.com/auth/drive.file`
(the app can only access files it creates — no access to the user's existing Drive).

The hook is safe to call multiple times; each call routes to a fresh Promise.

### Step 2 — Upload files (framework-agnostic)

```ts
import { uploadFilesToDrive } from './lib/driveUploadFlow';

const results = await uploadFilesToDrive({
  token,                          // from getAccessToken()
  files,                          // File[] — .mp4 / .mov validated by the caller
  folderName: 'Open Stitch Uploads', // optional, this is the default
  onProgress: (file, status, meta) => {
    // status: 'uploading' | 'done' | 'error'
    // meta.id    — Drive file ID when status === 'done'
    // meta.error — error message  when status === 'error'
    console.log(file.name, status, meta);
  },
});

// results: Array<{ file, status: 'done'|'error', id?, error? }>
for (const r of results) {
  if (r.status === 'done') {
    console.log(`Uploaded: https://drive.google.com/file/d/${r.id}/view`);
  } else {
    console.error(`Failed: ${r.file.name} — ${r.error}`);
  }
}
```

`uploadFilesToDrive` uploads files **sequentially** (not in parallel) for reliability.
It only throws if folder creation fails; per-file errors are captured in the returned
result array so the full batch result is always available.

---

## File map

| File | Purpose |
|---|---|
| `src/types/gis.d.ts` | TypeScript declarations for the GIS global (`google.accounts.oauth2`) |
| `src/hooks/useGoogleDriveAuth.ts` | React hook — exposes `getAccessToken()` |
| `src/lib/drive.ts` | Low-level Drive API calls (folder creation, resumable upload) |
| `src/lib/driveUploadFlow.ts` | UI-agnostic orchestration — sequential upload loop + progress callbacks |
