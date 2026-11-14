import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { Gate } from "./States";

afterEach(cleanup);

describe("Gate", () => {
  it("keeps the page heading while the data is loading", () => {
    render(<Gate<[number]> states={[{ status: "loading" }]} heading="季末戰績模擬">{() => <p>ready</p>}</Gate>);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("季末戰績模擬");
    expect(screen.getByRole("status")).toHaveTextContent("資料載入中");
  });

  it("keeps the page heading above a data error", () => {
    render(
      <Gate<[number]> states={[{ status: "error", error: new Error("無法載入 league.json（網路連線失敗）") }]} heading="資料可信度">
        {() => <p>ready</p>}
      </Gate>,
    );
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("資料可信度");
    expect(screen.getByRole("alert")).toHaveTextContent("無法載入 league.json（網路連線失敗）");
  });

  it("renders only the children once every dataset is ready", () => {
    render(<Gate<[number]> states={[{ status: "ready", data: 1 }]} heading="資料可信度">{(n) => <p>ready {n}</p>}</Gate>);
    expect(screen.queryByRole("heading", { level: 1 })).toBeNull();
    expect(screen.getByText("ready 1")).toBeInTheDocument();
  });
});
