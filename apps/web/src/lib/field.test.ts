import { expect, it } from "vitest";
import { currentAge, localGateway } from "./field";
it("allows only explicit local gateway origins", () => {
  expect(localGateway("http://127.0.0.1:8765")).toBe("http://127.0.0.1:8765");
  expect(localGateway("https://192.168.1.4:8765")).toContain("192.168.1.4");
  for (const value of [
    "http://192.168.1.4:8765",
    "https://example.com",
    "http://10.evil.test",
    "http://user:pass@localhost",
    "http://localhost/file",
    "http://8.8.8.8",
  ])
    expect(() => localGateway(value)).toThrow();
});
it("ages results without subtracting unrelated monotonic clocks", () => {
  expect(currentAge("100000000", 1000, 1200, 50)).toBe(350);
  expect(() => currentAge("100", 200, 100, 2)).toThrow();
});
