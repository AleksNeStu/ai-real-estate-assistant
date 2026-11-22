import {
  comparePropertiesApi,
  priceAnalysisApi,
  locationAnalysisApi,
  valuationApi,
  legalCheckApi,
  enrichAddressApi,
  crmSyncContactApi,
} from "../api";

global.fetch = jest.fn(async () => {
  return {
    ok: true,
    statusText: "OK",
    headers: { get: () => null },
    json: async () => ({}),
    text: async () => "",
  } as unknown as Response;
}) as jest.Mock;

describe("api tools", () => {
  it("calls compare properties", async () => {
    await comparePropertiesApi(["a", "b"]);
    expect(global.fetch).toHaveBeenCalled();
  });
  it("calls price analysis", async () => {
    await priceAnalysisApi("Warsaw");
    expect(global.fetch).toHaveBeenCalled();
  });
  it("calls location analysis", async () => {
    await locationAnalysisApi("p1");
    expect(global.fetch).toHaveBeenCalled();
  });
  it("calls valuation", async () => {
    await valuationApi({ property_id: "p1" });
    expect(global.fetch).toHaveBeenCalled();
  });
  it("calls legal check", async () => {
    await legalCheckApi("text");
    expect(global.fetch).toHaveBeenCalled();
  });
  it("calls enrich address", async () => {
    await enrichAddressApi("addr");
    expect(global.fetch).toHaveBeenCalled();
  });
  it("calls crm sync contact", async () => {
    await crmSyncContactApi("name", "123", "e@e.com");
    expect(global.fetch).toHaveBeenCalled();
  });
});
