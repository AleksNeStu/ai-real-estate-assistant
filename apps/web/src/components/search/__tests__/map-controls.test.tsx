import { render, screen, fireEvent } from '@testing-library/react';
import MapControls from '../map-controls';

describe('MapControls', () => {
  const mockOnChange = jest.fn();
  const mockOnZoomIn = jest.fn();
  const mockOnZoomOut = jest.fn();
  const mockOnFitBounds = jest.fn();

  const defaultOptions = {
    showHeatmap: false,
    heatmapIntensity: 1,
    showClusters: true,
    priceRange: undefined,
    propertyType: undefined,
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should render basic controls', () => {
    render(
      <MapControls
        options={defaultOptions}
        onChange={mockOnChange}
        onZoomIn={mockOnZoomIn}
        onZoomOut={mockOnZoomOut}
        onFitBounds={mockOnFitBounds}
      />
    );

    expect(screen.getByLabelText('Zoom in')).toBeInTheDocument();
    expect(screen.getByLabelText('Zoom out')).toBeInTheDocument();
    expect(screen.getByLabelText('Fit bounds')).toBeInTheDocument();
    expect(screen.getByLabelText('Toggle map filters')).toBeInTheDocument();
  });

  it('should call zoom handlers', () => {
    render(
      <MapControls
        options={defaultOptions}
        onChange={mockOnChange}
        onZoomIn={mockOnZoomIn}
        onZoomOut={mockOnZoomOut}
        onFitBounds={mockOnFitBounds}
      />
    );

    fireEvent.click(screen.getByLabelText('Zoom in'));
    expect(mockOnZoomIn).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByLabelText('Zoom out'));
    expect(mockOnZoomOut).toHaveBeenCalledTimes(1);
  });

  it('should call fit bounds handler', () => {
    render(
      <MapControls
        options={defaultOptions}
        onChange={mockOnChange}
        onZoomIn={mockOnZoomIn}
        onZoomOut={mockOnZoomOut}
        onFitBounds={mockOnFitBounds}
      />
    );

    fireEvent.click(screen.getByLabelText('Fit bounds'));
    expect(mockOnFitBounds).toHaveBeenCalledTimes(1);
  });

  it('should toggle advanced panel', () => {
    render(
      <MapControls
        options={defaultOptions}
        onChange={mockOnChange}
        onZoomIn={mockOnZoomIn}
        onZoomOut={mockOnZoomOut}
        onFitBounds={mockOnFitBounds}
      />
    );

    const toggleButton = screen.getByLabelText('Toggle map filters');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();

    fireEvent.click(toggleButton);
    expect(screen.getByRole('dialog')).toBeInTheDocument();

    fireEvent.click(toggleButton);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('should toggle heatmap', () => {
    render(
      <MapControls
        options={defaultOptions}
        onChange={mockOnChange}
        onZoomIn={mockOnZoomIn}
        onZoomOut={mockOnZoomOut}
        onFitBounds={mockOnFitBounds}
      />
    );

    fireEvent.click(screen.getByLabelText('Toggle map filters'));
    const heatmapToggle = screen.getByLabelText('Toggle heatmap');

    fireEvent.click(heatmapToggle);
    expect(mockOnChange).toHaveBeenCalledWith({ ...defaultOptions, showHeatmap: true });
  });

  it('should adjust heatmap intensity when heatmap is enabled', () => {
    const optionsWithHeatmap = { ...defaultOptions, showHeatmap: true, heatmapIntensity: 1 };
    render(
      <MapControls
        options={optionsWithHeatmap}
        onChange={mockOnChange}
        onZoomIn={mockOnZoomIn}
        onZoomOut={mockOnZoomOut}
        onFitBounds={mockOnFitBounds}
      />
    );

    fireEvent.click(screen.getByLabelText('Toggle map filters'));
    const intensitySlider = screen.getByLabelText('Heatmap intensity');

    fireEvent.change(intensitySlider, { target: { value: '2' } });
    expect(mockOnChange).toHaveBeenCalledWith({ ...optionsWithHeatmap, heatmapIntensity: 2 });
  });

  it('should toggle clusters', () => {
    render(
      <MapControls
        options={defaultOptions}
        onChange={mockOnChange}
        onZoomIn={mockOnZoomIn}
        onZoomOut={mockOnZoomOut}
        onFitBounds={mockOnFitBounds}
      />
    );

    fireEvent.click(screen.getByLabelText('Toggle map filters'));
    const clustersToggle = screen.getByLabelText('Toggle clusters');

    fireEvent.click(clustersToggle);
    expect(mockOnChange).toHaveBeenCalledWith({ ...defaultOptions, showClusters: false });
  });

  it('should filter by price range', () => {
    render(
      <MapControls
        options={defaultOptions}
        onChange={mockOnChange}
        onZoomIn={mockOnZoomIn}
        onZoomOut={mockOnZoomOut}
        onFitBounds={mockOnFitBounds}
      />
    );

    fireEvent.click(screen.getByLabelText('Toggle map filters'));
    // The band speaks in the currency of the listings, not in dollars.
    fireEvent.click(screen.getByLabelText('Filter under $300K'));

    expect(mockOnChange).toHaveBeenCalledWith({
      ...defaultOptions,
      priceRange: [0, 300000],
    });
  });

  it('should name the band in the currency of the listings', () => {
    render(
      <MapControls
        options={defaultOptions}
        onChange={mockOnChange}
        onZoomIn={mockOnZoomIn}
        onZoomOut={mockOnZoomOut}
        onFitBounds={mockOnFitBounds}
        currency="PLN"
      />
    );

    fireEvent.click(screen.getByLabelText('Toggle map filters'));

    expect(screen.getByLabelText('Filter under PLN 300K')).toBeInTheDocument();
    expect(screen.queryByLabelText('Filter under $300K')).not.toBeInTheDocument();
  });

  it('should filter by property type', () => {
    render(
      <MapControls
        options={defaultOptions}
        onChange={mockOnChange}
        onZoomIn={mockOnZoomIn}
        onZoomOut={mockOnZoomOut}
        onFitBounds={mockOnFitBounds}
      />
    );

    fireEvent.click(screen.getByLabelText('Toggle map filters'));
    const typeSelect = screen.getByLabelText('Filter by property type');

    fireEvent.change(typeSelect, { target: { value: 'apartment' } });
    expect(mockOnChange).toHaveBeenCalledWith({
      ...defaultOptions,
      propertyType: 'apartment',
    });
  });

  it('should reset all filters', () => {
    const optionsWithFilters = {
      ...defaultOptions,
      showHeatmap: true,
      priceRange: [0, 300000] as [number, number],
      propertyType: 'apartment',
    };

    render(
      <MapControls
        options={optionsWithFilters}
        onChange={mockOnChange}
        onZoomIn={mockOnZoomIn}
        onZoomOut={mockOnZoomOut}
        onFitBounds={mockOnFitBounds}
      />
    );

    fireEvent.click(screen.getByLabelText('Toggle map filters'));
    fireEvent.click(screen.getByLabelText('Reset all filters'));

    expect(mockOnChange).toHaveBeenCalledWith({
      showHeatmap: false,
      heatmapIntensity: 1,
      heatmapMode: 'density',
      showClusters: true,
      clusterOptions: {
        cellSizePx: 60,
        maxZoomForClustering: 15,
      },
      priceRange: undefined,
      propertyType: undefined,
    });
  });
});
