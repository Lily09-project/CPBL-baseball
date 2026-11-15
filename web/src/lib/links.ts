/** Public repository links shown as methodology references (same URLs as README.md). */
export const REPO_URL = "https://github.com/Lily09-project/CPBL-baseball";
export const MODEL_CARD_URL = `${REPO_URL}/blob/main/docs/MODEL_CARD.md`;

/** Only http(s) URLs from data files become links; anything else (e.g. `javascript:`) is shown as text. */
export function safeExternalUrl(url: string): string | null {
  try {
    const { protocol } = new URL(url);
    return protocol === "https:" || protocol === "http:" ? url : null;
  } catch {
    return null;
  }
}
