import {
  ModelProviderCatalog,
  MortgageResult,
  NotificationSettings,
} from "../types";
import {
  ApiError,
  calculateMortgage,
  chatMessage,
  getModelsCatalog,
  getNotificationSettings,
  ragQa,
  searchProperties,
  streamChatMessage,
  uploadRagDocuments,
  updateNotificationSettings,
} from "../api";
import { TextEncoder, TextDecoder } from 'util';

global.fetch = jest.fn();

// Polyfill for TextEncoder/TextDecoder if missing in test env
if (typeof global.TextEncoder === 'undefined') {
    (global as unknown as { TextEncoder?: typeof TextEncoder }).TextEncoder = TextEncoder;
    (global as unknown as { TextDecoder?: typeof TextDecoder }).TextDecoder = TextDecoder;
}

describe("API Client", () => {
  beforeEach(() => {
    jest.resetAllMocks();
    (global.fetch as jest.Mock) = jest.fn();
    window.localStorage.clear();
  });

  describe("Notification Settings", () => {
    const mockSettings: NotificationSettings = {
      email_digest: true,
      frequency: "weekly",
      expert_mode: false,
      marketing_emails: false,
    };

    it("never sends an asserted identity - the session names the account", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockSettings,
      });

      await getNotificationSettings();

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/settings/notifications"),
        expect.objectContaining({
          method: "GET",
          headers: expect.objectContaining({
            "Content-Type": "application/json",
          }),
        })
      );

      const [, options] = (global.fetch as jest.Mock).mock.calls[0];
      expect(options.headers["X-User-Email"]).toBeUndefined();
    });

    it("sends no identity header when running without window", async () => {
      const globalWithWindow = globalThis as unknown as { window?: unknown };
      const originalWindow = globalWithWindow.window;
      delete globalWithWindow.window;

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockSettings,
      });

      await getNotificationSettings();

      const [, options] = (global.fetch as jest.Mock).mock.calls[0];
      expect(options.headers["X-User-Email"]).toBeUndefined();

      globalWithWindow.window = originalWindow;
    });

    it("fetches settings", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockSettings,
      });

      const result = await getNotificationSettings();

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/settings/notifications"),
        expect.objectContaining({
          method: "GET",
        })
      );
      expect(result).toEqual(mockSettings);
    });

    it("updates settings", async () => {
      const newSettings = { ...mockSettings, frequency: "daily" as const };
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => newSettings,
      });

      const result = await updateNotificationSettings(newSettings);

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/settings/notifications"),
        expect.objectContaining({
          method: "PUT",
          body: JSON.stringify(newSettings),
        })
      );
      expect(result).toEqual(newSettings);
    });
  });

  describe("calculateMortgage", () => {
    it("calls /tools/mortgage-calculator endpoint", async () => {
      const mockResult: MortgageResult = {
        monthly_payment: 2500,
        total_interest: 400000,
        total_cost: 900000,
        down_payment: 100000,
        loan_amount: 400000,
        breakdown: { principal: 1000, interest: 1500 },
      };

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResult,
      });

      const input = {
        property_price: 500000,
        down_payment_percent: 20,
        interest_rate: 4.5,
        loan_years: 30,
      };

      const result = await calculateMortgage(input);

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/tools/mortgage-calculator"),
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify(input),
        })
      );
      expect(result).toEqual(mockResult);
    });
  });

  describe("getModelsCatalog", () => {
    it("calls /settings/models endpoint", async () => {
      const mockCatalog: ModelProviderCatalog[] = [
        {
          name: "openai",
          display_name: "OpenAI",
          is_local: false,
          requires_api_key: true,
          models: [],
        },
      ];

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockCatalog,
      });

      const result = await getModelsCatalog();

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/settings/models"),
        expect.objectContaining({
          method: "GET",
        })
      );
      expect(result).toEqual(mockCatalog);
    });
  });

  describe("searchProperties", () => {
    it("calls /search endpoint", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ results: [] }),
      });

      await searchProperties({ query: "test" });

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/search"),
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ query: "test" }),
        })
      );
    });

    it("throws ApiError with detail, status, and request_id on failure", async () => {
        const mockResponse = {
            ok: false,
            status: 400,
            statusText: "Bad Request",
            text: async () => JSON.stringify({ detail: "Invalid query" }),
            json: async () => ({ detail: "Invalid query" }),
            headers: { get: (name: string) => (name === "X-Request-ID" ? "req-abc-123" : null) },
        };
        (global.fetch as jest.Mock).mockResolvedValueOnce(mockResponse as unknown as Response);

        try {
          await searchProperties({ query: "" });
        } catch (e) {
          expect(e).toBeInstanceOf(ApiError);
          if (e instanceof ApiError) {
            expect(e.message).toBe("Invalid query");
            expect(e.status).toBe(400);
            expect(e.request_id).toBe("req-abc-123");
          }
        }
    });

    it("throws ApiError with status and request_id when detail parsing fails", async () => {
        const mockResponse = {
            ok: false,
            status: 500,
            statusText: "Server Error",
            text: async () => "Server Error",
            json: async () => { throw new Error("JSON parse error"); },
            headers: { get: (name: string) => (name === "X-Request-ID" ? "req-xyz-789" : null) },
        };
        (global.fetch as jest.Mock).mockResolvedValueOnce(mockResponse as unknown as Response);

        try {
          await searchProperties({ query: "" });
        } catch (e) {
          expect(e).toBeInstanceOf(ApiError);
          if (e instanceof ApiError) {
            expect(e.message).toBe("Server Error");
            expect(e.status).toBe(500);
            expect(e.request_id).toBe("req-xyz-789");
          }
        }
    });

    it("throws ApiError with default message if text is empty", async () => {
        const mockResponse = {
            ok: false,
            status: 503,
            statusText: "Service Unavailable",
            text: async () => "",
            json: async () => { throw new Error(); },
            headers: { get: () => null },
        };
        (global.fetch as jest.Mock).mockResolvedValueOnce(mockResponse as unknown as Response);

        try {
          await searchProperties({ query: "" });
        } catch (e) {
          expect(e).toBeInstanceOf(ApiError);
          if (e instanceof ApiError) {
            expect(e.message).toBe("API request failed");
            expect(e.status).toBe(503);
            expect(e.request_id).toBeUndefined();
          }
        }
    });

    it("throws ApiError without request_id when X-Request-ID header missing", async () => {
        const mockResponse = {
            ok: false,
            status: 404,
            statusText: "Not Found",
            text: async () => JSON.stringify({ detail: "Resource not found" }),
            json: async () => ({ detail: "Resource not found" }),
            headers: { get: () => null },
        };
        (global.fetch as jest.Mock).mockResolvedValueOnce(mockResponse as unknown as Response);

        try {
          await searchProperties({ query: "" });
        } catch (e) {
          expect(e).toBeInstanceOf(ApiError);
          if (e instanceof ApiError) {
            expect(e.message).toBe("Resource not found");
            expect(e.status).toBe(404);
            expect(e.request_id).toBeUndefined();
          }
        }
    });
  });

  describe("chatMessage", () => {
    it("calls /chat endpoint", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ response: "Hello" }),
      });

      await chatMessage({ message: "hi" });

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/chat"),
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ message: "hi" }),
        })
      );
    });
  });

  describe("RAG", () => {
    it("uploads files without forcing JSON content type", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ message: "Upload processed", chunks_indexed: 1, errors: [] }),
      });

      const file = new File(["hello"], "hello.txt", { type: "text/plain" });
      await uploadRagDocuments([file]);

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/rag/upload"),
        expect.objectContaining({
          method: "POST",
        })
      );

      const [, options] = (global.fetch as jest.Mock).mock.calls[0];
      expect(options.headers["X-User-Email"]).toBeUndefined();
      expect(options.headers["Content-Type"]).toBeUndefined();

      const body = options.body as FormData;
      expect(body).toBeInstanceOf(FormData);
      expect(body.getAll("files")).toHaveLength(1);
    });

    it("calls /rag/qa endpoint", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ answer: "A", citations: [], llm_used: false, provider: null, model: null }),
      });

      await ragQa({ question: "What is this?", top_k: 3 });

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/rag/qa"),
        expect.objectContaining({
          method: "POST",
          headers: expect.objectContaining({
            "Content-Type": "application/json",
          }),
          body: JSON.stringify({ question: "What is this?", top_k: 3 }),
        })
      );
    });
  });

  describe("streamChatMessage", () => {
      it("handles streaming response", async () => {
          const encoder = new TextEncoder();
          const mockReader = {
              read: jest.fn()
                  .mockResolvedValueOnce({ done: false, value: encoder.encode("data: Chunk 1\n\n") })
                  .mockResolvedValueOnce({ done: false, value: encoder.encode("data: Chunk 2\n\n") })
                  .mockResolvedValueOnce({ done: false, value: encoder.encode("data: [DONE]\n\n") })
                  .mockResolvedValueOnce({ done: true, value: undefined })
          };

          (global.fetch as jest.Mock).mockResolvedValueOnce({
              ok: true,
              headers: { get: () => "req-xyz" },
              text: async () => "",
              body: {
                  getReader: () => mockReader
              }
          });

          const onChunk = jest.fn();
          await streamChatMessage({ message: "stream" }, onChunk);

          expect(onChunk).toHaveBeenCalledTimes(2);
          expect(onChunk).toHaveBeenCalledWith("Chunk 1");
          expect(onChunk).toHaveBeenCalledWith("Chunk 2");
      });

      it("throws if body is missing", async () => {
          (global.fetch as jest.Mock).mockResolvedValueOnce({
              ok: true,
              headers: { get: () => "req-123" },
              text: async () => "",
              body: null
          });

          await expect(streamChatMessage({ message: "test" }, jest.fn()))
              .rejects.toThrow("Failed to start stream");
      });
  });
});
