import { useEffect, useId, useMemo, useRef, useState } from "react";
import { useDataset, useRoute } from "../app/hooks";
import { searchPlayers } from "../lib/search";
import type { PlayerSummary } from "../lib/types";
import "./CommandPalette.css";

function usePlayersWhenOpened(open: boolean) {
  // The player index is ~200 KB, so it is fetched the first time the palette opens.
  const [requested, setRequested] = useState(open);
  if (open && !requested) setRequested(true);
  return requested;
}

/** Quick player search, opened with ⌘/Ctrl+K or "/". ARIA combobox pattern. */
export function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const requested = usePlayersWhenOpened(open);
  return <PaletteDialog open={open} onClose={onClose} load={requested} />;
}

function PaletteDialog({ open, onClose, load }: { open: boolean; onClose: () => void; load: boolean }) {
  const players = useDataset(load ? "players.json" : null);
  const [, navigate] = useRoute();
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const dialog = useRef<HTMLDialogElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const listId = useId();

  const results = useMemo<PlayerSummary[]>(
    () => (players.status === "ready" && players.data ? searchPlayers(players.data, query, 8) : []),
    [players, query],
  );

  useEffect(() => {
    const node = dialog.current;
    if (!node) return;
    if (open && !node.open) {
      node.showModal();
      setQuery("");
      setActive(0);
      requestAnimationFrame(() => input.current?.focus());
    } else if (!open && node.open) {
      node.close();
    }
  }, [open]);

  const choose = (player: PlayerSummary | undefined) => {
    if (!player) return;
    navigate({ name: "player", type: player.type, id: player.player_id });
    onClose();
  };

  return (
    <dialog ref={dialog} className="palette" aria-label="搜尋球員" onClose={onClose} onCancel={onClose}>
      <div className="palette-body">
        <label htmlFor={`${listId}-input`} className="visually-hidden">
          輸入球員或球隊名稱
        </label>
        <input
          ref={input}
          id={`${listId}-input`}
          className="input palette-input"
          role="combobox"
          aria-expanded={results.length > 0}
          aria-controls={listId}
          aria-activedescendant={results[active] ? `${listId}-${active}` : undefined}
          aria-autocomplete="list"
          placeholder="搜尋球員或球隊，例如：郭天信、味全"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setActive(0);
          }}
          onKeyDown={(e) => {
            if (e.key === "ArrowDown") {
              e.preventDefault();
              setActive((a) => Math.min(a + 1, Math.max(results.length - 1, 0)));
            } else if (e.key === "ArrowUp") {
              e.preventDefault();
              setActive((a) => Math.max(a - 1, 0));
            } else if (e.key === "Enter") {
              e.preventDefault();
              choose(results[active]);
            }
          }}
        />
        <ul id={listId} role="listbox" className="palette-list" aria-label="搜尋結果">
          {results.map((p, i) => (
            <li
              key={`${p.type}-${p.player_id}`}
              id={`${listId}-${i}`}
              role="option"
              aria-selected={i === active}
              className="palette-option"
              onMouseEnter={() => setActive(i)}
              onClick={() => choose(p)}
            >
              <span className="palette-name">{p.name}</span>
              <span className="muted">
                {p.team}・{p.type === "batter" ? "打者" : "投手"}
                {!p.qualified && "・小樣本"}
              </span>
            </li>
          ))}
        </ul>
        {query && results.length === 0 && <p className="palette-empty muted">找不到符合「{query}」的球員。</p>}
        <p className="palette-hint muted">↑↓ 選擇・Enter 開啟・Esc 關閉</p>
      </div>
    </dialog>
  );
}
