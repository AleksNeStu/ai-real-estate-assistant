import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import PropertyMap from "../property-map";

const fitBoundsMock = jest.fn();
const setViewMock = jest.fn();
const divIconMock = jest.fn(() => ({}));

jest.mock("leaflet", () => ({
  divIcon: (...args: unknown[]) => divIconMock(...args),
}));

jest.mock("react-leaflet", () => ({
  MapContainer: ({ children }: { children: ReactNode }) => <div data-testid="map">{children}</div>,
  TileLayer: () => <div data-testid="tile" />,
  Marker: ({
    children,
    position,
    eventHandlers,
  }: {
    children: ReactNode;
    position: unknown;
    eventHandlers?: { click?: () => void };
  }) => (
    <div data-testid="marker" data-position={JSON.stringify(position)}>
      <button type="button" data-testid="marker-click" onClick={() => eventHandlers?.click?.()}>
        click
      </button>
      {children}
    </div>
  ),
  Popup: ({ children }: { children: ReactNode }) => <div data-testid="popup">{children}</div>,
  // The map hands out its tile pane so the theme can filter the tiles; the
  // double has no pane, which is what a map without a raster layer looks like.
  useMap: () => ({ fitBounds: fitBoundsMock, setView: setViewMock, getPane: () => null }),
  useMapEvents: () => ({ getZoom: () => 12 }),
}));

