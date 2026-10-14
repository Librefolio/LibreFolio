// Ambient declaration of the Designer Lab catalogue, served by frontend/scripts/designer-lab/vite-plugin.mjs in debug
// builds only. A separate file because src/app.d.ts is a module, where `declare module` would be an augmentation.
declare module 'virtual:lf-color-catalog' {
    const catalog: import('./types').ColorCatalog;
    export default catalog;
}
