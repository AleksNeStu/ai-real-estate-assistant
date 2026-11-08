# AI Real Estate Assistant - Frontend

This is the Next.js frontend for the AI Real Estate Assistant.

## Tech Stack

- **Framework**: Next.js 15+ (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS v4
- **Icons**: Lucide React
- **Utilities**: clsx, tailwind-merge
- **Data Fetching**: Axios (or SWR/TanStack Query in future)

## Getting Started

1.  **Install Dependencies**:

    ```bash
    npm install
    ```

2.  **Run Development Server**:

    ```bash
    npm run dev
    ```

    Open [http://localhost:3000](http://localhost:3000) with your browser.

    The frontend calls `/api/v1/*` on the Next.js server, which proxies to the Python backend. Configure:
    - `NEXT_PUBLIC_API_URL` (default `/api/v1`)
    - `BACKEND_API_URL` (default `http://localhost:8000/api/v1`)
    - `API_ACCESS_KEY` (used server-side to inject `X-API-Key`)

    The login/register pages store the submitted email in `localStorage` (`userEmail`), which is sent as `X-User-Email` for settings endpoints.

## Project Structure

- `src/app`: App Router pages and layouts.
- `src/components`: Reusable UI components.
  - `layout`: Structural components (Navbar, Sidebar).
  - `ui`: Primitive components (Buttons, Inputs, etc.).
- `src/lib`: Utility functions and configuration.

## Key Features

- **Search**: Property search interface.
- **Chat**: AI Assistant interaction.
- **Analytics**: Market insights and dashboards.

## Deployment

### Render Deployment

The frontend is deployed to Render using Docker. See [Deployment Guide](../../docs/deployment/DEPLOYMENT.md) for full setup.

**Environment Variables (Server-Side Only):**

| Variable          | Description            | Example                          |
| ----------------- | ---------------------- | -------------------------------- |
| `BACKEND_API_URL` | Deployed backend URL   | `https://api.example.com/api/v1` |
| `API_ACCESS_KEY`  | Backend authentication | Your generated key               |

**Key Security Design:**

- The Next.js API proxy at [`/api/v1/[...path]/route.ts`](src/app/api/v1/[...path]/route.ts) forwards requests to the backend
- `API_ACCESS_KEY` is injected server-side, never exposed to the browser
- `NEXT_PUBLIC_API_URL` stays as `/api/v1` (uses proxy) in all environments

**For complete deployment guide**, see [DEPLOYMENT.md](../../docs/deployment/DEPLOYMENT.md).

## Security Notes

- Do not expose secrets in the client. Use server-side env vars and the Next.js `/api/v1/*` proxy to inject `X-API-Key`.
- In production, authenticate requests server-side; let the backend enforce rate limits and CORS.
- `NEXT_PUBLIC_*` variables are exposed to the browser - never put secrets there.
