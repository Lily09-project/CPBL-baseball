import { describe, expect, it } from "vitest";
import { safeExternalUrl } from "./links";

describe("safeExternalUrl", () => {
  it("keeps http(s) links", () => {
    expect(safeExternalUrl("https://www.cpbl.com.tw/standings/season")).toBe("https://www.cpbl.com.tw/standings/season");
  });
  it("drops script, data and malformed URLs", () => {
    expect(safeExternalUrl("javascript:alert(1)")).toBeNull();
    expect(safeExternalUrl("data:text/html,x")).toBeNull();
    expect(safeExternalUrl("not a url")).toBeNull();
  });
});
