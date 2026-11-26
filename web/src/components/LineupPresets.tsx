import { useId, useState } from "react";
import type { SavedLineup } from "../lib/router";

const STORAGE_KEY = "cpbl-lineup-presets-v1";
const LIMIT = 12;
const NAME_LIMIT = 40;

interface Preset extends SavedLineup {
  name: string;
  snapshot: string;
}

function readPresets(): Preset[] {
  try {
    const saved: unknown = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "[]");
    if (!Array.isArray(saved)) return [];
    return saved.filter((item): item is Preset =>
      item !== null && typeof item === "object" &&
      typeof item.name === "string" && item.name.trim().length > 0 && item.name.length <= NAME_LIMIT &&
      typeof item.snapshot === "string" && Array.isArray(item.ids) &&
      item.ids.length === 9 && item.ids.every((id: unknown) => typeof id === "string") &&
      (item.pitcher === undefined || typeof item.pitcher === "string"),
    ).slice(0, LIMIT);
  } catch {
    return [];
  }
}

export function LineupPresets({ snapshot, current, isValid, onLoad }: {
  snapshot: string;
  current: SavedLineup;
  isValid: (lineup: SavedLineup) => boolean;
  onLoad: (lineup: SavedLineup) => void;
}) {
  const nameId = useId();
  const [presets, setPresets] = useState(readPresets);
  const [draft, setDraft] = useState("");
  const [message, setMessage] = useState("");

  const save = (next: Preset[], status: string) => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      setPresets(next);
      setMessage(status);
      return true;
    } catch {
      setMessage("瀏覽器無法儲存打線。請檢查網站儲存設定。");
      return false;
    }
  };

  return (
    <details>
      <summary>我的打線</summary>
      <p className="muted">將上方打線儲存在這個瀏覽器，下次可以直接載入。</p>
      <form className="stack" onSubmit={(event) => {
        event.preventDefault();
        const name = draft.trim();
        if (!name) return;
        const latest = readPresets();
        if (latest.some((preset) => preset.name === name)) {
          setMessage("已有同名打線，請換個名稱。");
          return;
        }
        if (latest.length >= LIMIT) {
          setMessage("已存滿 12 組，請先移除一組。");
          return;
        }
        if (save([...latest, { ...current, name, snapshot }], `已儲存「${name}」。`)) setDraft("");
      }}>
        <label htmlFor={nameId}>打線名稱</label>
        <input className="input" id={nameId} value={draft} maxLength={NAME_LIMIT}
          onChange={(event) => setDraft(event.target.value)} />
        <button className="btn" type="submit" disabled={!draft.trim() || !isValid(current)}>儲存打線</button>
      </form>
      <p role="status">{message}</p>
      {presets.length > 0 && <ul className="stack">
        {presets.map((preset) => {
          const usable = preset.snapshot === snapshot && isValid(preset);
          return <li key={preset.name}>
            <strong>{preset.name}</strong>{!usable && <span> · 此快照無法使用</span>}
            <div className="row">
              <button className="btn" type="button" disabled={!usable} aria-label={`載入 ${preset.name}`}
                onClick={() => { onLoad(preset); setMessage(`已載入「${preset.name}」到上方編輯區。`); }}>載入</button>
              <button className="btn" type="button" aria-label={`移除 ${preset.name}`}
                onClick={() => {
                  // This row is about to disappear; keep keyboard focus inside the section.
                  document.getElementById(nameId)?.focus();
                  save(readPresets().filter((item) => item.name !== preset.name), `已移除「${preset.name}」。`);
                }}>移除</button>
            </div>
          </li>;
        })}
      </ul>}
    </details>
  );
}
