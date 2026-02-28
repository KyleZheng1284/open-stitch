import { useRef, useCallback } from 'react';

const DRIVE_FILE_SCOPE = 'https://www.googleapis.com/auth/drive.file';

/**
 * Returns a stable `getAccessToken()` function that triggers the GIS OAuth
 * token flow and resolves with a short-lived access token scoped to
 * `drive.file` (access only to files this app creates).
 *
 * Safe to call multiple times: each call creates a fresh Promise and routes
 * the GIS callback to that Promise's resolve/reject via mutable refs, avoiding
 * the closure-capture bug that occurs when the callback is bound to the first
 * Promise's resolve/reject at initTokenClient time.
 *
 * The token client itself is still initialised lazily on the first call so the
 * async GIS <script> tag in index.html has time to load.
 *
 * Requires VITE_GOOGLE_CLIENT_ID to be set in the environment.
 */
export function useGoogleDriveAuth() {
  const tokenClientRef = useRef<TokenClient | null>(null);
  // Mutable refs so the single stored callback always dispatches to the
  // resolve/reject of whichever Promise is currently in flight.
  const resolveRef = useRef<((token: string) => void) | null>(null);
  const rejectRef = useRef<((err: Error) => void) | null>(null);

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

      // Point the shared refs at this call's Promise before requesting.
      resolveRef.current = resolve;
      rejectRef.current = reject;

      if (!tokenClientRef.current) {
        tokenClientRef.current = window.google.accounts.oauth2.initTokenClient({
          client_id: clientId,
          scope: DRIVE_FILE_SCOPE,
          callback: (response: TokenResponse) => {
            if (response.error) {
              rejectRef.current?.(
                new Error(`OAuth error: ${response.error} — ${response.error_description ?? ''}`),
              );
            } else {
              resolveRef.current?.(response.access_token);
            }
          },
          error_callback: (error: ClientConfigError) => {
            rejectRef.current?.(new Error(`GIS error (${error.type}): ${error.message}`));
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
