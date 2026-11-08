/**
 * Tests for NeighborhoodBadge component
 */

import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "@jest/globals";
import {
  NeighborhoodBadge,
  NeighborhoodBadgeCircle,
  NeighborhoodScoreDisplay,
} from "../neighborhood-badge";

describe("NeighborhoodBadge", () => {
  describe("NeighborhoodBadge", () => {
    it("renders the score correctly", () => {
      render(<NeighborhoodBadge overallScore={75.5} />);
      expect(screen.getByText("75.5")).toBeInTheDocument();
    });

    it("shows label when showLabel is true", () => {
      render(<NeighborhoodBadge overallScore={75.5} showLabel={true} />);
      expect(screen.getByText("75.5")).toBeInTheDocument();
      expect(screen.getByText("Good")).toBeInTheDocument();
    });

    it("hides label when showLabel is false", () => {
      render(<NeighborhoodBadge overallScore={75.5} showLabel={false} />);
      expect(screen.getByText("75.5")).toBeInTheDocument();
      expect(screen.queryByText("Good")).not.toBeInTheDocument();
    });

    it("applies correct color for excellent score (85+)", () => {
      const { container } = render(<NeighborhoodBadge overallScore={90} />);
      // Color class is on the inner span, not container
      const scoreSpan = container.querySelector("span.text-success");
      expect(scoreSpan).toBeInTheDocument();
      expect(container.firstChild).toHaveClass("bg-success/10");
    });

    it("applies correct color for good score (70-84)", () => {
      const { container } = render(<NeighborhoodBadge overallScore={75} />);
      const scoreSpan = container.querySelector("span.text-chart-7");
      expect(scoreSpan).toBeInTheDocument();
      expect(container.firstChild).toHaveClass("bg-chart-7/10");
    });

    it("applies correct color for fair score (55-69)", () => {
      const { container } = render(<NeighborhoodBadge overallScore={60} />);
      const scoreSpan = container.querySelector("span.text-warning");
      expect(scoreSpan).toBeInTheDocument();
      expect(container.firstChild).toHaveClass("bg-warning/10");
    });

    it("applies correct color for poor score (40-54)", () => {
      const { container } = render(<NeighborhoodBadge overallScore={45} />);
      const scoreSpan = container.querySelector("span.text-caution");
      expect(scoreSpan).toBeInTheDocument();
      expect(container.firstChild).toHaveClass("bg-caution/10");
    });

    it("applies correct color for very poor score (<40)", () => {
      const { container } = render(<NeighborhoodBadge overallScore={30} />);
      const scoreSpan = container.querySelector("span.text-destructive");
      expect(scoreSpan).toBeInTheDocument();
      expect(container.firstChild).toHaveClass("bg-destructive/10");
    });

    it("applies custom className", () => {
      const { container } = render(
        <NeighborhoodBadge overallScore={75} className="custom-class" />
      );
      expect(container.firstChild).toHaveClass("custom-class");
    });

    it("applies size classes correctly", () => {
      const { container: smContainer } = render(
        <NeighborhoodBadge overallScore={75} size="sm" />
      );
      const { container: mdContainer } = render(
        <NeighborhoodBadge overallScore={75} size="md" />
      );
      const { container: lgContainer } = render(
        <NeighborhoodBadge overallScore={75} size="lg" />
      );

      expect(smContainer.firstChild).toHaveClass("text-xs");
      expect(mdContainer.firstChild).toHaveClass("text-xs");
      expect(lgContainer.firstChild).toHaveClass("text-sm");
    });

    it("has proper title attribute for accessibility", () => {
      render(<NeighborhoodBadge overallScore={90} />);
      const badge = screen.getByText("90.0").closest("div");
      // Integer scores show as "90/100", not "90.0/100"
      expect(badge).toHaveAttribute(
        "title",
        "Neighborhood Quality: Excellent (90/100)"
      );
    });
  });

  describe("NeighborhoodBadgeCircle", () => {
    it("renders score as a circle", () => {
      render(<NeighborhoodBadgeCircle overallScore={75} />);
      expect(screen.getByText("75")).toBeInTheDocument();
    });

    it("rounds the score", () => {
      render(<NeighborhoodBadgeCircle overallScore={75.7} />);
      expect(screen.getByText("76")).toBeInTheDocument();
    });

    it("applies correct background color for excellent score", () => {
      const { container } = render(<NeighborhoodBadgeCircle overallScore={90} />);
      expect(container.firstChild).toHaveClass("bg-success");
    });

    it("applies correct background color for good score", () => {
      const { container } = render(<NeighborhoodBadgeCircle overallScore={75} />);
      expect(container.firstChild).toHaveClass("bg-chart-7");
    });

    it("applies correct background color for fair score", () => {
      const { container } = render(<NeighborhoodBadgeCircle overallScore={60} />);
      expect(container.firstChild).toHaveClass("bg-warning");
    });

    it("applies correct background color for poor score", () => {
      const { container } = render(<NeighborhoodBadgeCircle overallScore={45} />);
      expect(container.firstChild).toHaveClass("bg-caution");
    });

    it("applies correct background color for very poor score", () => {
      const { container } = render(<NeighborhoodBadgeCircle overallScore={30} />);
      expect(container.firstChild).toHaveClass("bg-destructive");
    });

    it("has proper title attribute", () => {
      render(<NeighborhoodBadgeCircle overallScore={75.5} />);
      // The circle rounds the score: 75.5 -> 76
      const badge = screen.getByText("76").closest("div");
      expect(badge).toHaveAttribute("title", "Neighborhood Quality: 75.5/100");
    });
  });

  describe("NeighborhoodScoreDisplay", () => {
    const mockResult = {
      overall_score: 75,
      safety_score: 80,
      schools_score: 70,
      amenities_score: 75,
      walkability_score: 72,
      green_space_score: 68,
    };

    it("renders overall score badge", () => {
      render(<NeighborhoodScoreDisplay result={mockResult} />);
      expect(screen.getByText("Overall Score")).toBeInTheDocument();
      // There are multiple "75.0" elements (badge + amenities), so we check count
      expect(screen.getAllByText("75.0")).toHaveLength(2);
    });

    it("renders all component scores in non-compact mode", () => {
      render(<NeighborhoodScoreDisplay result={mockResult} compact={false} />);
      expect(screen.getByText("Safety")).toBeInTheDocument();
      expect(screen.getByText("Schools")).toBeInTheDocument();
      expect(screen.getByText("Amenities")).toBeInTheDocument();
      expect(screen.getByText("Walkability")).toBeInTheDocument();
      expect(screen.getByText("Green Space")).toBeInTheDocument();
    });

    it("does not render component scores in compact mode", () => {
      render(<NeighborhoodScoreDisplay result={mockResult} compact={true} />);
      expect(screen.getByText("Overall Score")).toBeInTheDocument();
      expect(screen.queryByText("Safety")).not.toBeInTheDocument();
    });

    it("displays correct component scores", () => {
      render(<NeighborhoodScoreDisplay result={mockResult} compact={false} />);
      expect(screen.getByText("80.0")).toBeInTheDocument(); // safety
      expect(screen.getByText("70.0")).toBeInTheDocument(); // schools
      expect(screen.getAllByText("75.0")).toHaveLength(2); // overall + amenities
      expect(screen.getByText("72.0")).toBeInTheDocument(); // walkability
      expect(screen.getByText("68.0")).toBeInTheDocument(); // green space
    });

    it("displays weights", () => {
      render(<NeighborhoodScoreDisplay result={mockResult} compact={false} />);
      // Text is split across spans: "(25%)", so use a flexible matcher
      expect(screen.getAllByText((content, element) => {
        return element?.textContent === "Safety (25%)";
      })).toHaveLength(1);
      expect(screen.getAllByText((content, element) => {
        return element?.textContent === "Schools (20%)";
      })).toHaveLength(1);
      expect(screen.getAllByText((content, element) => {
        return element?.textContent === "Amenities (20%)";
      })).toHaveLength(1);
      expect(screen.getAllByText((content, element) => {
        return element?.textContent === "Walkability (20%)";
      })).toHaveLength(1);
      expect(screen.getAllByText((content, element) => {
        return element?.textContent === "Green Space (15%)";
      })).toHaveLength(1);
    });

    it("applies custom className", () => {
      const { container } = render(
        <NeighborhoodScoreDisplay result={mockResult} className="custom-class" />
      );
      expect(container.firstChild).toHaveClass("custom-class");
    });
  });
});
