// Ambient declarations of the Designer Lab virtual modules, served by frontend/scripts/designer-lab/vite-plugin.mjs in
// debug builds only. A separate file because src/app.d.ts is a module, where `declare module` would be an augmentation.
declare module 'virtual:lf-color-catalog' {
    const catalog: import('./types').ColorCatalog;
    export default catalog;
}

declare module 'virtual:lf-testid-index' {
    const index: import('./types').TestidIndex;
    export default index;
}
