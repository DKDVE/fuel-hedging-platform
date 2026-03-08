# Fuel Hedging Platform - Frontend

Modern React + TypeScript frontend for the Fuel Hedging Platform.

## Technology Stack

- **React 18** - UI library
- **TypeScript 5** - Type safety
- **Vite** - Build tool and dev server
- **TailwindCSS 3** - Utility-first CSS
- **React Query v5** - Data fetching and caching
- **React Router v6** - Client-side routing
- **Recharts** - Charts and visualizations
- **Axios** - HTTP client
- **Zod** - Schema validation
- **React Hook Form** - Form handling

## Quick Start

### Installation

```bash
cd frontend
npm install
```

### Development

```bash
npm run dev
```

The app will be available at `http://localhost:5173`

### Build

```bash
npm run build
```

The production build will be in the `dist/` folder.

### Type Checking

```bash
npm run type-check
```

### Linting

```bash
npm run lint
```

## Project Structure

```
frontend/
├── src/
│   ├── components/       # Reusable UI components
│   │   ├── Layout.tsx
│   │   ├── ProtectedRoute.tsx
│   │   ├── PriceChart.tsx
│   │   ├── RecommendationCard.tsx
│   │   └── MetricCard.tsx
│   ├── pages/            # Page components
│   │   ├── LoginPage.tsx
│   │   ├── DashboardPage.tsx
│   │   ├── MarketDataPage.tsx
│   │   ├── RecommendationsPage.tsx
│   │   └── AnalyticsPage.tsx
│   ├── contexts/         # React contexts
│   │   └── AuthContext.tsx
│   ├── hooks/            # Custom React hooks
│   │   ├── useAuth.ts
│   │   ├── useLivePrices.ts
│   │   ├── useMarketData.ts
│   │   ├── useRecommendations.ts
│   │   └── useAnalytics.ts
│   ├── lib/              # Utilities and API client
│   │   ├── api.ts
│   │   └── utils.ts
│   ├── types/            # TypeScript type definitions
│   │   └── api.ts
│   ├── App.tsx           # Root component
│   ├── main.tsx          # Entry point
│   └── index.css         # Global styles
├── public/               # Static assets
├── index.html            # HTML template
├── vite.config.ts        # Vite configuration
├── tsconfig.json         # TypeScript configuration
├── tailwind.config.js    # Tailwind configuration
└── package.json          # Dependencies

```

## Features

### Authentication
- JWT-based authentication with httpOnly cookies
- Role-based access control (ANALYST, RISK_MANAGER, CFO, ADMIN)
- Protected routes

### Dashboard
- Real-time price feed via Server-Sent Events (SSE)
- Key metrics overview
- 30-day price history chart
- Latest analytics run summary

### Market Data
- Live price ticker
- Historical price charts (7d, 30d, 90d, 1y)
- Multiple instrument comparison

### Recommendations
- Pending recommendations view
- Full recommendation history
- Approval workflow (CFO/Admin only)
- Detailed metrics and instrument mix

### Analytics
- Run history with success/failure status
- Summary statistics
- Manual run trigger (Admin/Risk Manager only)

## API Integration

The frontend communicates with the FastAPI backend through:

- **Axios client** (`src/lib/api.ts`) with interceptors for auth and error handling
- **React Query** for data fetching, caching, and mutations
- **SSE** for live price feed

All API types are defined in `src/types/api.ts` and must match backend Pydantic schemas exactly.

## Environment Variables

Create a `.env.local` file:

```bash
VITE_API_BASE_URL=/api/v1
```

In development, Vite proxy forwards `/api` requests to `http://localhost:8000`.

In production, set `VITE_API_BASE_URL` to your backend URL.

## Key Components

### Layout
Navigation bar and main content wrapper.

### ProtectedRoute
Wraps routes that require authentication and specific roles.

### PriceChart
Recharts-based line chart for price visualization.

### RecommendationCard
Displays hedge recommendation details with approval actions.

### MetricCard
Reusable card for displaying key metrics with icons and trends.

## Custom Hooks

### useAuth
Access authentication state and methods (login, logout).

### useLivePrices
Connect to SSE endpoint for real-time price updates.

### useMarketData
Fetch historical price data with date range filtering.

### useRecommendations
Query and mutate hedge recommendations.

### useAnalytics
Access analytics run history and trigger new runs.

## Styling

- **TailwindCSS** for utility-first styling
- Custom components defined in `index.css` (`.btn`, `.card`, `.badge`, etc.)
- Consistent color palette for risk levels and statuses
- Responsive design for mobile and desktop

## Type Safety

- **Strict TypeScript** enabled
- All API types match backend schemas
- No `any` types allowed
- Runtime validation with Zod (forms)

## Next Steps

- Add user management page (Admin only)
- Add configuration page for constraints
- Add position management
- Add audit log viewer
- Add export functionality for reports
