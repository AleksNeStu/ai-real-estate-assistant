import {
  aggregateByDistrict,
  pointInPolygon,
  getDistrictColor,
  loadDistrictBoundaries,
} from '../district-aggregation';

describe('district-aggregation', () => {
  describe('pointInPolygon', () => {
    it('should correctly identify points inside polygon', () => {
      // Simple triangle polygon [lon, lat]
      const triangle = [
        [0, 0],
        [10, 0],
        [0, 10],
        [0, 0], // Close the polygon
      ];
      expect(pointInPolygon(0, 1, triangle)).toBe(true);
      expect(pointInPolygon(5, 5, triangle)).toBe(false);
      expect(pointInPolygon(15, 15, triangle)).toBe(false);
    });

    it('should return false for polygon with less than 3 points', () => {
      expect(pointInPolygon(0, 1, [[0, 0]])).toBe(false);
      expect(
        pointInPolygon(1, 1, [
          [1, 0],
          [2, 0],
        ])
      ).toBe(false);
    });

    it('should return false for empty polygon', () => {
      expect(pointInPolygon(1, 1, [])).toBe(false);
    });
  });

  describe('getDistrictColor', () => {
    it('should return gray for null avgPrice', () => {
      expect(getDistrictColor(null, 1000000)).toBe('hsla(240, 4%, 46%, 0.3)');
    });

    it('should return green for low ratio', () => {
      // ratio = 0.2 (< 0.25)
      expect(getDistrictColor(20000, 100000)).toBe('hsla(142, 76%, 36%, 0.4)');
    });

    it('should return yellow for medium-low ratio', () => {
      // ratio = 0.4 (< 0.5, >= 0.25)
      expect(getDistrictColor(40000, 100000)).toBe('hsla(32, 95%, 44%, 0.4)');
    });

    it('should return orange for medium-high ratio', () => {
      // ratio = 0.6 (< 0.75, >= 0.5)
      expect(getDistrictColor(60000, 100000)).toBe('hsla(20, 90%, 48%, 0.4)');
    });

    it('should return red for high ratio', () => {
      // ratio = 0.8 (>= 0.75)
      expect(getDistrictColor(80000, 100000)).toBe('hsla(0, 84%, 60%, 0.4)');
    });
  });

  describe('loadDistrictBoundaries', () => {
    it('should return Warsaw districts for Warsaw', async () => {
      const result = await loadDistrictBoundaries('Warsaw');
      expect(result.length).toBeGreaterThan(0);
      expect(result[0].name).toBeDefined();
      expect(result[0].polygon.length).toBeGreaterThan(2);
    });

    it('should return Warsaw districts for Warszawa', async () => {
      const result = await loadDistrictBoundaries('Warszawa');
      expect(result.length).toBeGreaterThan(1);
    });

    it('should return empty array for other cities', async () => {
      const result = await loadDistrictBoundaries('Berlin');
      expect(result).toEqual([]);
    });

    it('should be case-insensitive', async () => {
      const lower = await loadDistrictBoundaries('warsaw');
      const upper = await loadDistrictBoundaries('WARSAW');
      expect(lower.length).toBe(upper.length);
    });
  });

  describe('aggregateByDistrict', () => {
    it('should return empty array when no points provided', () => {
      const boundaries = [
        {
          id: 'test',
          name: 'Test',
          center: [0, 0],
          bounds: [
            [-1, -1],
            [1, 1],
          ],
          polygon: [
            [0, 0],
            [1, 0],
            [0, 1],
            [0, 0],
          ],
        },
      ];
      const result = aggregateByDistrict([], boundaries);
      expect(result).toHaveLength(0);
    });

    it('should return empty array when no boundaries provided', () => {
      const points = [{ id: '1', lat: 0, lon: 0, price: 100000, price_per_sqm: 1000 }];
      const result = aggregateByDistrict(points, []);
      expect(result).toHaveLength(0);
    });
  });
});
