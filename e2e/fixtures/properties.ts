/**
 * Test property fixtures for E2E tests.
 * Provides sample property data for search and display tests.
 */

export interface TestProperty {
  id: string;
  title: string;
  price: number;
  rooms: number;
  area: number;
  city: string;
  neighborhood: string;
  propertyType: 'apartment' | 'house' | 'studio';
  description: string;
}

/**
 * Sample properties for search tests.
 */
export const TEST_PROPERTIES: TestProperty[] = [
  {
    id: 'prop-001',
    title: 'Modern 2-Bedroom Apartment in Mitte',
    price: 1200,
    rooms: 2,
    area: 75,
    city: 'Berlin',
    neighborhood: 'Mitte',
    propertyType: 'apartment',
    description: 'A modern apartment in the heart of Berlin with excellent transport links.',
  },
  {
    id: 'prop-002',
    title: 'Spacious 3-Bedroom Flat in Prenzlauer Berg',
    price: 1500,
    rooms: 3,
    area: 95,
    city: 'Berlin',
    neighborhood: 'Prenzlauer Berg',
    propertyType: 'apartment',
    description: 'Family-friendly apartment near parks and schools.',
  },
  {
    id: 'prop-003',
    title: 'Cozy Studio in Kreuzberg',
    price: 800,
    rooms: 1,
    area: 35,
    city: 'Berlin',
    neighborhood: 'Kreuzberg',
    propertyType: 'studio',
    description: 'Compact studio perfect for young professionals.',
  },
  {
    id: 'prop-004',
    title: 'Family House in Charlottenburg',
    price: 2500,
    rooms: 4,
    area: 150,
    city: 'Berlin',
    neighborhood: 'Charlottenburg',
    propertyType: 'house',
    description: 'Spacious house with garden in a quiet neighborhood.',
  },
  {
    id: 'prop-005',
    title: 'Luxury Penthouse in Friedrichshain',
    price: 3500,
    rooms: 3,
    area: 120,
    city: 'Berlin',
    neighborhood: 'Friedrichshain',
    propertyType: 'apartment',
    description: 'Stunning penthouse with rooftop terrace and city views.',
  },
];

/**
 * Shape of a property as the API returns it (snake_case, as in
 * `apps/web/src/lib/types.ts` -> `Property`).
 */
export interface ApiProperty {
  id: string;
  title: string;
  description: string;
  country: string;
  region: string;
  city: string;
  district: string;
  neighborhood: string;
  address: string;
  latitude: number;
  longitude: number;
  property_type: 'apartment' | 'house' | 'studio' | 'loft' | 'townhouse' | 'other';
  listing_type: 'rent' | 'sale' | 'room' | 'sublease';
  rooms: number;
  bathrooms: number;
  area_sqm: number;
  floor: number;
  total_floors: number;
  year_built: number;
  energy_rating: string;
  price: number;
  currency: string;
  has_parking: boolean;
  has_garden: boolean;
  has_pool: boolean;
  has_garage: boolean;
  has_bike_room: boolean;
  amenities: string[];
  images: string[];
}

/**
 * One entry of `SearchResponse.results` - the property plus its score.
 */
export interface ApiSearchResult {
  property: ApiProperty;
  score: number;
}

const BERLIN_DISTRICTS: Record<string, { district: string; lat: number; lon: number }> = {
  Mitte: { district: 'Mitte', lat: 52.52, lon: 13.405 },
  'Prenzlauer Berg': { district: 'Prenzlauer Berg', lat: 52.54, lon: 13.424 },
  Kreuzberg: { district: 'Kreuzberg', lat: 52.498, lon: 13.418 },
  Charlottenburg: { district: 'Charlottenburg', lat: 52.516, lon: 13.304 },
  Friedrichshain: { district: 'Friedrichshain', lat: 52.512, lon: 13.454 },
};

/**
 * Convert the camelCase fixtures into the API shape. The coordinates are
 * needed: the results header counts only the listings that can be placed on
 * the map, so a fixture without lat/lon shows up as "0 of N".
 */
export function toApiProperty(property: TestProperty): ApiProperty {
  const place = BERLIN_DISTRICTS[property.neighborhood] ?? BERLIN_DISTRICTS['Mitte'];
  return {
    id: property.id,
    title: property.title,
    description: property.description,
    country: 'Germany',
    region: 'Berlin',
    city: property.city,
    district: place.district,
    neighborhood: property.neighborhood,
    address: `${property.neighborhood} 1, ${property.city}`,
    latitude: place.lat,
    longitude: place.lon,
    property_type: property.propertyType,
    listing_type: 'rent',
    rooms: property.rooms,
    bathrooms: Math.max(1, Math.floor(property.rooms / 2)),
    area_sqm: property.area,
    floor: 2,
    total_floors: 5,
    year_built: 2015,
    energy_rating: 'B',
    price: property.price,
    currency: 'EUR',
    has_parking: false,
    has_garden: property.propertyType === 'house',
    has_pool: false,
    has_garage: false,
    has_bike_room: true,
    amenities: ['balcony', 'elevator'],
    images: [],
  };
}

/**
 * The search response payload the frontend expects.
 */
export const TEST_SEARCH_RESULTS: ApiSearchResult[] = TEST_PROPERTIES.map((property, index) => ({
  property: toApiProperty(property),
  score: 0.95 - index * 0.05,
}));

/**
 * Get all test properties.
 */
export function getTestProperties(): TestProperty[] {
  return TEST_PROPERTIES;
}

/**
 * Get a test property by ID.
 */
export function getTestPropertyById(id: string): TestProperty | undefined {
  return TEST_PROPERTIES.find((p) => p.id === id);
}

/**
 * Filter properties by criteria.
 */
export function filterProperties(
  criteria: Partial<{
    minPrice: number;
    maxPrice: number;
    minRooms: number;
    propertyType: string;
    city: string;
  }>
): TestProperty[] {
  return TEST_PROPERTIES.filter((p) => {
    if (criteria.minPrice !== undefined && p.price < criteria.minPrice) return false;
    if (criteria.maxPrice !== undefined && p.price > criteria.maxPrice) return false;
    if (criteria.minRooms !== undefined && p.rooms < criteria.minRooms) return false;
    if (criteria.propertyType !== undefined && p.propertyType !== criteria.propertyType)
      return false;
    if (criteria.city !== undefined && p.city !== criteria.city) return false;
    return true;
  });
}