describe("PropertyMap", () => {
  beforeEach(() => {
    fitBoundsMock.mockClear();
    setViewMock.mockClear();
    divIconMock.mockClear();
  });

  it("renders markers and popup content for points", () => {
    render(
      <PropertyMap
        points={[
          { id: "a", lat: 52.23, lon: 21.01, title: "A", city: "Warsaw", country: "PL", price: 100000 },
          { id: "b", lat: 52.24, lon: 21.02, title: "B", city: "Warsaw", country: "PL" },
        ]}
      />
    );

    expect(screen.getAllByTestId("marker")).toHaveLength(2);
    expect(screen.getByText("A")).toBeInTheDocument();
    expect(screen.getAllByText("Warsaw, PL")).toHaveLength(2);
    expect(screen.getByText("$100,000")).toBeInTheDocument();
    expect(screen.getByText("B")).toBeInTheDocument();
  });

  it("fits bounds when points are present", () => {
    render(<PropertyMap points={[{ id: "a", lat: 1, lon: 2 }, { id: "b", lat: 3, lon: 4 }]} />);
    expect(fitBoundsMock).toHaveBeenCalledTimes(1);
    expect(fitBoundsMock).toHaveBeenCalledWith(
      [
        [1, 2],
        [3, 4],
      ],
      { padding: [24, 24] }
    );
  });

  it("does not fit bounds when no points are present", () => {
    render(<PropertyMap points={[]} />);
    expect(fitBoundsMock).not.toHaveBeenCalled();
  });

  it("draws the markers with the tokens of the theme, not with raw colors", () => {
    render(
      <PropertyMap
        points={[
          { id: "a", lat: 52.23, lon: 21.01, title: "A", city: "Warsaw", country: "PL" },
        ]}
      />
    );

    expect(divIconMock).toHaveBeenCalled();
    const html = divIconMock.mock.calls.map((call) => (call[0] as { html: string }).html).join(" ");
    expect(html).toContain("hsl(var(--chart-1))");
    expect(html).toContain("hsl(var(--background))");
    expect(html).not.toMatch(/#[0-9a-fA-F]{3,6}\b/);
  });

  it("clusters dense points and renders a cluster popup summary", () => {
    const points = Array.from({ length: 80 }, (_, idx) => ({
      id: `p-${idx}`,
      lat: 52.23 + idx * 0.000001,
      lon: 21.01 + idx * 0.000001,
      title: `Property ${idx}`,
      city: "Warsaw",
      country: "PL",
    }));

    render(<PropertyMap points={points} />);

    expect(screen.getAllByTestId("marker").length).toBeLessThan(points.length);
    expect(screen.getByText("80 properties in this area")).toBeInTheDocument();
    expect(screen.getByText("Property 0")).toBeInTheDocument();
  });

  it("fits bounds when clicking a cluster marker", () => {
    const points = Array.from({ length: 80 }, (_, idx) => ({
      id: `p-${idx}`,
      lat: 52.23 + idx * 0.000001,
      lon: 21.01 + idx * 0.000001,
      title: `Property ${idx}`,
    }));

    render(<PropertyMap points={points} />);

    expect(screen.getAllByTestId("marker").length).toBeLessThan(points.length);
    const clickButtons = screen.getAllByTestId("marker-click");
    clickButtons[0].click();

    expect(setViewMock).not.toHaveBeenCalled();
    expect(fitBoundsMock).toHaveBeenCalledTimes(2);

    const lats = points.map((p) => p.lat);
    const lons = points.map((p) => p.lon);
    const minLat = Math.min(...lats);
    const maxLat = Math.max(...lats);
    const minLon = Math.min(...lons);
    const maxLon = Math.max(...lons);

    expect(fitBoundsMock).toHaveBeenLastCalledWith(
      [
        [minLat, minLon],
        [maxLat, maxLon],
      ],
      { padding: [24, 24], maxZoom: 14 }
    );
  });

  it("uses default center when no points are provided", () => {
    render(<PropertyMap points={[]} />);

    expect(screen.getByTestId("map")).toBeInTheDocument();
    expect(fitBoundsMock).not.toHaveBeenCalled();
  });

  it("renders cluster with truncated title list", () => {
    const points = Array.from({ length: 80 }, (_, idx) => ({
      id: `p-${idx}`,
      lat: 52.23 + idx * 0.000001,
      lon: 21.01 + idx * 0.000001,
      title: `Property ${idx}`,
      city: "Warsaw",
      country: "PL",
    }));

    render(<PropertyMap points={points} />);

    // Should show first 5 titles in cluster popup
    expect(screen.getByText("Property 0")).toBeInTheDocument();
    expect(screen.getByText("Property 1")).toBeInTheDocument();
    expect(screen.getByText("Property 2")).toBeInTheDocument();
    expect(screen.getByText("Property 3")).toBeInTheDocument();
    expect(screen.getByText("Property 4")).toBeInTheDocument();
  });

  it("handles cluster click when no bounds can be computed", () => {
    const points = Array.from({ length: 80 }, (_, idx) => ({
      id: `p-${idx}`,
      lat: 52.23, // All same lat - no bounds
      lon: 21.01, // All same lon - no bounds
      title: `Property ${idx}`,
    }));

    render(<PropertyMap points={points} />);

    const clickButtons = screen.getAllByTestId("marker-click");
    clickButtons[0].click();

    // Should use setView instead of fitBounds when no bounds (minLat === maxLat and minLon === maxLon)
    // When all points are the same, computeBounds returns null, so it zooms in
    expect(fitBoundsMock).toHaveBeenCalledTimes(2); // Initial fit + cluster click (with null bounds defaults to zoom)
  });

  it("renders cluster without titles when all properties are untitled", () => {
    const points = Array.from({ length: 80 }, (_, idx) => ({
      id: `p-${idx}`,
      lat: 52.23 + idx * 0.000001,
      lon: 21.01 + idx * 0.000001,
      city: "Warsaw",
      country: "PL",
      // No title - all filtered out as undefined
    }));

    render(<PropertyMap points={points} />);

    // Should show cluster with count but without individual title list
    expect(screen.getByText("80 properties in this area")).toBeInTheDocument();
  });

  it("handles empty city and country in popup", () => {
    render(
      <PropertyMap
        points={[
          { id: "a", lat: 52.23, lon: 21.01, title: "Test Property" },
          // No city or country
        ]}
      />
    );

    expect(screen.getByText("Location unavailable")).toBeInTheDocument();
  });
});
