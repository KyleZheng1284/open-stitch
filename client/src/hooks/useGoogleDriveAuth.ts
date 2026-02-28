import { useRef, useCallback } from 'react';

const DRIVE_FILE_SCOPE = 'https://www.googleapis.com/auth/drive.file';

/**
 * Returns a stable `getAccessToken()` function that triggers the GIS OAuth
 * token flow and resolves with a short-lived access token scoped to
 * `drive.file` (access only to files this app creates).
 *
 * The token client is initialised lazily on the first call so the GIS script
 * has time to load via the async <script> tag in index.html.
 *
 * Requires VITE_GOOGLE_CLIENT_ID to be set in the environment.
 */
export function useGoogleDriveAuth() {
  const tokenClientRef = useRef<TokenClient | null>(null);

  const getAccessToken = useCallback((): Promise<string> => {
    return new Promise((resolve, reject) => {
      if (!window.google?.accounts?.oauth2) {
        reject(new Error('Google Identity Services script has not loaded yet.'));
        return;
      }

      const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined;
      if (!clientId) {
        reject(new Error('VITE_GOOGLE_CLIENT_ID is not set.'));
        return;
      }

      // Initialise the token client once and reuse it across calls.
      if (!tokenClientRef.current) {
        tokenClientRef.current = window.google.accounts.oauth2.initTokenClient({
          client_id: clientId,
          scope: DRIVE_FILE_SCOPE,
          callback: (response: TokenResponse) => {
            if (response.error) {
              reject(new Error(`OAuth error: ${response.error} — ${response.error_description ?? ''}`));
            } else {
              resolve(response.access_token);
            }
          },
          error_callback: (error: ClientConfigError) => {
            reject(new Error(`GIS error (${error.type}): ${error.message}`));
          },
        });
      }

      // prompt: '' reuses an existing session without a consent screen when
      // the token is still valid; shows the picker only when required.
      tokenClientRef.current.requestAccessToken({ prompt: '' });
    });
  }, []);

  return { getAccessToken };
}
