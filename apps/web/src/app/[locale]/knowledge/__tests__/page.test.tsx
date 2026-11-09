import "@testing-library/jest-dom";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import KnowledgePage from "../page";
import { ragQa, resetRagKnowledge, uploadRagDocuments } from "@/lib/api";

jest.mock("@/lib/api", () => {
  class MockApiError extends Error {
    constructor(message: string, public status: number, public request_id?: string) {
      super(message);
      this.name = "ApiError";
    }
  }
  return {
    uploadRagDocuments: jest.fn(async () => ({
      message: "Upload processed",
      chunks_indexed: 3,
      errors: [],
    })),
    resetRagKnowledge: jest.fn(async () => ({
      message: "Knowledge cleared",
      documents_removed: 0,
      documents_remaining: 0,
    })),
    ragQa: jest.fn(async () => ({
      answer: "Answer text",
      citations: [{ source: "file.txt", chunk_index: 0 }],
      llm_used: false,
      provider: null,
      model: null,
    })),
    ApiError: MockApiError,
  };
});

describe("KnowledgePage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders and validates inputs", async () => {
    render(<KnowledgePage />);

    expect(screen.getByText("Knowledge")).toBeInTheDocument();

    // Upload button should be disabled when no files are selected
    expect(screen.getByRole("button", { name: "Upload" })).toBeDisabled();

    // Ask button should be disabled when no question is entered
    expect(screen.getByRole("button", { name: "Ask" })).toBeDisabled();
  });

  it("uploads a file and asks a question", async () => {
    render(<KnowledgePage />);

    const fileInput = screen.getByLabelText("Knowledge files") as HTMLInputElement;
    const file = new File(["hello"], "file.txt", { type: "text/plain" });

    fireEvent.change(fileInput, { target: { files: [file] } });

    fireEvent.click(screen.getByRole("button", { name: "Upload" }));
    await waitFor(() => expect(screen.getByText("Upload processed")).toBeInTheDocument());
    expect(screen.getByText("Chunks indexed: 3")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Knowledge question"), { target: { value: "What is in the file?" } });
    fireEvent.click(screen.getByRole("button", { name: "Ask" }));

    await waitFor(() => expect(screen.getByText("Answer text")).toBeInTheDocument());
    // The passage ledger names the document and the place in it.
    expect(screen.getByText("file.txt · chunk 0")).toBeInTheDocument();
  });

  it("clamps top_k and trims provider/model", async () => {
    render(<KnowledgePage />);

    fireEvent.change(screen.getByLabelText("Top K"), { target: { value: "999" } });
    fireEvent.change(screen.getByLabelText("Provider override"), { target: { value: " openai " } });
    fireEvent.change(screen.getByLabelText("Model override"), { target: { value: " gpt-4o " } });
    fireEvent.change(screen.getByLabelText("Knowledge question"), { target: { value: "Q" } });
    fireEvent.click(screen.getByRole("button", { name: "Ask" }));

    await waitFor(() => expect(ragQa).toHaveBeenCalled());
    expect((ragQa as jest.Mock).mock.calls[0][0]).toEqual({
      question: "Q",
      top_k: 50,
      provider: "openai",
      model: "gpt-4o",
    });
  });

  it("asks for the default top_k when the slider is untouched", async () => {
    render(<KnowledgePage />);

    fireEvent.change(screen.getByLabelText("Knowledge question"), { target: { value: "Q" } });
    fireEvent.click(screen.getByRole("button", { name: "Ask" }));

    await waitFor(() => expect(ragQa).toHaveBeenCalled());
    expect((ragQa as jest.Mock).mock.calls[0][0]).toEqual({
      question: "Q",
      top_k: 5,
      provider: undefined,
      model: undefined,
    });
  });

  it("surfaces upload and QA failures", async () => {
    (uploadRagDocuments as jest.Mock).mockRejectedValueOnce(new Error("Upload failed (status=500)"));
    (ragQa as jest.Mock).mockRejectedValueOnce(new Error("QA failed (status=503)"));

    render(<KnowledgePage />);

    const fileInput = screen.getByLabelText("Knowledge files") as HTMLInputElement;
    fireEvent.change(fileInput, { target: { files: [new File(["x"], "file.txt", { type: "text/plain" })] } });

    fireEvent.click(screen.getByRole("button", { name: "Upload" }));
    await waitFor(() => expect(screen.getByText(/Upload failed.*status=500/)).toBeInTheDocument());

    fireEvent.change(screen.getByLabelText("Knowledge question"), { target: { value: "Q" } });
    fireEvent.click(screen.getByRole("button", { name: "Ask" }));
    await waitFor(() => expect(screen.getByText(/QA failed.*status=503/)).toBeInTheDocument());
  });

  it("clears knowledge after confirmation", async () => {
    const confirmSpy = jest.spyOn(window, "confirm").mockReturnValue(true);
    (resetRagKnowledge as jest.Mock).mockResolvedValueOnce({
      message: "Knowledge cleared",
      documents_removed: 3,
      documents_remaining: 0,
    });

    render(<KnowledgePage />);

    fireEvent.click(screen.getByRole("button", { name: /Clear Knowledge/i }));
    await waitFor(() => expect(resetRagKnowledge).toHaveBeenCalled());
    expect(screen.getByText(/Knowledge cleared\. Removed 3\. Remaining 0\./)).toBeInTheDocument();

    confirmSpy.mockRestore();
  });

  it("does not clear knowledge when confirmation is cancelled", async () => {
    const confirmSpy = jest.spyOn(window, "confirm").mockReturnValue(false);

    render(<KnowledgePage />);

    fireEvent.click(screen.getByRole("button", { name: /Clear Knowledge/i }));
    await waitFor(() => expect(confirmSpy).toHaveBeenCalled());
    expect(resetRagKnowledge).not.toHaveBeenCalled();

    confirmSpy.mockRestore();
  });

  it("surfaces reset failures", async () => {
    const confirmSpy = jest.spyOn(window, "confirm").mockReturnValue(true);
    (resetRagKnowledge as jest.Mock).mockRejectedValueOnce(new Error("Reset failed (status=503)"));

    render(<KnowledgePage />);

    fireEvent.click(screen.getByRole("button", { name: /Clear Knowledge/i }));
    await waitFor(() => expect(screen.getByText(/Reset failed.*status=503/)).toBeInTheDocument());

    confirmSpy.mockRestore();
  });
});
