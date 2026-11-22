/**
 * The contract the client speaks.
 *
 * Every path the client calls is named here, once, next to the operation it
 * belongs to. The drift test reads this file's paths out of the published
 * contract and fails when one of them is not described there - the client may
 * not call an endpoint the contract does not describe.
 */

/** The version prefix the application publishes its API under. */
export const API_ROOT = '/api/v1';

export interface Operation {
  /** The method the client calls with. */
  readonly method: 'get' | 'post';
  /** The path in the published contract. */
  readonly path: string;
  /** The path below the API root - what the client appends to the base URL. */
  readonly relative: string;
}

/** The three operations the client calls. */
export const OPERATIONS = {
  valuation: {
    method: 'post',
    path: `${API_ROOT}/tools/valuation`,
    relative: '/tools/valuation',
  },
  search: {
    method: 'post',
    path: `${API_ROOT}/search`,
    relative: '/search',
  },
  chat: {
    method: 'post',
    path: `${API_ROOT}/chat`,
    relative: '/chat',
  },
} as const satisfies Record<string, Operation>;
