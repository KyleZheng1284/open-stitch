// Type declarations for Google Identity Services (GIS) OAuth token client.
// Sourced from: https://developers.google.com/identity/oauth2/web/reference/js-reference

interface TokenResponse {
  access_token: string;
  expires_in: number;
  scope: string;
  token_type: string;
  error?: string;
  error_description?: string;
  error_uri?: string;
}

interface ClientConfigError {
  type: string;
  message: string;
}

interface TokenClientConfig {
  client_id: string;
  scope: string;
  callback: (response: TokenResponse) => void;
  error_callback?: (error: ClientConfigError) => void;
  prompt?: string;
}

interface TokenClient {
  requestAccessToken(overrideConfig?: { prompt?: string }): void;
}

declare namespace google.accounts.oauth2 {
  function initTokenClient(config: TokenClientConfig): TokenClient;
  function revoke(accessToken: string, done?: () => void): void;
}
