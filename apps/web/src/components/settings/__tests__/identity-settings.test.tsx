import { render, screen } from "@testing-library/react";
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
  it("shows the account the session proved", () => {
    render(<IdentitySettings userEmail="u1@example.com" />);
    expect(screen.getByText("u1@example.com")).toBeInTheDocument();
  });

  it("states that nobody is signed in when there is no account", () => {
    render(<IdentitySettings userEmail={null} />);
    expect(screen.getByText("You are not signed in.")).toBeInTheDocument();
  });

  it("takes no address from the visitor - the account is not typed in", () => {
    render(<IdentitySettings userEmail="u1@example.com" />);
    // A field the visitor could fill in would be an assertion, and the
    // backend resolves the account from the session instead.
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Save" })).not.toBeInTheDocument();
  });

  it("states the sign-in methods the deployment carries", async () => {
    render(<IdentitySettings userEmail="u1@example.com" />);
    expect(await screen.findByText("E-mail + password")).toBeInTheDocument();
    expect(screen.getByText("Google")).toBeInTheDocument();
    expect(screen.queryByText("Apple")).not.toBeInTheDocument();
  });
});
