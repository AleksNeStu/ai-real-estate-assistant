import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ModelSettings } from "../model-settings";
import { getModelPreferences, updateModelPreferences } from "@/lib/api";
import type { ModelProviderCatalog } from "@/lib/types";

jest.mock("@/lib/api", () => ({
  getModelPreferences: jest.fn(),
  updateModelPreferences: jest.fn(),
}));

const catalog: ModelProviderCatalog[] = [
  {
    name: "openai",
    display_name: "OpenAI",
    is_local: false,
    requires_api_key: true,
    models: [
      {
        id: "model-a",
        display_name: "Model A",
        provider_name: "OpenAI",
        context_window: 1,
        pricing: null,
        capabilities: [],
        description: null,
        recommended_for: [],
      },
      {
        id: "model-b",
        display_name: "Model B",
        provider_name: "OpenAI",
        context_window: 1,
        pricing: null,
        capabilities: [],
        description: null,
        recommended_for: [],
      },
    ],
    runtime_available: null,
    available_models: null,
    runtime_error: null,
  },
  {
    name: "ollama",
    display_name: "Ollama",
    is_local: true,
    requires_api_key: false,
    models: [
      {
        id: "model-c",
        display_name: "Model C",
        provider_name: "Ollama",
        context_window: 1,
        pricing: null,
        capabilities: [],
        description: null,
        recommended_for: [],
      },
    ],
    runtime_available: true,
    available_models: ["model-c"],
    runtime_error: null,
  },
];

describe("ModelSettings", () => {
  beforeEach(() => {
    jest.resetAllMocks();
    window.localStorage.clear();
  });

  it("asks for a session when there is no account", async () => {
    (getModelPreferences as jest.Mock).mockResolvedValue({ preferred_provider: null, preferred_model: null });
    render(<ModelSettings catalog={catalog} userEmail={null} />);
    await waitFor(() => {
      expect(screen.getByText(/Sign in to choose a default model/i)).toBeInTheDocument();
    });
  });

  it("loads preferences from API and persists to localStorage", async () => {
    (getModelPreferences as jest.Mock).mockResolvedValue({ preferred_provider: "openai", preferred_model: "model-b" });
    render(<ModelSettings catalog={catalog} userEmail={"u1@example.com"} />);

    await waitFor(() => {
      expect(screen.getByLabelText("Provider")).toBeInTheDocument();
    });

    const providerSelect = screen.getByLabelText("Provider") as HTMLSelectElement;
    const modelSelect = screen.getByLabelText("Model") as HTMLSelectElement;
    expect(providerSelect.value).toBe("openai");
    expect(modelSelect.value).toBe("model-b");
    expect(window.localStorage.getItem("modelPrefs:u1@example.com")).toContain('"preferred_provider":"openai"');
  });

  it("saves preferences via API and persists locally", async () => {
    (getModelPreferences as jest.Mock).mockResolvedValue({ preferred_provider: "openai", preferred_model: "model-a" });
    (updateModelPreferences as jest.Mock).mockImplementation(async (p) => p);

    render(<ModelSettings catalog={catalog} userEmail={"u1@example.com"} />);

    await waitFor(() => {
      expect(screen.getByLabelText("Provider")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("Provider"), { target: { value: "ollama" } });
    fireEvent.change(screen.getByLabelText("Model"), { target: { value: "model-c" } });

    fireEvent.click(screen.getByRole("button", { name: "Save Default Model" }));

    await waitFor(() => {
      expect(updateModelPreferences).toHaveBeenCalledWith({
        preferred_provider: "ollama",
        preferred_model: "model-c",
      });
      expect(screen.getByText("Default model saved.")).toBeInTheDocument();
    });

    const raw = window.localStorage.getItem("modelPrefs:u1@example.com");
    expect(raw).toContain('"preferred_provider":"ollama"');
    expect(raw).toContain('"preferred_model":"model-c"');
  });

  it("shows runtime error for local providers when unavailable", async () => {
    (getModelPreferences as jest.Mock).mockResolvedValue({ preferred_provider: "openai", preferred_model: "model-a" });
    const downCatalog: ModelProviderCatalog[] = catalog.map((p) =>
      p.name === "ollama"
        ? {
            ...p,
            runtime_available: false,
            available_models: [],
            runtime_error: "Ollama is installed but not running. Start it with 'ollama serve'",
          }
        : p
    );

    render(<ModelSettings catalog={downCatalog} userEmail={"u1@example.com"} />);

    await waitFor(() => {
      expect(screen.getByLabelText("Provider")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("Provider"), { target: { value: "ollama" } });

    expect(screen.getByText("Local runtime: unavailable.")).toBeInTheDocument();
    expect(
      screen.getByText("Ollama is installed but not running. Start it with 'ollama serve'")
    ).toBeInTheDocument();
  });

  it("shows error message when loading preferences fails", async () => {
    const errorSpy = jest.spyOn(console, "error").mockImplementation(() => {});
    (getModelPreferences as jest.Mock).mockRejectedValueOnce(new Error("API Error"));

    render(<ModelSettings catalog={catalog} userEmail={"u1@example.com"} />);

    await waitFor(() => {
      expect(screen.getByText("Failed to load model preferences. Using local preferences.")).toBeInTheDocument();
    });
    expect(errorSpy).not.toHaveBeenCalled();
    errorSpy.mockRestore();
  });

  it("shows error message when saving preferences fails", async () => {
    const errorSpy = jest.spyOn(console, "error").mockImplementation(() => {});
    (getModelPreferences as jest.Mock).mockResolvedValue({ preferred_provider: "openai", preferred_model: "model-a" });
    (updateModelPreferences as jest.Mock).mockRejectedValueOnce(new Error("Save failed"));

    render(<ModelSettings catalog={catalog} userEmail={"u1@example.com"} />);

    await waitFor(() => {
      expect(screen.getByLabelText("Provider")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("Provider"), { target: { value: "ollama" } });
    fireEvent.change(screen.getByLabelText("Model"), { target: { value: "model-c" } });
    fireEvent.click(screen.getByRole("button", { name: "Save Default Model" }));

    await waitFor(() => {
      expect(screen.getByText("Failed to save default model. Please try again.")).toBeInTheDocument();
    });

    expect(errorSpy).not.toHaveBeenCalled();
    errorSpy.mockRestore();
  });
});
