# React + TypeScript + Vite

This template provides a minimal setup to get React working in Vite with HMR and some Oxlint rules.

## This project's stack

- **React 19 + Vite** with TypeScript.
- **Routing:** [TanStack Router](https://tanstack.com/router) (`src/router.tsx`).
- **Data fetching / server state:** [TanStack Query](https://tanstack.com/query)
  (see `src/pages/HomePage.tsx` and `src/api/`).

### Prefer the TanStack ecosystem

When you need additional client capabilities, reach for the TanStack ecosystem
first so the stack stays cohesive with the router/query already in use:

- **Forms** → [TanStack Form](https://tanstack.com/form)
- **Client state** → [TanStack Store](https://tanstack.com/store)
- **Tables / data grids** → [TanStack Table](https://tanstack.com/table)
- **Virtualized lists** → [TanStack Virtual](https://tanstack.com/virtual)

Overview of the whole ecosystem: <https://tanstack.com/>. For an
LLM/agent-friendly index of the docs, see <https://tanstack.com/llms.txt>.

Install new dependencies with `npm install <pkg>` (this project uses `npm`; do
not introduce `pnpm`/`yarn`).

## Vite plugins

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the Oxlint configuration

If you are developing a production application, we recommend enabling type-aware lint rules by installing `oxlint-tsgolint` and editing `.oxlintrc.json`:

```json
{
  "$schema": "./node_modules/oxlint/configuration_schema.json",
  "plugins": ["react", "typescript", "oxc"],
  "options": {
    "typeAware": true
  },
  "rules": {
    "react/rules-of-hooks": "error",
    "react/only-export-components": ["warn", { "allowConstantExport": true }]
  }
}
```

See the [Oxlint rules documentation](https://oxc.rs/docs/guide/usage/linter/rules) for the full list of rules and categories.
