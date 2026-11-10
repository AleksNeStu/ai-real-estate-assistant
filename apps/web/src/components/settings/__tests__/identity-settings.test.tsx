import { fireEvent, render, screen } from "@testing-library/react";
import { IdentitySettings } from "../identity-settings";

jest.mock("@/hooks/useCapabilities", () => ({
  useCapabilities: () => ({
    capabilities: {
      auth: { jwt_enabled: true, demo_user_bypass: false, oauth: { google: true, apple: false } },
    },
    loading: false,
  }),
}));

describe("IdentitySettings", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("loads email from localStorage", async () => {
    window.localStorage.setItem("userEmail", "u1@example.com");
    render(<IdentitySettings />);
    const input = await screen.findByLabelText("Email");
    expect((input as HTMLInputElement).value).toBe("u1@example.com");
  });

  it("saves a valid email and triggers onChange", async () => {
    const onChange = jest.fn();
    render(<IdentitySettings onChange={onChange} />);

    const input = await screen.findByLabelText("Email");
    fireEvent.change(input, { target: { value: "new@example.com" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(window.localStorage.getItem("userEmail")).toBe("new@example.com");
    expect(onChange).toHaveBeenCalledWith("new@example.com");
    expect(screen.getByText("Email saved.")).toBeInTheDocument();
  });

  it("shows validation error for invalid email", async () => {
    render(<IdentitySettings />);

    const input = await screen.findByLabelText("Email");
    fireEvent.change(input, { target: { value: "not-an-email" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(window.localStorage.getItem("userEmail")).toBeNull();
    expect(screen.getByText("Please enter a valid email address.")).toBeInTheDocument();
  });

  it("states the sign-in methods the deployment carries", async () => {
    render(<IdentitySettings />);
    expect(await screen.findByText("E-mail + password")).toBeInTheDocument();
    expect(screen.getByText("Google")).toBeInTheDocument();
    expect(screen.queryByText("Apple")).not.toBeInTheDocument();
  });

  it("clears email when input is empty", async () => {
    window.localStorage.setItem("userEmail", "u1@example.com");
    const onChange = jest.fn();
    render(<IdentitySettings onChange={onChange} />);

    const input = await screen.findByLabelText("Email");
    fireEvent.change(input, { target: { value: "" } });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    expect(window.localStorage.getItem("userEmail")).toBeNull();
    expect(onChange).toHaveBeenCalledWith(null);
    expect(screen.getByText("Email cleared.")).toBeInTheDocument();
  });
});
