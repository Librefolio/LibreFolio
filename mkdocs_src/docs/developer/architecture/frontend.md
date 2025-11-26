# Frontend Architecture

> 🚧 **Work in Progress**
>
> The frontend is currently under development. This documentation will be expanded once the architecture and component library are stabilized.

## 🧰 Technology Stack

- **Framework**: React
- **Language**: TypeScript
- **Build Tool**: Vite
- **UI Components**: Material UI (MUI)
- **Data Fetching/State**: React Query
- **Internationalization (i18n)**: i18next

## 🎨 Design Principles

- **Component-Based**: The UI is built from reusable React components.
- **Responsive**: The layout will adapt to various screen sizes, from mobile to desktop.
- **Multilingual**: All UI text is managed through `i18next` to support multiple languages (EN, IT, FR, ES).
- **Backend-Driven Calculations**: The frontend is responsible for presentation only. All financial calculations, analysis, and data aggregation are performed by the backend. The frontend fetches and displays the results.

## 🕵️ How to get information about the frontend architecture

To get information about the frontend architecture an Agent can:

1.  Read this file.
2.  (Once implemented) Inspect the `frontend/` directory.
3.  (Once implemented) Read the `frontend/README.md` for setup and development instructions.
